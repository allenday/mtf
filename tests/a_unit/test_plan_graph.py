"""Unit tests for PlanGraph functionality."""

from pathlib import Path

import networkx as nx
import pytest

from mtf.plan.graph import EdgeType, PlanGraph, XMLValidationError
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


def test_task_graph_visualization() -> None:
    """Test that PlanGraph can generate visualizations."""
    plan_graph = PlanGraph()
    plan_graph.build_from_xml(SAMPLE_PLAN_PATH)

    # Get reference nodes for testing
    epic1 = plan_graph.graph.nodes["epic1"]["node"]
    story1 = plan_graph.graph.nodes["story1"]["node"]
    task1 = plan_graph.graph.nodes["task1"]["node"]

    # Test markdown generation
    markdown = plan_graph.to_markdown()
    md_epic = f"- {epic1.id}: {epic1.description} ({epic1.status.value})"
    md_story = f"  - {story1.id}: {story1.description} ({story1.status.value})"
    assert md_epic in markdown
    assert md_story in markdown

    # Test mermaid generation
    mermaid = plan_graph.to_mermaid()
    mmd_story = f"{story1.id}[{story1.description}] --> {epic1.id}[{epic1.description}]"
    mmd_task = f"{task1.id}[{task1.description}] --> {story1.id}[{story1.description}]"
    assert mmd_story in mermaid
    assert mmd_task in mermaid

    # Test graphviz generation
    dot = plan_graph.to_graphviz()
    assert "digraph" in dot
    # Test for presence of node IDs and descriptions
    assert story1.id in dot
    assert epic1.id in dot
    assert story1.description in dot
    assert epic1.description in dot
