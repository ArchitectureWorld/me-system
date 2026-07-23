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
    """Declarative metadata for the single ME-Core authority database."""


_JSON = JSON().with_variant(JSONB(), "postgresql")
_BIG_INTEGER_ID = BigInteger().with_variant(Integer, "sqlite")


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

    id: Mapped[int] = mapped_column(_BIG_INTEGER_ID, primary_key=True, autoincrement=True)
    object_id: Mapped[str] = mapped_column(
        ForeignKey("graph_objects.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_fragment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_anchor: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)


class SourceRecordRow(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_source_records_idempotency_key"),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_source_records_content_sha256_length",
        ),
        Index("ix_source_records_external_identity", "external_system", "external_id"),
    )

    source_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    external_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_ref: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", _JSON, nullable=False, default=dict
    )


class EvidenceFragmentRow(Base):
    __tablename__ = "evidence_fragments"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "ordinal",
            name="uq_evidence_fragments_source_ordinal",
        ),
        CheckConstraint("ordinal >= 0", name="ck_evidence_fragments_ordinal"),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_evidence_fragments_content_sha256_length",
        ),
        Index("ix_evidence_fragments_source_ordinal", "source_id", "ordinal"),
    )

    fragment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_records.source_id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    fragment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_anchor: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", _JSON, nullable=False, default=dict
    )


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'partial', 'failed')",
            name="ck_ingestion_runs_status",
        ),
        CheckConstraint(
            "input_item_count >= 0 AND processed_item_count >= 0 "
            "AND skipped_item_count >= 0 AND failed_item_count >= 0 "
            "AND fragment_count >= 0 AND candidate_count >= 0",
            name="ck_ingestion_runs_counts_non_negative",
        ),
        CheckConstraint(
            "processed_item_count + skipped_item_count + failed_item_count <= input_item_count",
            name="ck_ingestion_runs_counts_within_input",
        ),
        CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_ingestion_runs_coverage",
        ),
        CheckConstraint(
            "(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) "
            "OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) "
            "OR (status IN ('completed', 'partial', 'failed') "
            "AND started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND completed_at >= started_at)",
            name="ck_ingestion_runs_timestamps",
        ),
        Index("ix_ingestion_runs_source_started", "source_id", "started_at"),
        Index("ix_ingestion_runs_status_started", "status", "started_at"),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_records.source_id", ondelete="CASCADE"), nullable=False
    )
    adapter_name: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_version: Mapped[str] = mapped_column(Text, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fragment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_report: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False, default=dict)
    log_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


def create_schema(engine: Engine) -> None:
    """Create the current ME-Core schema for tests and local prototypes."""

    Base.metadata.create_all(engine)
