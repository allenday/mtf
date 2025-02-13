"""Unit tests for the example module."""

from unittest.mock import MagicMock

from pydantic_ai import RunContext

from mtf.example import add, calculate_sum


def test_example() -> None:
    """Basic test to verify test infrastructure."""
    assert True


def test_add() -> None:
    """Test the add function from the example module."""
    assert add(2, 3) == 5


def test_calculate_sum() -> None:
    """Test the calculate sum function without Agent."""
    # Create a mock RunContext
    ctx = MagicMock(spec=RunContext[str])
    result = calculate_sum(ctx, 2, 3)
    assert result == "The sum of 2 and 3 is 5"
