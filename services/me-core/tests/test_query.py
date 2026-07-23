from __future__ import annotations

from pathlib import Path

from me_core.contracts import GraphNamespace
from me_core.fixtures import load_graph_fixture
from me_core.query import GraphQueryService
from me_core.store import InMemoryGraphStore


FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "graph" / "lighting-platform.json"


def service() -> GraphQueryService:
    store = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, store)
    return GraphQueryService(store)


def ids(graph_slice) -> set[str]:
    return {node.id for node in graph_slice.nodes}


def edge_types(graph_slice) -> set[str]:
    return {edge.type for edge in graph_slice.edges}


def test_project_snapshot_keeps_current_decision_and_excludes_superseded_decision() -> None:
    snapshot = service().get_project_snapshot("brain:project:lighting-platform")
    assert snapshot.graph is GraphNamespace.ME_BRAIN
    assert "brain:decision:radiance-primary" in ids(snapshot)
    assert "brain:decision:cycles-primary" not in ids(snapshot)
    assert snapshot.excluded["superseded"] == ("brain:decision:cycles-primary",)


def test_project_snapshot_includes_blocking_issue_and_task_relation() -> None:
    snapshot = service().get_project_snapshot("brain:project:lighting-platform")
    assert "brain:task:material-schema" in ids(snapshot)
    assert "brain:issue:material-parameters-unstable" in ids(snapshot)
    assert "BLOCKS" in edge_types(snapshot)


def test_trace_decision_returns_current_and_superseded_history() -> None:
    history = service().trace_decision("brain:decision:radiance-primary")
    assert ids(history) == {
        "brain:decision:radiance-primary",
        "brain:decision:cycles-primary",
    }
    assert edge_types(history) == {"SUPERSEDES"}


def test_get_evidence_returns_addressable_source_reference() -> None:
    refs = service().get_evidence("brain:decision:radiance-primary")
    assert refs[0].source_id == "src:conversation:2026-07-14"
    assert refs[0].source_anchor["value"]["message_id"] == "lighting-decision-14"


def test_task_profile_returns_only_rules_relevant_to_task_type() -> None:
    query = service()
    implementation = query.get_task_profile(
        "who:user:master",
        "brain:project:lighting-platform",
        "implementation",
    )
    architecture = query.get_task_profile(
        "who:user:master",
        "brain:project:lighting-platform",
        "technical_architecture",
    )
    assert "who:collaboration-rule:direct-execution" in ids(implementation)
    assert "who:collaboration-rule:architecture-first" not in ids(implementation)
    assert "who:collaboration-rule:architecture-first" in ids(architecture)
    assert "who:collaboration-rule:direct-execution" not in ids(architecture)


def test_expand_subgraph_respects_depth() -> None:
    query = service()
    depth_one = query.expand_subgraph("brain:project:lighting-platform", depth=1)
    depth_two = query.expand_subgraph("brain:project:lighting-platform", depth=2)
    assert "brain:decision:radiance-primary" in ids(depth_one)
    assert "brain:decision:cycles-primary" not in ids(depth_one)
    assert "brain:decision:cycles-primary" in ids(depth_two)
