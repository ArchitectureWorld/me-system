from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative metadata for the persistent ME-System store."""


_JSON = JSON().with_variant(JSONB(), "postgresql")
_EVIDENCE_ID = BigInteger().with_variant(Integer, "sqlite")


class GraphObjectRecord(Base):
    __tablename__ = "graph_objects"
    __table_args__ = (
        CheckConstraint("object_kind IN ('node', 'edge')", name="ck_graph_objects_kind"),
        CheckConstraint(
            "graph_namespace IN ('me_brain', 'me_who', 'bridge')",
            name="ck_graph_objects_namespace",
        ),
        CheckConstraint(
            "(object_kind = 'node' AND graph_namespace <> 'bridge' "
            "AND label IS NOT NULL AND temporal_status IS NOT NULL "
            "AND from_id IS NULL AND to_id IS NULL AND confidence IS NULL) "
            "OR (object_kind = 'edge' AND from_id IS NOT NULL AND to_id IS NOT NULL "
            "AND from_id <> to_id AND confidence IS NOT NULL "
            "AND label IS NULL AND temporal_status IS NULL)",
            name="ck_graph_objects_shape",
        ),
        Index("ix_graph_objects_lookup", "graph_namespace", "object_kind", "object_type"),
        Index("ix_graph_objects_from_id", "from_id"),
        Index("ix_graph_objects_to_id", "to_id"),
        Index("ix_graph_objects_temporal", "temporal_status", "valid_to"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    object_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    graph_namespace: Mapped[str] = mapped_column(String(16), nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_id: Mapped[str | None] = mapped_column(
        ForeignKey("graph_objects.id", ondelete="RESTRICT"), nullable=True
    )
    to_id: Mapped[str | None] = mapped_column(
        ForeignKey("graph_objects.id", ondelete="RESTRICT"), nullable=True
    )
    properties: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False, default=dict)
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    temporal_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class EvidenceRefRecord(Base):
    __tablename__ = "graph_evidence_refs"
    __table_args__ = (
        UniqueConstraint("object_id", "ordinal", name="uq_graph_evidence_object_ordinal"),
        Index("ix_graph_evidence_object_id", "object_id"),
        Index("ix_graph_evidence_source_id", "source_id"),
    )

    id: Mapped[int] = mapped_column(_EVIDENCE_ID, primary_key=True, autoincrement=True)
    object_id: Mapped[str] = mapped_column(
        ForeignKey("graph_objects.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_fragment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_anchor: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)


# Import after Base and graph records exist so the shared metadata contains the
# source/evidence/ingestion/candidate tables without a second declarative base.
from . import ingestion_models as _ingestion_models  # noqa: E402,F401


def create_schema(engine: Engine) -> None:
    """Create the current ME-System schema for tests and local prototypes."""

    Base.metadata.create_all(engine)
