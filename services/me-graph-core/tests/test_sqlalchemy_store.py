from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import inspect

from me_graph_core.contracts import (
    AuthorityLevel,
    ConfirmationStatus,
    EvidenceRef,
    GraphEdge,
    GraphNamespace,
    GraphNode,
    Sensitivity,
    TemporalStatus,
)
from me_graph_core.errors import (
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
)
from me_graph_core.persistence.models import create_schema
from me_graph_core.persistence.store import SqlAlchemyGraphStore
from me_graph_core.persistence.testing import create_sqlite_test_engine


def evidence(source_id: str, ordinal: int = 0) -> EvidenceRef:
    return EvidenceRef(
        source_id=source_id,
        document_id=f"doc:{ordinal}",
        version_id=f"version:{ordinal}",
        content_fragment_id=f"fragment:{ordinal}",
        source_anchor={"type": "fixture", "value": {"ordinal": ordinal}},
    )


def node(
    node_id: str,
    graph: GraphNamespace,
    *,
    refs: tuple[EvidenceRef, ...] | None = None,
    properties: dict[str, object] | None = None,
) -> GraphNode:
    return GraphNode(
        id=node_id,
        graph=graph,
        type="Entity",
        label=node_id,
        properties=properties or {"nested": {"value": 1}},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        status=TemporalStatus.CURRENT,
        valid_from=datetime(2026, 7, 23, tzinfo=timezone.utc),
        valid_to=None,
        sensitivity=(
            Sensitivity.PROJECT_PRIVATE
            if graph is GraphNamespace.ME_BRAIN
            else Sensitivity.PERSONAL_PRIVATE
        ),
        source_refs=refs or (evidence(f"src:{node_id}"),),
    )


def edge(
    edge_id: str,
    graph: GraphNamespace,
    from_id: str,
    to_id: str,
    *,
    refs: tuple[EvidenceRef, ...] | None = None,
) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        graph=graph,
        type="RELATED_TO",
        from_id=from_id,
        to_id=to_id,
        properties={"kind": "test"},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        confidence=0.9,
        valid_from=datetime(2026, 7, 23, tzinfo=timezone.utc),
        valid_to=None,
        sensitivity=(
            Sensitivity.RESTRICTED
            if graph is GraphNamespace.BRIDGE
            else Sensitivity.PROJECT_PRIVATE
        ),
        source_refs=refs or (evidence(f"src:{edge_id}"),),
    )


@pytest.fixture
def engine():
    value = create_sqlite_test_engine()
    create_schema(value)
    return value


@pytest.fixture
def store(engine):
    return SqlAlchemyGraphStore(engine)


def test_schema_creates_graph_tables(engine) -> None:
    names = set(inspect(engine).get_table_names())
    assert names == {"graph_objects", "graph_evidence_refs"}


def test_node_round_trip_preserves_json_time_and_ordered_evidence(store) -> None:
    value = node(
        "brain:project:lighting",
        GraphNamespace.ME_BRAIN,
        refs=(evidence("src:second", 2), evidence("src:first", 1)),
        properties={"nested": {"list": [1, 2, 3]}},
    )
    store.add_node(value)
    assert store.get_node(value.id) == value


def test_edge_round_trip_and_neighbors(store) -> None:
    project = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    decision = node("brain:decision:radiance", GraphNamespace.ME_BRAIN)
    store.add_node(project)
    store.add_node(decision)
    relation = edge("edge:has-decision", GraphNamespace.ME_BRAIN, project.id, decision.id)
    store.add_edge(relation)
    assert store.get_edge(relation.id) == relation
    assert store.neighbors(project.id, direction="out") == (relation,)
    assert store.neighbors(decision.id, direction="in") == (relation,)


def test_global_duplicate_id_is_rejected(store) -> None:
    project = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    decision = node("brain:decision:radiance", GraphNamespace.ME_BRAIN)
    store.add_node(project)
    store.add_node(decision)
    with pytest.raises(DuplicateGraphObjectError):
        store.add_edge(edge(project.id, GraphNamespace.ME_BRAIN, project.id, decision.id))


def test_missing_endpoint_is_rejected(store) -> None:
    project = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    store.add_node(project)
    with pytest.raises(GraphObjectNotFoundError, match="missing"):
        store.add_edge(
            edge("edge:missing", GraphNamespace.ME_BRAIN, project.id, "brain:missing")
        )


def test_cross_graph_requires_bridge(store) -> None:
    brain = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    who = node("who:user:master", GraphNamespace.ME_WHO)
    store.add_node(brain)
    store.add_node(who)
    with pytest.raises(GraphNamespaceError, match="bridge"):
        store.add_edge(edge("edge:invalid", GraphNamespace.ME_BRAIN, brain.id, who.id))
    bridge = edge("edge:bridge:participates", GraphNamespace.BRIDGE, who.id, brain.id)
    store.add_edge(bridge)
    assert store.list_edges(GraphNamespace.BRIDGE) == (bridge,)


def test_file_database_survives_store_recreation(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    engine1 = create_sqlite_test_engine(url)
    create_schema(engine1)
    first = SqlAlchemyGraphStore(engine1)
    value = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    first.add_node(value)
    engine1.dispose()

    engine2 = create_sqlite_test_engine(url)
    second = SqlAlchemyGraphStore(engine2)
    assert second.get_node(value.id) == value
