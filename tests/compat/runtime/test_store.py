from __future__ import annotations

import pytest

from me_core.contracts import (
    AuthorityLevel,
    ConfirmationStatus,
    EvidenceRef,
    GraphEdge,
    GraphNamespace,
    GraphNode,
    Sensitivity,
    TemporalStatus,
)
from me_core.errors import DuplicateGraphObjectError, GraphNamespaceError
from me_core.store import InMemoryGraphStore


def evidence(source_id: str) -> EvidenceRef:
    return EvidenceRef(source_id=source_id, source_anchor={"type": "fixture", "value": {"id": source_id}})


def node(node_id: str, graph: GraphNamespace) -> GraphNode:
    return GraphNode(
        id=node_id,
        graph=graph,
        type="Entity",
        label=node_id,
        properties={},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        status=TemporalStatus.CURRENT,
        valid_from=None,
        valid_to=None,
        sensitivity=(Sensitivity.PROJECT_PRIVATE if graph is GraphNamespace.ME_BRAIN else Sensitivity.PERSONAL_PRIVATE),
        source_refs=(evidence(f"src:{node_id}"),),
    )


def edge(edge_id: str, graph: GraphNamespace, from_id: str, to_id: str) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        graph=graph,
        type="RELATED_TO",
        from_id=from_id,
        to_id=to_id,
        properties={},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        confidence=1.0,
        valid_from=None,
        valid_to=None,
        sensitivity=Sensitivity.RESTRICTED if graph is GraphNamespace.BRIDGE else Sensitivity.PROJECT_PRIVATE,
        source_refs=(evidence(f"src:{edge_id}"),),
    )


def test_store_keeps_me_brain_and_me_who_nodes_separate() -> None:
    store = InMemoryGraphStore()
    brain = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    who = node("who:user:master", GraphNamespace.ME_WHO)
    store.add_node(brain)
    store.add_node(who)
    assert store.list_nodes(GraphNamespace.ME_BRAIN) == (brain,)
    assert store.list_nodes(GraphNamespace.ME_WHO) == (who,)


def test_store_rejects_duplicate_node_id() -> None:
    store = InMemoryGraphStore()
    project = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    store.add_node(project)
    with pytest.raises(DuplicateGraphObjectError):
        store.add_node(project)


def test_store_rejects_cross_graph_edge_without_bridge_namespace() -> None:
    store = InMemoryGraphStore()
    store.add_node(node("brain:project:lighting", GraphNamespace.ME_BRAIN))
    store.add_node(node("who:user:master", GraphNamespace.ME_WHO))
    with pytest.raises(GraphNamespaceError, match="bridge"):
        store.add_edge(
            edge(
                "edge:invalid",
                GraphNamespace.ME_BRAIN,
                "brain:project:lighting",
                "who:user:master",
            )
        )


def test_store_accepts_explicit_bridge_edge() -> None:
    store = InMemoryGraphStore()
    brain = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    who = node("who:user:master", GraphNamespace.ME_WHO)
    store.add_node(brain)
    store.add_node(who)
    bridge = edge("edge:bridge:participates", GraphNamespace.BRIDGE, who.id, brain.id)
    store.add_edge(bridge)
    assert store.list_edges(GraphNamespace.BRIDGE) == (bridge,)


def test_neighbors_support_direction_and_type_filter() -> None:
    store = InMemoryGraphStore()
    project = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    decision = node("brain:decision:radiance", GraphNamespace.ME_BRAIN)
    store.add_node(project)
    store.add_node(decision)
    payload = edge("edge:has-decision", GraphNamespace.ME_BRAIN, project.id, decision.id).to_dict()
    payload["type"] = "HAS_DECISION"
    relation = GraphEdge.from_dict(payload)
    store.add_edge(relation)
    assert store.neighbors(project.id, edge_types={"HAS_DECISION"}, direction="out") == (relation,)
    assert store.neighbors(project.id, edge_types={"BLOCKS"}, direction="out") == ()
