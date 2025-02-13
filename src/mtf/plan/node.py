"""Node classes for representing plan elements."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Status(Enum):
    """Status of a plan element."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass
class TaskNode:
    """Node representing a task in the plan."""

    id: str
    description: str
    status: Status
    priority: int
    depends_on: List[str] = field(default_factory=list)


@dataclass
class StoryNode:
    """Node representing a story in the plan."""

    id: str
    description: str
    status: Status
    priority: int
    points: int
    tasks: List[TaskNode] = field(default_factory=list)


@dataclass
class EpicNode:
    """Node representing an epic in the plan."""

    id: str
    description: str
    status: Status
    priority: int
    stories: List[StoryNode] = field(default_factory=list)


@dataclass
class PlanNode:
    """Node representing the entire plan."""

    version: str
    epics: List[EpicNode] = field(default_factory=list)
