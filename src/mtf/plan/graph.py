"""PlanGraph module for building and analyzing plan dependencies from XML."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, List, Optional, Set, Union, cast

import networkx as nx
from lxml import etree

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
        task_id = cast(str, task_elem.get("id", ""))
        status_str = cast(str, task_elem.get("status", ""))
        description = cast(str, task_elem.findtext("description", ""))
        priority_str = cast(str, task_elem.findtext("priority", "1"))

        if not task_id or not status_str:
            return None

        try:
            status = Status(status_str)
        except ValueError:
            return None

        deps = task_elem.findall(".//depends_on")
        depends_on = [cast(str, dep.text) for dep in deps if dep.text]

        return TaskNode(
            id=task_id,
            description=description,
            status=status,
            priority=int(priority_str),
            depends_on=depends_on,
        )

    def _parse_story(self, story_elem: Any) -> Optional[StoryNode]:
        """Parse a story element into a StoryNode."""
        story_id = cast(str, story_elem.get("id", ""))
        status_str = cast(str, story_elem.get("status", ""))
        description = cast(str, story_elem.findtext("description", ""))
        priority_str = cast(str, story_elem.findtext("priority", "1"))
        points_str = cast(str, story_elem.findtext("points", "0"))

        if not story_id or not status_str:
            return None

        try:
            status = Status(status_str)
        except ValueError:
            return None

        tasks = []
        for task_elem in story_elem.findall(".//task"):
            task = self._parse_task(task_elem)
            if task:
                tasks.append(task)

        return StoryNode(
            id=story_id,
            description=description,
            status=status,
            priority=int(priority_str),
            points=int(points_str),
            tasks=tasks,
        )

    def _parse_epic(self, epic_elem: Any) -> Optional[EpicNode]:
        """Parse an epic element into an EpicNode."""
        epic_id = cast(str, epic_elem.get("id", ""))
        status_str = cast(str, epic_elem.get("status", ""))
        description = cast(str, epic_elem.findtext("description", ""))
        priority_str = cast(str, epic_elem.findtext("priority", "1"))

        if not epic_id or not status_str:
            return None

        try:
            status = Status(status_str)
        except ValueError:
            return None

        stories = []
        for story_elem in epic_elem.findall(".//story"):
            story = self._parse_story(story_elem)
            if story:
                stories.append(story)

        return EpicNode(
            id=epic_id,
            description=description,
            status=status,
            priority=int(priority_str),
            stories=stories,
        )

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

    def get_ready_tasks(self) -> List[str]:
        """
        Get all tasks that are ready to be worked on.

        A task is ready if:
        1. It is in PENDING status
        2. All its dependencies are COMPLETE

        Returns:
            List[str]: List of task IDs that are ready to be worked on
        """
        ready_tasks = []
        for node_id, node_data in self.graph.nodes(data=True):
            node = cast(NodeType, node_data.get("node"))
            if not isinstance(node, TaskNode) or node.status != Status.PENDING:
                continue

            # Check if all dependencies are complete
            dependencies = [
                self.graph.nodes[dep]["node"]
                for dep in self.graph.successors(node_id)
                if self.graph.edges[node_id, dep]["edge"].type == EdgeType.DEPENDS_ON
            ]
            if all(dep.status == Status.COMPLETE for dep in dependencies):
                ready_tasks.append(node_id)

        return ready_tasks

    def to_markdown(self) -> str:
        """
        Generate a markdown representation of the task hierarchy.

        Returns:
            str: Markdown formatted task hierarchy
        """

        def _add_task(task_id: str, visited: Set[str], level: int = 0) -> List[str]:
            if task_id in visited:
                return []
            visited.add(task_id)

            node_data = self.graph.nodes[task_id]
            node = cast(NodeType, node_data.get("node"))
            lines = [f"{'  ' * level}- {node.id}: {node.description} ({node.status.value})"]

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

        return "\n".join(lines)

    def to_mermaid(self) -> str:
        """
        Generate a mermaid graph representation.

        Returns:
            str: Mermaid formatted graph definition
        """
        lines = ["graph TD"]
        for src, dst, data in self.graph.edges(data=True):
            src_data = self.graph.nodes[src]
            dst_data = self.graph.nodes[dst]
            src_node = cast(NodeType, src_data.get("node"))
            dst_node = cast(NodeType, dst_data.get("node"))
            edge = cast(Edge, data.get("edge"))

            # Use different arrow styles for different edge types
            arrow = "-.>" if edge.type == EdgeType.DEPENDS_ON else "-->"
            lines.append(
                f"    {src_node.id}[{src_node.description}] {arrow} "
                f"{dst_node.id}[{dst_node.description}]"
            )
        return "\n".join(lines)

    def to_graphviz(self) -> str:
        """
        Generate a Graphviz DOT representation.

        Returns:
            str: Graphviz DOT formatted graph definition
        """
        lines = ["digraph {"]
        for src, dst, data in self.graph.edges(data=True):
            src_data = self.graph.nodes[src]
            dst_data = self.graph.nodes[dst]
            src_node = cast(NodeType, src_data.get("node"))
            dst_node = cast(NodeType, dst_data.get("node"))
            edge = cast(Edge, data.get("edge"))

            # Use different styles for different edge types
            style = "style=dashed" if edge.type == EdgeType.DEPENDS_ON else ""
            lines.append(
                f'    "{src_node.id}" [label="{src_node.description}"] -> '
                f'"{dst_node.id}" [label="{dst_node.description}" {style}]'
            )
        lines.append("}")
        return "\n".join(lines)
