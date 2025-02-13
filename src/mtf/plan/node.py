"""Node classes for representing plan elements in the dependency graph."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Status(Enum):
    """Status of a plan element."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass
class BaseNode:
    """Base class for all plan nodes."""

    id: str
    description: str
    status: Status
    priority: int


@dataclass
class TaskNode(BaseNode):
    """Represents a task in the plan."""

    depends_on: List[str] = field(default_factory=list)


@dataclass
class StoryNode(BaseNode):
    """Represents a story in the plan."""

    points: int
    tasks: List[TaskNode] = field(default_factory=list)


@dataclass
class EpicNode(BaseNode):
    """Represents an epic in the plan."""

    stories: List[StoryNode] = field(default_factory=list)


@dataclass
class PlanNode:
    """Represents the root plan node."""

    version: str
    epics: List[EpicNode] = field(default_factory=list)
