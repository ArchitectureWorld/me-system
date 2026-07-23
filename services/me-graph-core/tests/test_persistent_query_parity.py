from __future__ import annotations

from pathlib import Path

from me_graph_core.fixtures import load_graph_fixture
from me_graph_core.persistence.models import create_schema
from me_graph_core.persistence.store import SqlAlchemyGraphStore
from me_graph_core.persistence.testing import create_sqlite_test_engine
from me_graph_core.query import GraphQueryService
from me_graph_core.store import InMemoryGraphStore


FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "graph" / "lighting-platform.json"


def _stores() -> tuple[InMemoryGraphStore, SqlAlchemyGraphStore]:
    memory = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, memory)

    engine = create_sqlite_test_engine()
    create_schema(engine)
    persistent = SqlAlchemyGraphStore(engine)
    load_graph_fixture(FIXTURE, persistent)
    return memory, persistent


def test_persistent_project_snapshot_matches_in_memory() -> None:
    memory, persistent = _stores()
    expected = GraphQueryService(memory).get_project_snapshot(
        "brain:project:lighting-platform"
    )
    actual = GraphQueryService(persistent).get_project_snapshot(
        "brain:project:lighting-platform"
    )

    assert actual.nodes == expected.nodes
    assert actual.edges == expected.edges
    assert actual.evidence_handles == expected.evidence_handles
    assert actual.excluded == expected.excluded
    assert actual.summary == expected.summary


def test_persistent_decision_trace_matches_in_memory() -> None:
    memory, persistent = _stores()
    expected = GraphQueryService(memory).trace_decision(
        "brain:decision:radiance-primary"
    )
    actual = GraphQueryService(persistent).trace_decision(
        "brain:decision:radiance-primary"
    )

    assert actual.nodes == expected.nodes
    assert actual.edges == expected.edges
    assert actual.evidence_handles == expected.evidence_handles
    assert actual.summary == expected.summary


def test_persistent_task_profile_matches_in_memory() -> None:
    memory, persistent = _stores()
    expected = GraphQueryService(memory).get_task_profile(
        "who:user:master",
        "brain:project:lighting-platform",
        "implementation",
    )
    actual = GraphQueryService(persistent).get_task_profile(
        "who:user:master",
        "brain:project:lighting-platform",
        "implementation",
    )

    assert actual.nodes == expected.nodes
    assert actual.edges == expected.edges
    assert actual.evidence_handles == expected.evidence_handles
    assert actual.summary == expected.summary
