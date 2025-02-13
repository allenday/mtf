"""Tests for schema definitions."""

import json

from mtf.schema import ComponentSchema, Dependency, Parameter


def test_basic_component_schema() -> None:
    """Test creating and serializing a basic component schema."""
    example_component = ComponentSchema(
        component_type="function",
        name="add_numbers",
        description="Adds two numbers together.",
        input_parameters=[
            Parameter(
                name="a", param_type="int", description="The first number", default_value=None
            ),
            Parameter(
                name="b", param_type="int", description="The second number", default_value=None
            ),
        ],
        output_type="int",
        output_description="The sum of a and b.",
        dependencies=[],
        code=None,
        example_usage=None,
        tags=None,
        metadata=None,
    )

    # Convert to JSON and back to verify serialization
    json_str = example_component.model_dump_json(indent=2)
    parsed = json.loads(json_str)

    # Basic assertions
    assert parsed["component_type"] == "function"
    assert parsed["name"] == "add_numbers"
    assert len(parsed["input_parameters"]) == 2
    assert parsed["output_type"] == "int"


def test_full_component_schema() -> None:
    """Test creating a component schema with all optional fields."""
    example_component = ComponentSchema(
        component_type="function",
        name="add_numbers",
        description="Adds two numbers together.",
        input_parameters=[
            Parameter(name="a", param_type="int", description="The first number", default_value=0),
            Parameter(name="b", param_type="int", description="The second number", default_value=0),
        ],
        output_type="int",
        output_description="The sum of a and b.",
        dependencies=[Dependency(name="numpy", version=">=1.20.0")],
        code="""def add_numbers(a: int = 0, b: int = 0) -> int:
    return a + b""",
        example_usage="result = add_numbers(1, 2)  # returns 3",
        tags=["math", "basic", "addition"],
        metadata={"author": "MTF Team", "created_at": "2024-02-13"},
    )

    # Convert to JSON and verify all fields
    json_str = example_component.model_dump_json(indent=2)
    parsed = json.loads(json_str)

    # Detailed assertions
    assert parsed["dependencies"][0]["name"] == "numpy"
    assert parsed["dependencies"][0]["version"] == ">=1.20.0"
    assert parsed["tags"] == ["math", "basic", "addition"]
    assert "code" in parsed
    assert "example_usage" in parsed
    assert "metadata" in parsed
    assert parsed["metadata"]["author"] == "MTF Team"
