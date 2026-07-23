from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import Engine, Select, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..contracts import EvidenceRef, GraphEdge, GraphNamespace, GraphNode
from ..errors import (
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
    GraphStoreUnavailableError,
)
from ..store import Direction
from .database import create_database_engine
from .models import EvidenceRefRecord, GraphObjectRecord


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_edge_namespace(edge: GraphEdge, from_node: GraphNode, to_node: GraphNode) -> None:
    if edge.graph is GraphNamespace.BRIDGE:
        if from_node.graph is to_node.graph:
            raise GraphNamespaceError("bridge edges must connect different canonical graphs")
        return
    if from_node.graph is not edge.graph or to_node.graph is not edge.graph:
        raise GraphNamespaceError("cross-graph relations must use the explicit bridge namespace")


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


def _evidence_records(object_id: str, refs: Iterable[EvidenceRef]) -> list[EvidenceRefRecord]:
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


def _refs(session: Session, object_id: str) -> tuple[EvidenceRef, ...]:
    rows = session.scalars(
        select(EvidenceRefRecord)
        .where(EvidenceRefRecord.object_id == object_id)
        .order_by(EvidenceRefRecord.ordinal)
    ).all()
    return tuple(
        EvidenceRef.from_dict(
            {
                "source_id": row.source_id,
                "document_id": row.document_id,
                "version_id": row.version_id,
                "content_fragment_id": row.content_fragment_id,
                "source_anchor": dict(row.source_anchor),
            }
        )
        for row in rows
    )


def _to_node(session: Session, row: GraphObjectRecord) -> GraphNode:
    return GraphNode.from_dict(
        {
            "id": row.id,
            "graph": row.graph_namespace,
            "type": row.object_type,
            "label": row.label,
            "properties": dict(row.properties),
            "authority": row.authority,
            "confirmation_status": row.confirmation_status,
            "status": row.temporal_status,
            "valid_from": _aware(row.valid_from),
            "valid_to": _aware(row.valid_to),
            "sensitivity": row.sensitivity,
            "source_refs": [ref.to_dict() for ref in _refs(session, row.id)],
        }
    )


def _to_edge(session: Session, row: GraphObjectRecord) -> GraphEdge:
    return GraphEdge.from_dict(
        {
            "id": row.id,
            "graph": row.graph_namespace,
            "type": row.object_type,
            "from_id": row.from_id,
            "to_id": row.to_id,
            "properties": dict(row.properties),
            "authority": row.authority,
            "confirmation_status": row.confirmation_status,
            "confidence": row.confidence,
            "valid_from": _aware(row.valid_from),
            "valid_to": _aware(row.valid_to),
            "sensitivity": row.sensitivity,
            "source_refs": [ref.to_dict() for ref in _refs(session, row.id)],
        }
    )


