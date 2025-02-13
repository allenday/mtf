"""PlanGraph module for building and analyzing plan dependencies from XML."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, List, Optional, Set, Union, cast

import networkx as nx
from lxml import etree

from mtf.plan.models import (
    EpicModel,
    GetReadyTasksRequest,
    GraphvizResponse,
    MarkdownResponse,
    MermaidResponse,
    ReadyTasksResponse,
    StoryModel,
    TaskModel,
    ToGraphvizRequest,
    ToMarkdownRequest,
    ToMermaidRequest,
)
from mtf.plan.node import EpicNode, PlanNode, Status, StoryNode, TaskNode


class EdgeType(Enum):
    """Types of relationships between nodes."""

    COMPONENT_OF = auto()  # Task is component of Story, Story is component of Epic
    DEPENDS_ON = auto()  # Task depends on another Task


@dataclass
class Edge:
    """Edge data for the plan graph."""

    type: EdgeType


class XMLValidationError(Exception):
    """Exception raised when XML validation fails."""


NodeType = Union[TaskNode, StoryNode, EpicNode]


class PlanGraph:
    """Class for building and analyzing plan dependency graphs from XML plans."""

    def __init__(self) -> None:
        """Initialize an empty PlanGraph."""
        self.graph: nx.DiGraph[str] = nx.DiGraph()  # pylint: disable=unsubscriptable-object
        self._schema: Optional[etree.XMLSchema] = None
        self.plan: Optional[PlanNode] = None

    def _load_schema(self) -> etree.XMLSchema:
        """Load and cache the XML schema."""
        if self._schema is None:
            schema_path = Path(__file__).parent / "schema" / "plan.xsd"
            schema_doc = etree.parse(str(schema_path))
            self._schema = etree.XMLSchema(schema_doc)
        return self._schema

    def validate_xml(self, xml_path: Path) -> bool:
        """
        Validate XML against the schema.

        Args:
            xml_path: Path to the XML file to validate

        Returns:
            bool: True if validation succeeds

        Raises:
            XMLValidationError: If validation fails
        """
        try:
            xml_doc = etree.parse(str(xml_path))
            schema = self._load_schema()
            schema.assertValid(xml_doc)
            return True
        except etree.DocumentInvalid as e:
            raise XMLValidationError(f"XML validation failed: {str(e)}") from e
        except (etree.XMLSyntaxError, OSError) as e:
            raise XMLValidationError(f"Failed to parse XML: {str(e)}") from e

    def _parse_task(self, task_elem: Any) -> Optional[TaskNode]:
        """Parse a task element into a TaskNode."""
        try:
            task_id = cast(str, task_elem.get("id", ""))
            status_str = cast(str, task_elem.get("status", ""))
            description = cast(str, task_elem.findtext("description", ""))
            priority_str = cast(str, task_elem.findtext("priority", "1"))
            deps = task_elem.findall(".//depends_on")
            depends_on = [cast(str, dep.text) for dep in deps if dep.text]

            # Validate using Pydantic model
            task_model = TaskModel(
                id=task_id,
                description=description,
                status=Status(status_str),
                priority=int(priority_str),
                depends_on=depends_on,
            )

            return TaskNode(
                id=task_model.id,
                description=task_model.description,
                status=task_model.status,
                priority=task_model.priority,
                depends_on=task_model.depends_on,
            )
        except (ValueError, TypeError):
            return None

    def _parse_story(self, story_elem: Any) -> Optional[StoryNode]:
        """Parse a story element into a StoryNode."""
        try:
            story_id = cast(str, story_elem.get("id", ""))
            status_str = cast(str, story_elem.get("status", ""))
            description = cast(str, story_elem.findtext("description", ""))
            priority_str = cast(str, story_elem.findtext("priority", "1"))
            points_str = cast(str, story_elem.findtext("points", "0"))

            tasks = []
            for task_elem in story_elem.findall(".//task"):
                task = self._parse_task(task_elem)
                if task:
                    tasks.append(task)

            # Validate using Pydantic model
            story_model = StoryModel(
                id=story_id,
                description=description,
                status=Status(status_str),
                priority=int(priority_str),
                points=int(points_str),
                tasks=[
                    TaskModel(
                        id=task.id,
                        description=task.description,
                        status=task.status,
                        priority=task.priority,
                        depends_on=task.depends_on,
                    )
                    for task in tasks
                ],
            )

            return StoryNode(
                id=story_model.id,
                description=story_model.description,
                status=story_model.status,
                priority=story_model.priority,
                points=story_model.points,
                tasks=tasks,
            )
        except (ValueError, TypeError):
            return None

    def _parse_epic(self, epic_elem: Any) -> Optional[EpicNode]:
        """Parse an epic element into an EpicNode."""
        try:
            epic_id = cast(str, epic_elem.get("id", ""))
            status_str = cast(str, epic_elem.get("status", ""))
            description = cast(str, epic_elem.findtext("description", ""))
            priority_str = cast(str, epic_elem.findtext("priority", "1"))

            stories = []
            for story_elem in epic_elem.findall(".//story"):
                story = self._parse_story(story_elem)
                if story:
                    stories.append(story)

            # Validate using Pydantic model
            epic_model = EpicModel(
                id=epic_id,
                description=description,
                status=Status(status_str),
                priority=int(priority_str),
                stories=[
                    StoryModel(
                        id=story.id,
                        description=story.description,
                        status=story.status,
                        priority=story.priority,
                        points=story.points,
                        tasks=[
                            TaskModel(
                                id=task.id,
                                description=task.description,
                                status=task.status,
                                priority=task.priority,
                                depends_on=task.depends_on,
                            )
                            for task in story.tasks
                        ],
                    )
                    for story in stories
                ],
            )

            return EpicNode(
                id=epic_model.id,
                description=epic_model.description,
                status=epic_model.status,
                priority=epic_model.priority,
                stories=stories,
            )
        except (ValueError, TypeError):
            return None

    def build_from_xml(self, xml_path: Path) -> None:
        """
        Build the task dependency graph from an XML file.

        Args:
            xml_path: Path to the XML file to parse
        """
        # First validate the XML
        self.validate_xml(xml_path)

        # Parse the XML
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Clear existing graph
        self.graph.clear()

        # Parse plan
        version = cast(str, root.get("version", "1.0"))
        epics = []
        for epic_elem in root.findall(".//epic"):
            epic = self._parse_epic(epic_elem)
            if epic:
                epics.append(epic)

        self.plan = PlanNode(version=version, epics=epics)

        # Build graph from plan
        for epic in self.plan.epics:
            self.graph.add_node(epic.id, node=epic)
            for story in epic.stories:
                self.graph.add_node(story.id, node=story)
                # Story is component of Epic
                self.graph.add_edge(story.id, epic.id, edge=Edge(type=EdgeType.COMPONENT_OF))
                for task in story.tasks:
                    self.graph.add_node(task.id, node=task)
                    # Task is component of Story
                    self.graph.add_edge(task.id, story.id, edge=Edge(type=EdgeType.COMPONENT_OF))
                    # Task depends on other tasks
                    for dep_id in task.depends_on:
                        self.graph.add_edge(task.id, dep_id, edge=Edge(type=EdgeType.DEPENDS_ON))

    def get_ready_tasks(self, request: GetReadyTasksRequest) -> ReadyTasksResponse:
        """
        Get all tasks that are ready to be worked on.

        Args:
            request: Input parameters for the request

        Returns:
            ReadyTasksResponse: Response containing list of task IDs that are ready to be worked on
        """
        # Validate request using Pydantic
        validated_request = GetReadyTasksRequest.model_validate(request)

        ready_tasks = []
        for node_id, node_data in self.graph.nodes(data=True):
            node = cast(NodeType, node_data.get("node"))
            if not isinstance(node, TaskNode):
                continue

            if node.status == Status.COMPLETE:
                continue

            if node.status == Status.IN_PROGRESS and not validated_request.include_in_progress:
                continue

            # Check if all dependencies are complete
            dependencies = [
                self.graph.nodes[dep]["node"]
                for dep in self.graph.successors(node_id)
                if self.graph.edges[node_id, dep]["edge"].type == EdgeType.DEPENDS_ON
            ]
            if all(dep.status == Status.COMPLETE for dep in dependencies):
                ready_tasks.append(node_id)

        # Validate response using Pydantic
        response = ReadyTasksResponse(tasks=ready_tasks)
        return response

    def to_markdown(self, request: ToMarkdownRequest) -> MarkdownResponse:
        """
        Generate a markdown representation of the task hierarchy.

        Args:
            request: Input parameters for the request

        Returns:
            MarkdownResponse: Response containing markdown formatted task hierarchy
        """
        # Validate request using Pydantic
        validated_request = ToMarkdownRequest.model_validate(request)

        def _add_task(task_id: str, visited: Set[str], level: int = 0) -> List[str]:
            if task_id in visited:
                return []
            visited.add(task_id)

            node_data = self.graph.nodes[task_id]
            node = cast(NodeType, node_data.get("node"))
            if validated_request.include_status:
                lines = [f"{'  ' * level}- {node.id}: {node.description} ({node.status.value})"]
            else:
                lines = [f"{'  ' * level}- {node.id}: {node.description}"]

            # Find children (nodes that point to this one as a component)
            children = [
                src
                for src, dst in self.graph.in_edges(task_id)
                if self.graph.edges[src, dst]["edge"].type == EdgeType.COMPONENT_OF
            ]
            for child in children:
                lines.extend(_add_task(child, visited, level + 1))
            return lines

        visited: Set[str] = set()
        # Find root nodes (those with no outgoing COMPONENT_OF edges)
        roots = [
            n
            for n in self.graph.nodes
            if not any(
                self.graph.edges[n, dst]["edge"].type == EdgeType.COMPONENT_OF
                for dst in self.graph.successors(n)
            )
        ]
        lines = []
        for root in roots:
            lines.extend(_add_task(root, visited))

        # Validate response using Pydantic
        response = MarkdownResponse(content="\n".join(lines))
        return response

    def to_mermaid(self, request: ToMermaidRequest) -> MermaidResponse:
        """
        Generate a mermaid graph representation.

        Args:
            request: Input parameters for the request

        Returns:
            MermaidResponse: Response containing mermaid formatted graph definition
        """
        # Validate request using Pydantic
        validated_request = ToMermaidRequest.model_validate(request)

        lines = ["graph TD"]
        for src, dst, data in self.graph.edges(data=True):
            src_data = self.graph.nodes[src]
            dst_data = self.graph.nodes[dst]
            src_node = cast(NodeType, src_data.get("node"))
            dst_node = cast(NodeType, dst_data.get("node"))
            edge = cast(Edge, data.get("edge"))

            # Use different arrow styles for different edge types
            arrow = "-.>" if edge.type == EdgeType.DEPENDS_ON else "-->"
            if validated_request.include_descriptions:
                lines.append(
                    f"    {src_node.id}[{src_node.description}] {arrow} "
                    f"{dst_node.id}[{dst_node.description}]"
                )
            else:
                lines.append(f"    {src_node.id} {arrow} {dst_node.id}")

        # Validate response using Pydantic
        response = MermaidResponse(content="\n".join(lines))
        return response

    def to_graphviz(self, request: ToGraphvizRequest) -> GraphvizResponse:
        """
        Generate a Graphviz DOT representation.

        Args:
            request: Input parameters for the request

        Returns:
            GraphvizResponse: Response containing Graphviz DOT formatted graph definition
        """
        # Validate request using Pydantic
        validated_request = ToGraphvizRequest.model_validate(request)

        lines = ["digraph {"]
        for src, dst, data in self.graph.edges(data=True):
            src_data = self.graph.nodes[src]
            dst_data = self.graph.nodes[dst]
            src_node = cast(NodeType, src_data.get("node"))
            dst_node = cast(NodeType, dst_data.get("node"))
            edge = cast(Edge, data.get("edge"))

            # Use different styles for different edge types
            style = "style=dashed" if edge.type == EdgeType.DEPENDS_ON else ""
            if validated_request.include_descriptions:
                lines.append(
                    f'    "{src_node.id}" [label="{src_node.description}"] -> '
                    f'"{dst_node.id}" [label="{dst_node.description}" {style}]'
                )
            else:
                lines.append(f'    "{src_node.id}" -> "{dst_node.id}" [{style}]')
        lines.append("}")

        # Validate response using Pydantic
        response = GraphvizResponse(content="\n".join(lines))
        return response
