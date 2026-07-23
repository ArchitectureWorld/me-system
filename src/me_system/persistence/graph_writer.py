from __future__ import annotations

from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..contracts import EvidenceRef, GraphEdge, GraphNamespace, GraphNode
from ..errors import (
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
)
from .models import EvidenceRefRecord, GraphObjectRecord


def _node_record(node: GraphNode) -> GraphObjectRecord:
    return GraphObjectRecord(
        id=node.id,
        object_kind="node",
        graph_namespace=node.graph.value,
        object_type=node.type,
        label=node.label,
        from_id=None,
        to_id=None,
        properties=dict(node.properties),
        authority=node.authority.value,
        confirmation_status=node.confirmation_status.value,
        temporal_status=node.status.value,
        confidence=None,
        valid_from=node.valid_from,
        valid_to=node.valid_to,
        sensitivity=node.sensitivity.value,
    )


def _edge_record(edge: GraphEdge) -> GraphObjectRecord:
    return GraphObjectRecord(
        id=edge.id,
        object_kind="edge",
        graph_namespace=edge.graph.value,
        object_type=edge.type,
        label=None,
        from_id=edge.from_id,
        to_id=edge.to_id,
        properties=dict(edge.properties),
        authority=edge.authority.value,
        confirmation_status=edge.confirmation_status.value,
        temporal_status=None,
        confidence=edge.confidence,
        valid_from=edge.valid_from,
        valid_to=edge.valid_to,
        sensitivity=edge.sensitivity.value,
    )


def _evidence_records(
    object_id: str,
    refs: Iterable[EvidenceRef],
) -> list[EvidenceRefRecord]:
    return [
        EvidenceRefRecord(
            object_id=object_id,
            ordinal=ordinal,
            source_id=ref.source_id,
            document_id=ref.document_id,
            version_id=ref.version_id,
            content_fragment_id=ref.content_fragment_id,
            source_anchor={
                "type": ref.source_anchor["type"],
                "value": dict(ref.source_anchor["value"]),
            },
        )
        for ordinal, ref in enumerate(refs)
    ]


def _ensure_available_id(session: Session, object_id: str) -> None:
    if session.get(GraphObjectRecord, object_id) is not None:
        raise DuplicateGraphObjectError(f"graph object already exists: {object_id}")


def _flush_graph_object(session: Session, object_id: str) -> None:
    try:
        session.flush()
    except IntegrityError as exc:
        raise DuplicateGraphObjectError(
            f"graph object already exists: {object_id}"
        ) from exc


def _endpoint(session: Session, node_id: str) -> GraphObjectRecord:
    row = session.get(GraphObjectRecord, node_id)
    if row is None or row.object_kind != "node":
        raise GraphObjectNotFoundError(f"node not found: {node_id}")
    return row


def _validate_edge_namespace(
    edge: GraphEdge,
    from_row: GraphObjectRecord,
    to_row: GraphObjectRecord,
) -> None:
    if edge.graph is GraphNamespace.BRIDGE:
        if from_row.graph_namespace == to_row.graph_namespace:
            raise GraphNamespaceError(
                "bridge edges must connect different canonical graphs"
            )
        return
    if (
        from_row.graph_namespace != edge.graph.value
        or to_row.graph_namespace != edge.graph.value
    ):
        raise GraphNamespaceError(
            "cross-graph relations must use the explicit bridge namespace"
        )


def write_graph_node(session: Session, node: GraphNode) -> GraphNode:
    """Write a node and all evidence inside the caller's transaction."""

    _ensure_available_id(session, node.id)
    session.add(_node_record(node))
    _flush_graph_object(session, node.id)
    session.add_all(_evidence_records(node.id, node.source_refs))
    session.flush()
    return node


def write_graph_edge(session: Session, edge: GraphEdge) -> GraphEdge:
    """Write an edge and all evidence inside the caller's transaction."""

    _ensure_available_id(session, edge.id)
    from_row = _endpoint(session, edge.from_id)
    to_row = _endpoint(session, edge.to_id)
    _validate_edge_namespace(edge, from_row, to_row)
    session.add(_edge_record(edge))
    _flush_graph_object(session, edge.id)
    session.add_all(_evidence_records(edge.id, edge.source_refs))
    session.flush()
    return edge
