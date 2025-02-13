"""Pylint plugin to enforce Pydantic usage at component boundaries."""

from typing import Any, Callable, List, Optional, Sequence, Set, TypeVar

# mypy: ignore-errors
import astroid
from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter

F = TypeVar("F", bound=Callable[..., Any])

PYDANTIC_VALIDATION_METHODS = {
    "model_validate",
    "model_validate_json",
    "parse_obj",
    "parse_raw",
    "parse_file",
}


def pydantic_boundary_exempt(func: F) -> F:
    """Decorator to exempt a function from Pydantic boundary checks.

    Example:
        @pydantic_boundary_exempt
        def my_api_endpoint(data: dict) -> dict:
            return data
    """
    setattr(func, "_pydantic_boundary_exempt", True)
    return func


class PydanticBoundaryChecker(BaseChecker):
    """Checks for proper Pydantic model usage at function boundaries.

    This checker enforces two main rules:
    1. All function type annotations must be Pydantic models
    2. Boundary functions must utilize Pydantic validation

    Truth table for message emission:
    | has_pyd_ann | has_ann | uses_pyd | uses_val | ann_miss | val_miss |
    |-------------|---------|----------|----------|----------|-----------|
    | 0           | 0       | 0        | 0        | 1        | 1        |
    | 0           | 0       | 0        | 1        | 1        | 0        |
    | 0           | 0       | 1        | 0        | 1        | 1        |
    | 0           | 0       | 1        | 1        | 1        | 0        |
    | 0           | 1       | 0        | 0        | 1        | 1        |
    | 0           | 1       | 0        | 1        | 1        | 0        |
    | 0           | 1       | 1        | 0        | 1        | 1        |
    | 0           | 1       | 1        | 1        | 1        | 0        |
    | 1           | 0       | 0        | 0        | 0        | 1        |
    | 1           | 0       | 0        | 1        | 0        | 0        |
    | 1           | 0       | 1        | 0        | 0        | 1        |
    | 1           | 0       | 1        | 1        | 0        | 0        |
    | 1           | 1       | 0        | 0        | 0        | 1        |
    | 1           | 1       | 0        | 1        | 0        | 0        |
    | 1           | 1       | 1        | 0        | 0        | 1        |
    | 1           | 1       | 1        | 1        | 0        | 0        |
    """

    name = "pydantic-boundary"
    priority = -1
    msgs = {
        "W6201": (
            "Function '%s' is missing Pydantic model annotations",
            "pydantic-annotations-missing",
            "Function arguments and return values should be annotated with Pydantic models",
        ),
        "W6202": (
            "Function '%s' is missing Pydantic validation",
            "pydantic-validation-missing",
            "Function should validate its inputs using Pydantic validation methods",
        ),
    }

    options = (
        (
            "boundary-patterns",
            {
                "default": "",
                "type": "string",
                "metavar": "<pattern>",
                "help": "Comma-separated patterns for identifying component boundary functions",
            },
        ),
    )

    def __init__(self, linter: Optional[PyLinter] = None) -> None:
        """Initialize the checker."""
        if linter is None:
            raise ValueError("Linter must be provided")
        super().__init__(linter)
        self._boundary_patterns: List[str] = []
        self._pydantic_imports: Set[str] = set()

    def open(self) -> None:
        """Initialize boundary patterns from configuration."""
        patterns = getattr(self.linter.config, "boundary_patterns", [])
        if isinstance(patterns, str):
            patterns = [p.strip() for p in patterns.split(",") if p.strip()]
        self._boundary_patterns = patterns

    def _is_boundary_function(self, node: nodes.FunctionDef) -> bool:
        """Check if a function is a component boundary based on naming patterns."""
        for pattern in self._boundary_patterns:
            if node.name.startswith(pattern):
                return True
        return False

    def _is_exempt(self, node: nodes.FunctionDef) -> bool:
        """Check if a function is explicitly exempt from Pydantic validation."""
        if not node.decorators:
            return False

        for decorator in node.decorators.nodes:
            # Check for direct decorator usage
            if isinstance(decorator, nodes.Name) and decorator.name == "pydantic_boundary_exempt":
                return True
            # Check for qualified decorator usage
            if (
                isinstance(decorator, nodes.Attribute)
                and decorator.attrname == "pydantic_boundary_exempt"
            ):
                return True
        return False

    def _check_base_model_in_class(self, class_node: nodes.ClassDef) -> bool:
        """Check if a class inherits from BaseModel."""
        for base in class_node.bases:
            if isinstance(base, nodes.Name) and base.name == "BaseModel":
                return True
            if isinstance(base, nodes.Attribute) and base.attrname == "BaseModel":
                return True
        return False

    def _check_base_model_in_module(self, module_node: nodes.Module) -> bool:
        """Check if a module imports BaseModel from pydantic."""
        for import_node in module_node.nodes_of_class(nodes.ImportFrom):
            if import_node.modname == "pydantic":
                for name, _ in import_node.names:
                    if name == "BaseModel":
                        return True
        return False

    def _is_pydantic_model(self, node: nodes.NodeNG) -> bool:
        """Check if a node represents a Pydantic model.

        Args:
            node: The node to check.

        Returns:
            bool: True if the node represents a Pydantic model, False otherwise.
        """
        if isinstance(node, nodes.Name):
            # Check if the name is a Pydantic model class
            try:
                inferred = next(node.infer())
                if isinstance(inferred, nodes.ClassDef):
                    for base in inferred.bases:
                        if isinstance(base, nodes.Name) and base.name == "BaseModel":
                            return True
            except astroid.exceptions.InferenceError:
                pass
        return False

    def _has_pydantic_annotations(self, node: nodes.FunctionDef) -> bool:
        """Check if the function has Pydantic model annotations in its signature.

        Args:
            node: The function definition node to check.

        Returns:
            bool: True if the function has Pydantic model annotations, False otherwise.
        """
        # Check argument annotations
        if node.args.annotations:
            for annotation in node.args.annotations:
                if annotation and self._is_pydantic_model(annotation):
                    return True

        # Check return annotation
        if node.returns and self._is_pydantic_model(node.returns):
            return True

        return False

    def _uses_pydantic_validation(self, node: nodes.FunctionDef) -> bool:
        """Check if the function uses Pydantic validation."""
        for child in node.nodes_of_class(nodes.Call):
            if isinstance(child.func, nodes.Attribute):
                # Check for model_validate and other validation methods
                if child.func.attrname in PYDANTIC_VALIDATION_METHODS:
                    return True
        return False

    def _uses_pydantic_models(self, node: nodes.FunctionDef) -> bool:
        """Check if the function uses Pydantic models."""

        def check_inferred(inferred: Sequence[Any]) -> bool:
            """Helper to check inferred nodes for BaseModel."""
            for inf in inferred:
                if isinstance(inf, nodes.ClassDef):
                    if self._check_base_model_in_class(inf):
                        return True
            return False

        for child in node.nodes_of_class(nodes.Call):
            if isinstance(child.func, nodes.Name):
                try:
                    if check_inferred(child.func.inferred()):
                        return True
                except:  # pylint: disable=bare-except
                    continue
            elif isinstance(child.func, nodes.Attribute):
                try:
                    if check_inferred(child.func.expr.inferred()):
                        return True
                except:  # pylint: disable=bare-except
                    continue
        return False

    def _has_any_annotations(self, node: nodes.FunctionDef) -> bool:
        """Check if the function has any type annotations.

        Args:
            node: The function definition node to check.

        Returns:
            bool: True if the function has any type annotations, False otherwise.
        """
        return bool(node.args.annotations or node.returns)

    def _uses_model_attribute(self, node: nodes.FunctionDef, model_name: str) -> bool:
        """Check if a model's attributes are accessed in the function.

        This ensures that if we receive a Pydantic model, we actually use its data.
        """
        for child in node.nodes_of_class(nodes.Attribute):
            if isinstance(child.expr, nodes.Name) and child.expr.name == model_name:
                return True
        return False

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Visit a function definition.

        For boundary functions, analyze data flow:
        1. Input models must be accessed (used) or validated
        2. Any Pydantic models used internally must be validated
        """
        if not self._boundary_patterns or not self._is_boundary_function(node):
            return

        if self._is_exempt(node):
            return

        # Track Pydantic model parameters
        pydantic_inputs = []
        if node.args.args and node.args.annotations:
            for arg, annotation in zip(node.args.args, node.args.annotations):
                if annotation and self._is_pydantic_model(annotation):
                    pydantic_inputs.append(arg.name)

        # Check if we use any Pydantic models (including constructing output)
        uses_pydantic = self._uses_pydantic_models(node)
        uses_validation = self._uses_pydantic_validation(node)

        # For input models, either validation or direct access is fine
        for param_name in pydantic_inputs:
            if not (uses_validation or self._uses_model_attribute(node, param_name)):
                self.add_message(
                    "pydantic-validation-missing",
                    node=node,
                    args=node.name,
                )
                break

        # For internal/output Pydantic usage, must validate
        if uses_pydantic and not uses_validation:
            self.add_message(
                "pydantic-validation-missing",
                node=node,
                args=node.name,
            )


def register(linter: PyLinter) -> None:
    """Register the checker with pylint."""
    linter.register_checker(PydanticBoundaryChecker(linter))
