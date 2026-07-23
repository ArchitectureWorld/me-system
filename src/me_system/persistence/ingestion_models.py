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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, _JSON

_ROW_ID = BigInteger().with_variant(Integer, "sqlite")


class SourceRecordRow(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_source_records_idempotency_key"),
        Index("ix_source_external_identity", "external_system", "external_id"),
    )

    source_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
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
        UniqueConstraint("source_id", "ordinal", name="uq_evidence_source_ordinal"),
        UniqueConstraint("source_id", "fragment_id", name="uq_evidence_source_fragment"),
        CheckConstraint("ordinal >= 0", name="ck_evidence_fragments_ordinal"),
        Index("ix_evidence_fragments_source_ordinal", "source_id", "ordinal"),
    )

    fragment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_records.source_id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    fragment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_anchor: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
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
            name="ck_ingestion_runs_nonnegative_counts",
        ),
        CheckConstraint(
            "processed_item_count + skipped_item_count + failed_item_count "
            "<= input_item_count",
            name="ck_ingestion_runs_handled_counts",
        ),
        CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_ingestion_runs_coverage",
        ),
        CheckConstraint(
            "((status IN ('completed', 'partial', 'failed')) AND completed_at IS NOT NULL) "
            "OR ((status IN ('pending', 'running')) AND completed_at IS NULL)",
            name="ck_ingestion_runs_completion",
        ),
        Index("ix_ingestion_runs_source_started", "source_id", "started_at"),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_records.source_id", ondelete="CASCADE"), nullable=False
    )
    adapter_name: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fragment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quality_report: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False, default=dict)
    log_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class CandidateGraphChangeRow(Base):
    __tablename__ = "candidate_graph_changes"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_candidate_idempotency_key"),
        CheckConstraint(
            "target_graph IN ('me_brain', 'me_who', 'bridge')",
            name="ck_candidate_target_graph",
        ),
        CheckConstraint(
            "operation IN ('add_node', 'add_edge')",
            name="ck_candidate_operation",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_candidate_review_status",
        ),
        CheckConstraint(
            "(review_status = 'pending' AND reviewed_at IS NULL "
            "AND reviewed_by IS NULL AND approved_object_id IS NULL) "
            "OR (review_status = 'approved' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND approved_object_id IS NOT NULL) "
            "OR (review_status = 'rejected' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND review_reason IS NOT NULL "
            "AND approved_object_id IS NULL)",
            name="ck_candidate_review_shape",
        ),
        Index("ix_candidate_review_status_created", "review_status", "created_at"),
        Index("ix_candidate_target_status", "target_graph", "review_status"),
        Index("ix_candidate_ingestion_run", "ingestion_run_id"),
    )

    change_id: Mapped[str] = mapped_column(Text, primary_key=True)
    target_graph: Mapped[str] = mapped_column(String(16), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    submitted_by: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_object_id: Mapped[str | None] = mapped_column(
        ForeignKey("graph_objects.id", ondelete="RESTRICT"), nullable=True
    )
    ingestion_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("ingestion_runs.run_id", ondelete="SET NULL"), nullable=True
    )


class CandidateEvidenceRefRow(Base):
    __tablename__ = "candidate_evidence_refs"
    __table_args__ = (
        UniqueConstraint("change_id", "ordinal", name="uq_candidate_evidence_ordinal"),
        Index("ix_candidate_evidence_source", "source_id"),
        Index("ix_candidate_evidence_fragment", "content_fragment_id"),
    )

    id: Mapped[int] = mapped_column(_ROW_ID, primary_key=True, autoincrement=True)
    change_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_graph_changes.change_id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source_records.source_id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_fragment_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_fragments.fragment_id", ondelete="RESTRICT"), nullable=True
    )
    source_anchor: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False)


class CandidateReviewEventRow(Base):
    __tablename__ = "candidate_review_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('submitted', 'approved', 'rejected')",
            name="ck_candidate_review_events_type",
        ),
        CheckConstraint(
            "actor_kind IN ('adapter', 'agent', 'human', 'rule')",
            name="ck_candidate_review_events_actor_kind",
        ),
        Index("ix_candidate_review_events_change_created", "change_id", "created_at"),
    )

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    change_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_graph_changes.change_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", _JSON, nullable=False, default=dict
    )
