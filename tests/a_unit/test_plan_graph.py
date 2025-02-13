"""Unit tests for PlanGraph functionality."""

import tempfile
from pathlib import Path

import networkx as nx
import pytest
from lxml import etree

from mtf.plan.graph import EdgeType, PlanGraph, XMLValidationError
from mtf.plan.models import (
    GetReadyTasksRequest,
    ToGraphvizRequest,
    ToMarkdownRequest,
    ToMermaidRequest,
)
from mtf.plan.node import EpicNode, Status, StoryNode, TaskNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PLAN_PATH = FIXTURES_DIR / "sample_plan.xml"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "src" / "mtf" / "schema" / "plan.xsd"


def test_xml_validation() -> None:
    """Test that XML validation works correctly."""
    # Test with valid XML
    plan_graph = PlanGraph()
    assert plan_graph.validate_xml(SAMPLE_PLAN_PATH) is True

    # Test with invalid XML
    with pytest.raises(XMLValidationError) as exc_info:
        plan_graph.validate_xml(FIXTURES_DIR / "invalid_plan.xml")
    assert isinstance(exc_info.value, XMLValidationError)

    # Test with non-existent file
    with pytest.raises(XMLValidationError) as exc_info:
        plan_graph.validate_xml(Path("nonexistent.xml"))
    assert isinstance(exc_info.value, XMLValidationError)

    # Test with malformed XML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml") as tmp:
        tmp.write("<?xml version='1.0'?><not>valid</xml>")
        tmp.flush()
        with pytest.raises(XMLValidationError) as exc_info:
            plan_graph.validate_xml(Path(tmp.name))
        assert isinstance(exc_info.value, XMLValidationError)


def test_task_graph_construction() -> None:
    """Test that PlanGraph correctly builds the graph from XML."""
    plan_graph = PlanGraph()
    plan_graph.build_from_xml(SAMPLE_PLAN_PATH)

    # Test graph properties
    assert isinstance(plan_graph.graph, nx.DiGraph)
    assert len(plan_graph.graph.nodes) > 0

    # Test plan structure
    assert plan_graph.plan is not None
    assert plan_graph.plan.version == "1.0"
    assert len(plan_graph.plan.epics) > 0

    # Test specific nodes exist and have correct types
    epic1_data = plan_graph.graph.nodes["epic1"]
    epic1_node = epic1_data["node"]
    assert isinstance(epic1_node, EpicNode)
    assert epic1_node.status == Status.IN_PROGRESS
    assert epic1_node.description == "Implement core model system"

    story1_data = plan_graph.graph.nodes["story1"]
    story1_node = story1_data["node"]
    assert isinstance(story1_node, StoryNode)
    assert story1_node.status == Status.COMPLETE
    assert story1_node.description == "Implement base model classes"

    task1_data = plan_graph.graph.nodes["task1"]
    task1_node = task1_data["node"]
    assert isinstance(task1_node, TaskNode)
    assert task1_node.status == Status.COMPLETE
    assert task1_node.description == "Create Task model"

    # Test dependencies (child points to parent)
    assert plan_graph.graph.has_edge("task2", "task1")  # task2 depends on task1
    assert plan_graph.graph.has_edge("task3", "task2")  # task3 depends on task2
    edge_data = plan_graph.graph.edges[("task2", "task1")]["edge"]
    assert edge_data.type == EdgeType.DEPENDS_ON

    # Test component relationships
    assert plan_graph.graph.has_edge("story1", "epic1")  # story1 is component of epic1
    assert plan_graph.graph.has_edge("task1", "story1")  # task1 is component of story1
    edge_data = plan_graph.graph.edges[("story1", "epic1")]["edge"]
    assert edge_data.type == EdgeType.COMPONENT_OF


# pylint: disable=protected-access
def test_invalid_node_parsing() -> None:
    """Test parsing of invalid nodes."""
    plan_graph = PlanGraph()

    # Test invalid task
    task_elem = etree.Element("task")
    assert plan_graph._parse_task(task_elem) is None

    task_elem.set("id", "task1")  # Missing status
    assert plan_graph._parse_task(task_elem) is None

    task_elem.set("status", "invalid_status")  # Invalid status
    assert plan_graph._parse_task(task_elem) is None

    # Test invalid story
    story_elem = etree.Element("story")
    assert plan_graph._parse_story(story_elem) is None

    story_elem.set("id", "story1")  # Missing status
    assert plan_graph._parse_story(story_elem) is None

    story_elem.set("status", "invalid_status")  # Invalid status
    assert plan_graph._parse_story(story_elem) is None

    # Test invalid epic
    epic_elem = etree.Element("epic")
    assert plan_graph._parse_epic(epic_elem) is None

    epic_elem.set("id", "epic1")  # Missing status
    assert plan_graph._parse_epic(epic_elem) is None

    epic_elem.set("status", "invalid_status")  # Invalid status
    assert plan_graph._parse_epic(epic_elem) is None


# pylint: enable=protected-access


def test_ready_tasks() -> None:
    """Test identification of ready tasks."""
    plan_graph = PlanGraph()
    plan_graph.build_from_xml(SAMPLE_PLAN_PATH)

    # Get ready tasks
    request = GetReadyTasksRequest(include_in_progress=False)
    ready_tasks = plan_graph.get_ready_tasks(request).tasks

    # task10 should not be ready (depends on task9 which is not complete)
    assert "task10" not in ready_tasks

    # task9 should not be ready (in_progress)
    assert "task9" not in ready_tasks

    # task1 should not be ready (complete)
    assert "task1" not in ready_tasks

    # Create a task that should be ready
    # pylint: disable=protected-access
    task_elem = etree.Element("task", id="ready_task", status="pending")
    task = plan_graph._parse_task(task_elem)
    assert task is not None
    # pylint: enable=protected-access
    plan_graph.graph.add_node("ready_task", node=task)

    # Now this task should be ready (pending with no dependencies)
    ready_tasks = plan_graph.get_ready_tasks(request).tasks
    assert "ready_task" in ready_tasks


def test_task_graph_visualization() -> None:
    """Test that PlanGraph can generate visualizations."""
    plan_graph = PlanGraph()
    plan_graph.build_from_xml(SAMPLE_PLAN_PATH)

    # Get reference nodes for testing
    epic1 = plan_graph.graph.nodes["epic1"]["node"]
    story1 = plan_graph.graph.nodes["story1"]["node"]
    task1 = plan_graph.graph.nodes["task1"]["node"]

    # Test markdown generation
    markdown_request = ToMarkdownRequest(include_status=True)
    markdown = plan_graph.to_markdown(markdown_request).content
    md_epic = f"- {epic1.id}: {epic1.description} ({epic1.status.value})"
    md_story = f"  - {story1.id}: {story1.description} ({story1.status.value})"
    assert md_epic in markdown
    assert md_story in markdown

    # Test mermaid generation
    mermaid_request = ToMermaidRequest(include_descriptions=True)
    mermaid = plan_graph.to_mermaid(mermaid_request).content
    mmd_story = f"{story1.id}[{story1.description}] --> {epic1.id}[{epic1.description}]"
    mmd_task = f"{task1.id}[{task1.description}] --> {story1.id}[{story1.description}]"
    assert mmd_story in mermaid
    assert mmd_task in mermaid

    # Test graphviz generation
    graphviz_request = ToGraphvizRequest(include_descriptions=True)
    dot = plan_graph.to_graphviz(graphviz_request).content
    assert "digraph" in dot
    # Test for presence of node IDs and descriptions
    assert story1.id in dot
    assert epic1.id in dot
    assert story1.description in dot
    assert epic1.description in dot
