from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, Select, or_, select
from sqlalchemy.exc import SQLAlchemyError
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
from .graph_writer import write_graph_edge, write_graph_node
from .models import EvidenceRefRecord, GraphObjectRecord


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
                write_graph_node(session, node)
        except DuplicateGraphObjectError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist graph node") from exc

    def add_edge(self, edge: GraphEdge) -> None:
        try:
            with self._sessions.begin() as session:
                write_graph_edge(session, edge)
        except (
            DuplicateGraphObjectError,
            GraphObjectNotFoundError,
            GraphNamespaceError,
        ):
            raise
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
                    raise GraphObjectNotFoundError(
                        f"graph object not found: {object_id}"
                    )
                return (
                    _to_node(session, row)
                    if row.object_kind == "node"
                    else _to_edge(session, row)
                )
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read graph object") from exc

    def list_nodes(
        self,
        graph: GraphNamespace | None = None,
    ) -> tuple[GraphNode, ...]:
        statement = select(GraphObjectRecord).where(
            GraphObjectRecord.object_kind == "node"
        )
        if graph is not None:
            statement = statement.where(
                GraphObjectRecord.graph_namespace == graph.value
            )
        return self._read_nodes(statement.order_by(GraphObjectRecord.id))

    def list_edges(
        self,
        graph: GraphNamespace | None = None,
    ) -> tuple[GraphEdge, ...]:
        statement = select(GraphObjectRecord).where(
            GraphObjectRecord.object_kind == "edge"
        )
        if graph is not None:
            statement = statement.where(
                GraphObjectRecord.graph_namespace == graph.value
            )
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
                    statement = statement.where(
                        GraphObjectRecord.from_id == node_id
                    )
                elif direction == "in":
                    statement = statement.where(GraphObjectRecord.to_id == node_id)
                else:
                    statement = statement.where(
                        or_(
                            GraphObjectRecord.from_id == node_id,
                            GraphObjectRecord.to_id == node_id,
                        )
                    )
                rows = session.scalars(
                    statement.order_by(GraphObjectRecord.id)
                ).all()
                return tuple(_to_edge(session, row) for row in rows)
        except GraphObjectNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError(
                "unable to query graph neighbors"
            ) from exc

    def _get_node(self, session: Session, node_id: str) -> GraphNode:
        row = session.get(GraphObjectRecord, node_id)
        if row is None or row.object_kind != "node":
            raise GraphObjectNotFoundError(f"node not found: {node_id}")
        return _to_node(session, row)

    def _read_nodes(self, statement: Select) -> tuple[GraphNode, ...]:
        try:
            with self._sessions() as session:
                return tuple(
                    _to_node(session, row)
                    for row in session.scalars(statement).all()
                )
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list graph nodes") from exc

    def _read_edges(self, statement: Select) -> tuple[GraphEdge, ...]:
        try:
            with self._sessions() as session:
                return tuple(
                    _to_edge(session, row)
                    for row in session.scalars(statement).all()
                )
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list graph edges") from exc


def create_postgres_graph_store(database_url: str) -> SqlAlchemyGraphStore:
    return SqlAlchemyGraphStore(
        create_database_engine(database_url, production=True)
    )
