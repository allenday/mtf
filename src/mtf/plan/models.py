"""Pydantic models for plan graph operations."""

from typing import List

from pydantic import BaseModel, Field

from mtf.plan.node import Status


class TaskModel(BaseModel):
    """Model representing a task in the graph."""

    id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Description of the task")
    status: Status = Field(..., description="Current status of the task")
    priority: int = Field(..., description="Priority level of the task")
    depends_on: List[str] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )


class StoryModel(BaseModel):
    """Model representing a story in the graph."""

    id: str = Field(..., description="Unique identifier for the story")
    description: str = Field(..., description="Description of the story")
    status: Status = Field(..., description="Current status of the story")
    priority: int = Field(..., description="Priority level of the story")
    points: int = Field(..., description="Story points estimate")
    tasks: List[TaskModel] = Field(default_factory=list, description="List of tasks in this story")


class EpicModel(BaseModel):
    """Model representing an epic in the graph."""

    id: str = Field(..., description="Unique identifier for the epic")
    description: str = Field(..., description="Description of the epic")
    status: Status = Field(..., description="Current status of the epic")
    priority: int = Field(..., description="Priority level of the epic")
    stories: List[StoryModel] = Field(
        default_factory=list, description="List of stories in this epic"
    )


class PlanModel(BaseModel):
    """Model representing the entire plan."""

    version: str = Field(..., description="Version of the plan")
    epics: List[EpicModel] = Field(default_factory=list, description="List of epics in the plan")


# Input Models
class GetReadyTasksRequest(BaseModel):
    """Input model for get_ready_tasks."""

    include_in_progress: bool = Field(
        default=False, description="Whether to include in-progress tasks in the result"
    )


class ToMarkdownRequest(BaseModel):
    """Input model for to_markdown."""

    include_status: bool = Field(
        default=True, description="Whether to include status in the output"
    )


class ToMermaidRequest(BaseModel):
    """Input model for to_mermaid."""

    include_descriptions: bool = Field(
        default=True, description="Whether to include descriptions in the output"
    )


class ToGraphvizRequest(BaseModel):
    """Input model for to_graphviz."""

    include_descriptions: bool = Field(
        default=True, description="Whether to include descriptions in the output"
    )


# Response Models
class ReadyTasksResponse(BaseModel):
    """Response model for get_ready_tasks."""

    tasks: List[str] = Field(
        default_factory=list, description="List of task IDs that are ready to be worked on"
    )


class MarkdownResponse(BaseModel):
    """Response model for to_markdown."""

    content: str = Field(..., description="Markdown formatted task hierarchy")


class MermaidResponse(BaseModel):
    """Response model for to_mermaid."""

    content: str = Field(..., description="Mermaid formatted graph definition")


class GraphvizResponse(BaseModel):
    """Response model for to_graphviz."""

    content: str = Field(..., description="Graphviz DOT formatted graph definition")