class SqlAlchemyGraphStore:
    """SQLAlchemy-backed canonical graph store with deterministic round trips."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def add_node(self, node: GraphNode) -> None:
        try:
            with self._sessions.begin() as session:
                self._ensure_available_id(session, node.id)
                session.add(_node_record(node))
                self._flush_graph_object(session, node.id)
                session.add_all(_evidence_records(node.id, node.source_refs))
                session.flush()
        except DuplicateGraphObjectError:
            raise
        except IntegrityError as exc:
            raise GraphStoreUnavailableError("unable to persist graph node") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist graph node") from exc

    def add_edge(self, edge: GraphEdge) -> None:
        try:
            with self._sessions.begin() as session:
                self._ensure_available_id(session, edge.id)
                from_node = self._get_node(session, edge.from_id)
                to_node = self._get_node(session, edge.to_id)
                _validate_edge_namespace(edge, from_node, to_node)
                session.add(_edge_record(edge))
                self._flush_graph_object(session, edge.id)
                session.add_all(_evidence_records(edge.id, edge.source_refs))
                session.flush()
        except (DuplicateGraphObjectError, GraphObjectNotFoundError, GraphNamespaceError):
            raise
        except IntegrityError as exc:
            raise GraphStoreUnavailableError("unable to persist graph edge") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist graph edge") from exc

    def get_node(self, node_id: str) -> GraphNode:
        try:
            with self._sessions() as session:
                return self._get_node(session, node_id)
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read graph node") from exc

    def get_edge(self, edge_id: str) -> GraphEdge:
        try:
            with self._sessions() as session:
                row = session.get(GraphObjectRecord, edge_id)
                if row is None or row.object_kind != "edge":
                    raise GraphObjectNotFoundError(f"edge not found: {edge_id}")
                return _to_edge(session, row)
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read graph edge") from exc

    def get_object(self, object_id: str) -> GraphNode | GraphEdge:
        try:
            with self._sessions() as session:
                row = session.get(GraphObjectRecord, object_id)
                if row is None:
                    raise GraphObjectNotFoundError(f"graph object not found: {object_id}")
                return _to_node(session, row) if row.object_kind == "node" else _to_edge(session, row)
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read graph object") from exc

    def list_nodes(self, graph: GraphNamespace | None = None) -> tuple[GraphNode, ...]:
        statement = select(GraphObjectRecord).where(GraphObjectRecord.object_kind == "node")
        if graph is not None:
            statement = statement.where(GraphObjectRecord.graph_namespace == graph.value)
        return self._read_nodes(statement.order_by(GraphObjectRecord.id))

    def list_edges(self, graph: GraphNamespace | None = None) -> tuple[GraphEdge, ...]:
        statement = select(GraphObjectRecord).where(GraphObjectRecord.object_kind == "edge")
        if graph is not None:
            statement = statement.where(GraphObjectRecord.graph_namespace == graph.value)
        return self._read_edges(statement.order_by(GraphObjectRecord.id))

    def neighbors(
        self,
        node_id: str,
        edge_types: set[str] | None = None,
        direction: Direction = "both",
    ) -> tuple[GraphEdge, ...]:
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be one of: in, out, both")
        try:
            with self._sessions() as session:
                self._get_node(session, node_id)
                statement = select(GraphObjectRecord).where(
                    GraphObjectRecord.object_kind == "edge"
                )
                if edge_types is not None:
                    if not edge_types:
                        return ()
                    statement = statement.where(
                        GraphObjectRecord.object_type.in_(sorted(edge_types))
                    )
                if direction == "out":
                    statement = statement.where(GraphObjectRecord.from_id == node_id)
                elif direction == "in":
                    statement = statement.where(GraphObjectRecord.to_id == node_id)
                else:
                    statement = statement.where(
                        or_(
                            GraphObjectRecord.from_id == node_id,
                            GraphObjectRecord.to_id == node_id,
                        )
                    )
                rows = session.scalars(statement.order_by(GraphObjectRecord.id)).all()
                return tuple(_to_edge(session, row) for row in rows)
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to query graph neighbors") from exc

    def _ensure_available_id(self, session: Session, object_id: str) -> None:
        if session.get(GraphObjectRecord, object_id) is not None:
            raise DuplicateGraphObjectError(f"graph object already exists: {object_id}")

    @staticmethod
    def _flush_graph_object(session: Session, object_id: str) -> None:
        try:
            session.flush()
        except IntegrityError as exc:
            raise DuplicateGraphObjectError(
                f"graph object already exists: {object_id}"
            ) from exc

    def _get_node(self, session: Session, node_id: str) -> GraphNode:
        row = session.get(GraphObjectRecord, node_id)
        if row is None or row.object_kind != "node":
            raise GraphObjectNotFoundError(f"node not found: {node_id}")
        return _to_node(session, row)

    def _read_nodes(self, statement: Select) -> tuple[GraphNode, ...]:
        try:
            with self._sessions() as session:
                return tuple(_to_node(session, row) for row in session.scalars(statement).all())
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list graph nodes") from exc

    def _read_edges(self, statement: Select) -> tuple[GraphEdge, ...]:
        try:
            with self._sessions() as session:
                return tuple(_to_edge(session, row) for row in session.scalars(statement).all())
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list graph edges") from exc


def create_postgres_graph_store(database_url: str) -> SqlAlchemyGraphStore:
    return SqlAlchemyGraphStore(create_database_engine(database_url, production=True))
