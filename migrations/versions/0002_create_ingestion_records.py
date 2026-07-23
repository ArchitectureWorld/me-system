"""create source evidence ingestion and candidate records

Revision ID: 0002_ingestion
Revises: 0001_graph_store
Create Date: 2026-07-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_ingestion"
down_revision = "0001_graph_store"
branch_labels = None
depends_on = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
_BIG_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "source_records",
        sa.Column("source_id", sa.Text(), primary_key=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("external_system", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("content_ref", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("metadata", _JSON, nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_source_records_idempotency_key"),
    )
    op.create_index(
        "ix_source_records_external",
        "source_records",
        ["external_system", "external_id"],
    )
    op.create_index("ix_source_records_ingested_at", "source_records", ["ingested_at"])

    op.create_table(
        "evidence_fragments",
        sa.Column("fragment_id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("fragment_type", sa.String(length=32), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("source_anchor", _JSON, nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_id", sa.Text(), nullable=True),
        sa.Column("metadata", _JSON, nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"], ["source_records.source_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "source_id", "ordinal", name="uq_evidence_fragments_source_ordinal"
        ),
    )
    op.create_index(
        "ix_evidence_fragments_source",
        "evidence_fragments",
        ["source_id", "ordinal"],
    )
    op.create_index(
        "ix_evidence_fragments_occurred_at",
        "evidence_fragments",
        ["occurred_at"],
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("adapter_name", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fragment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_report", _JSON, nullable=False),
        sa.Column("log_ref", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"], ["source_records.source_id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'partial', 'failed')",
            name="ck_ingestion_runs_status",
        ),
        sa.CheckConstraint(
            "input_item_count >= 0 AND processed_item_count >= 0 "
            "AND skipped_item_count >= 0 AND failed_item_count >= 0 "
            "AND fragment_count >= 0 AND candidate_count >= 0",
            name="ck_ingestion_runs_nonnegative_counts",
        ),
        sa.CheckConstraint(
            "processed_item_count + skipped_item_count + failed_item_count <= input_item_count",
            name="ck_ingestion_runs_accounted_items",
        ),
        sa.CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_ingestion_runs_coverage",
        ),
        sa.CheckConstraint(
            "((status IN ('pending', 'running')) AND completed_at IS NULL) "
            "OR ((status IN ('completed', 'partial', 'failed')) AND completed_at IS NOT NULL)",
            name="ck_ingestion_runs_completion_shape",
        ),
    )
    op.create_index(
        "ix_ingestion_runs_source_started",
        "ingestion_runs",
        ["source_id", "started_at"],
    )
    op.create_index(
        "ix_ingestion_runs_status", "ingestion_runs", ["status", "started_at"]
    )

    op.create_table(
        "candidate_graph_changes",
        sa.Column("change_id", sa.Text(), primary_key=True),
        sa.Column("target_graph", sa.String(length=16), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("submitted_by", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", _JSON, nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("approved_object_id", sa.Text(), nullable=True),
        sa.Column("ingestion_run_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["approved_object_id"], ["graph_objects.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"], ["ingestion_runs.run_id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_candidate_changes_idempotency_key"
        ),
        sa.CheckConstraint(
            "target_graph IN ('me_brain', 'me_who', 'bridge')",
            name="ck_candidate_changes_target_graph",
        ),
        sa.CheckConstraint(
            "operation IN ('add_node', 'add_edge')",
            name="ck_candidate_changes_operation",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_candidate_changes_review_status",
        ),
        sa.CheckConstraint(
            "(review_status = 'pending' AND reviewed_at IS NULL AND reviewed_by IS NULL "
            "AND review_reason IS NULL AND approved_object_id IS NULL) "
            "OR (review_status = 'approved' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND review_reason IS NOT NULL "
            "AND approved_object_id IS NOT NULL) "
            "OR (review_status = 'rejected' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND review_reason IS NOT NULL "
            "AND approved_object_id IS NULL)",
            name="ck_candidate_changes_review_shape",
        ),
    )
    op.create_index(
        "ix_candidate_changes_pending",
        "candidate_graph_changes",
        ["review_status", "created_at"],
    )
    op.create_index(
        "ix_candidate_changes_graph_status",
        "candidate_graph_changes",
        ["target_graph", "review_status"],
    )
    op.create_index(
        "ix_candidate_changes_ingestion_run",
        "candidate_graph_changes",
        ["ingestion_run_id"],
    )

    op.create_table(
        "candidate_evidence_refs",
        sa.Column("id", _BIG_ID, primary_key=True, autoincrement=True),
        sa.Column("change_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Text(), nullable=True),
        sa.Column("content_fragment_id", sa.Text(), nullable=True),
        sa.Column("source_anchor", _JSON, nullable=False),
        sa.ForeignKeyConstraint(
            ["change_id"], ["candidate_graph_changes.change_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["source_records.source_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["content_fragment_id"],
            ["evidence_fragments.fragment_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "change_id", "ordinal", name="uq_candidate_evidence_change_ordinal"
        ),
    )
    op.create_index(
        "ix_candidate_evidence_source_id",
        "candidate_evidence_refs",
        ["source_id"],
    )
    op.create_index(
        "ix_candidate_evidence_fragment_id",
        "candidate_evidence_refs",
        ["content_fragment_id"],
    )

    op.create_table(
        "candidate_review_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("change_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("actor_kind", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", _JSON, nullable=False),
        sa.ForeignKeyConstraint(
            ["change_id"], ["candidate_graph_changes.change_id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "event_type IN ('submitted', 'approved', 'rejected')",
            name="ck_candidate_review_events_type",
        ),
        sa.CheckConstraint(
            "actor_kind IN ('adapter', 'agent', 'human', 'rule')",
            name="ck_candidate_review_events_actor_kind",
        ),
    )
    op.create_index(
        "ix_candidate_review_events_change_created",
        "candidate_review_events",
        ["change_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_review_events_change_created",
        table_name="candidate_review_events",
    )
    op.drop_table("candidate_review_events")

    op.drop_index(
        "ix_candidate_evidence_fragment_id", table_name="candidate_evidence_refs"
    )
    op.drop_index(
        "ix_candidate_evidence_source_id", table_name="candidate_evidence_refs"
    )
    op.drop_table("candidate_evidence_refs")

    op.drop_index(
        "ix_candidate_changes_ingestion_run", table_name="candidate_graph_changes"
    )
    op.drop_index(
        "ix_candidate_changes_graph_status", table_name="candidate_graph_changes"
    )
    op.drop_index(
        "ix_candidate_changes_pending", table_name="candidate_graph_changes"
    )
    op.drop_table("candidate_graph_changes")

    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_source_started", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index(
        "ix_evidence_fragments_occurred_at", table_name="evidence_fragments"
    )
    op.drop_index("ix_evidence_fragments_source", table_name="evidence_fragments")
    op.drop_table("evidence_fragments")

    op.drop_index("ix_source_records_ingested_at", table_name="source_records")
    op.drop_index("ix_source_records_external", table_name="source_records")
    op.drop_table("source_records")
