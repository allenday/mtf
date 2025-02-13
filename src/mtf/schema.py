"""Schema definitions for the component registry."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field  # pylint: disable=import-error


class Parameter(BaseModel):
    """Schema for a component parameter."""

    name: str = Field(..., description="Name of the parameter")
    param_type: str = Field(
        ..., description="Data type of the parameter (e.g., str, int, list, dict)"
    )
    description: str = Field(..., description="Description of the parameter's purpose")
    default_value: Optional[Union[str, int, float, bool, List[Any], Dict[str, Any]]] = Field(
        None, description="Optional default value for the parameter"
    )


class Dependency(BaseModel):
    """Schema for a component dependency."""

    name: str = Field(..., description="Name of the dependency (e.g., requests, numpy)")
    version: Optional[str] = Field(
        None, description="Specific version of the dependency (e.g., 2.28.1)"
    )


class ComponentSchema(BaseModel):
    """Schema for a component in the registry."""

    component_type: str = Field(
        ..., description="Type of component (e.g., function, class, module)"
    )
    name: str = Field(..., description="Name of the component")
    description: str = Field(
        ..., description="Natural language description of the component's functionality"
    )
    input_parameters: List[Parameter] = Field([], description="List of input parameters")
    output_type: Optional[str] = Field(
        None, description="Data type of the output (e.g., str, int, list, dict)"
    )
    output_description: Optional[str] = Field(None, description="Description of the output")
    dependencies: List[Dependency] = Field([], description="List of dependencies")
    code: Optional[str] = Field(
        None, description="The generated code for the component (initially None)"
    )
    example_usage: Optional[str] = Field(
        None, description="Example code snippet demonstrating how to use the component"
    )
    tags: Optional[List[str]] = Field(
        None, description="List of tags for searching and categorizing components"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata (e.g., author, creation date)"
    )
