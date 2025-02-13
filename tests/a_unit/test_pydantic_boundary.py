"""Tests for the Pydantic boundary checker."""

# mypy: ignore-errors
import astroid
from pylint.testutils import CheckerTestCase, MessageTest

from mtf.pylint_plugins.pydantic_boundary import PydanticBoundaryChecker


class TestPydanticBoundaryChecker(CheckerTestCase):
    """Test cases for PydanticBoundaryChecker."""

    CHECKER_CLASS = PydanticBoundaryChecker

    def setup_method(self) -> None:
        """Set up test patterns."""
        super().setup_method()
        # Configure test patterns - using protected access is acceptable in tests
        # pylint: disable=protected-access
        self.checker._boundary_patterns = ["test_boundary_", "other_pattern_"]

    def test_input_model_not_accessed(self) -> None:
        """Test that receiving a Pydantic model but never accessing it fails."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class InputModel(BaseModel):
                field: str
            def test_boundary_func(data: InputModel) -> str:  #@
                return "test"  # Never uses data
            """
        )
        with self.assertAddsMessages(
            MessageTest(
                msg_id="pydantic-validation-missing",
                node=node,
                args="test_boundary_func",
            ),
            ignore_position=True,
        ):
            self.checker.visit_functiondef(node)

    def test_input_model_properly_used(self) -> None:
        """Test that receiving and properly using a Pydantic model passes."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class InputModel(BaseModel):
                field: str
            def test_boundary_func(data: InputModel) -> str:  #@
                validated = InputModel.model_validate(data)
                return validated.field
            """
        )
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_output_model_without_validation(self) -> None:
        """Test that returning a Pydantic model without validation fails."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class OutputModel(BaseModel):
                result: str
            def test_boundary_func(data: dict) -> OutputModel:  #@
                return OutputModel(result=data["field"])  # Direct construction without validation
            """
        )
        with self.assertAddsMessages(
            MessageTest(
                msg_id="pydantic-validation-missing",
                node=node,
                args="test_boundary_func",
            ),
            ignore_position=True,
        ):
            self.checker.visit_functiondef(node)

    def test_output_model_with_validation(self) -> None:
        """Test that properly validating before returning a Pydantic model passes."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class OutputModel(BaseModel):
                result: str
            def test_boundary_func(data: dict) -> OutputModel:  #@
                return OutputModel.model_validate(data)
            """
        )
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_internal_model_usage_without_validation(self) -> None:
        """Test that using Pydantic models internally without validation fails."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class MyModel(BaseModel):
                field: str
            def test_boundary_func(data: dict) -> dict:  #@
                model = MyModel(field=data["field"])  # Direct construction
                return model.model_dump()
            """
        )
        with self.assertAddsMessages(
            MessageTest(
                msg_id="pydantic-validation-missing",
                node=node,
                args="test_boundary_func",
            ),
            ignore_position=True,
        ):
            self.checker.visit_functiondef(node)

    def test_internal_model_usage_with_validation(self) -> None:
        """Test that using Pydantic models internally with validation passes."""
        node = astroid.extract_node(
            """
            from pydantic import BaseModel
            class MyModel(BaseModel):
                field: str
            def test_boundary_func(data: dict) -> dict:  #@
                model = MyModel.model_validate(data)
                return model.model_dump()
            """
        )
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_non_boundary_function_ignored(self) -> None:
        """Test that non-boundary functions are ignored."""
        node = astroid.extract_node(
            """
            def normal_function(data: dict) -> dict:  #@
                return data
            """
        )
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_exempt_function(self) -> None:
        """Test that exempt functions are not checked."""
        node = astroid.extract_node(
            """
            from mtf.pylint_plugins.pydantic_boundary import pydantic_boundary_exempt
            @pydantic_boundary_exempt
            def test_boundary_func(data: dict) -> dict:  #@
                return data
            """
        )
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)
