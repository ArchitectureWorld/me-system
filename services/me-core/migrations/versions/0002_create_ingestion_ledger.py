"""create ME-Core ingestion ledger

Revision ID: 0002_ingestion_ledger
Revises: 0001_graph_store
Create Date: 2026-07-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_ingestion_ledger"
down_revision = "0001_graph_store"
branch_labels = None
depends_on = None


_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


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
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_source_records_content_sha256_length",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_source_records_idempotency_key",
        ),
    )
    op.create_index(
        "ix_source_records_external_identity",
        "source_records",
        ["external_system", "external_id"],
    )

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
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("metadata", _JSON, nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_evidence_fragments_ordinal",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_evidence_fragments_content_sha256_length",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_records.source_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "source_id",
            "ordinal",
            name="uq_evidence_fragments_source_ordinal",
        ),
    )
    op.create_index(
        "ix_evidence_fragments_source_ordinal",
        "evidence_fragments",
        ["source_id", "ordinal"],
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("adapter_name", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("pipeline_version", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_item_count", sa.Integer(), nullable=False),
        sa.Column("processed_item_count", sa.Integer(), nullable=False),
        sa.Column("skipped_item_count", sa.Integer(), nullable=False),
        sa.Column("failed_item_count", sa.Integer(), nullable=False),
        sa.Column("fragment_count", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=False),
        sa.Column("quality_report", _JSON, nullable=False),
        sa.Column("log_ref", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'partial', 'failed')",
            name="ck_ingestion_runs_status",
        ),
        sa.CheckConstraint(
            "input_item_count >= 0 AND processed_item_count >= 0 "
            "AND skipped_item_count >= 0 AND failed_item_count >= 0 "
            "AND fragment_count >= 0 AND candidate_count >= 0",
            name="ck_ingestion_runs_counts_non_negative",
        ),
        sa.CheckConstraint(
            "processed_item_count + skipped_item_count + failed_item_count <= input_item_count",
            name="ck_ingestion_runs_counts_within_input",
        ),
        sa.CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_ingestion_runs_coverage",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) "
            "OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) "
            "OR (status IN ('completed', 'partial', 'failed') "
            "AND started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND completed_at >= started_at)",
            name="ck_ingestion_runs_timestamps",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_records.source_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_ingestion_runs_source_started",
        "ingestion_runs",
        ["source_id", "started_at"],
    )
    op.create_index(
        "ix_ingestion_runs_status_started",
        "ingestion_runs",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_runs_status_started", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_source_started", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index(
        "ix_evidence_fragments_source_ordinal",
        table_name="evidence_fragments",
    )
    op.drop_table("evidence_fragments")

    op.drop_index(
        "ix_source_records_external_identity",
        table_name="source_records",
    )
    op.drop_table("source_records")
