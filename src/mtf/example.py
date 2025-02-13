"""Example module demonstrating PydanticAI usage."""

import os
from typing import Any, Optional

from pydantic import BaseModel, Field  # pylint: disable=import-error
from pydantic_ai import Agent, RunContext  # pylint: disable=import-error


class AdditionResult(BaseModel):  # pylint: disable=too-few-public-methods
    """Result of an addition operation."""

    result: int = Field(description="The sum of the two numbers")
    explanation: str = Field(description="Explanation of the calculation")


def add(a: int, b: int) -> int:
    """Add two integers and return their sum.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b


# Create an agent only if API key is available
calculator: Optional[Agent[str, str]] = None
if os.getenv("OPENAI_API_KEY"):
    calculator = Agent(
        "openai:gpt-4",
        result_type=str,
        system_prompt="You are a helpful calculator assistant.",
    )


def calculate_sum(  # pylint: disable=unused-argument
    ctx: RunContext[str], /, a: int, b: int
) -> Any:
    """Calculate the sum of two numbers.

    Args:
        ctx: The run context
        a: First number to add
        b: Second number to add

    Returns:
        The sum of the two numbers
    """
    result = add(a, b)
    return f"The sum of {a} and {b} is {result}"


if calculator is not None:
    calculate_sum = calculator.tool(calculate_sum)

