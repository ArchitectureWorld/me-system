"""create canonical graph store

Revision ID: 0001_graph_store
Revises:
Create Date: 2026-07-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_graph_store"
down_revision = None
branch_labels = None
depends_on = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
_EVIDENCE_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "graph_objects",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("object_kind", sa.String(length=8), nullable=False),
        sa.Column("graph_namespace", sa.String(length=16), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("from_id", sa.Text(), nullable=True),
        sa.Column("to_id", sa.Text(), nullable=True),
        sa.Column("properties", _JSON, nullable=False),
        sa.Column("authority", sa.String(length=32), nullable=False),
        sa.Column("confirmation_status", sa.String(length=32), nullable=False),
        sa.Column("temporal_status", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("object_kind IN ('node', 'edge')", name="ck_graph_objects_kind"),
        sa.CheckConstraint(
            "graph_namespace IN ('me_brain', 'me_who', 'bridge')",
            name="ck_graph_objects_namespace",
        ),
        sa.CheckConstraint(
            "(object_kind = 'node' AND graph_namespace <> 'bridge' "
            "AND label IS NOT NULL AND temporal_status IS NOT NULL "
            "AND from_id IS NULL AND to_id IS NULL AND confidence IS NULL) "
            "OR (object_kind = 'edge' AND from_id IS NOT NULL AND to_id IS NOT NULL "
            "AND from_id <> to_id AND confidence IS NOT NULL "
            "AND label IS NULL AND temporal_status IS NULL)",
            name="ck_graph_objects_shape",
        ),
        sa.ForeignKeyConstraint(["from_id"], ["graph_objects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_id"], ["graph_objects.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_graph_objects_lookup",
        "graph_objects",
        ["graph_namespace", "object_kind", "object_type"],
    )
    op.create_index("ix_graph_objects_from_id", "graph_objects", ["from_id"])
    op.create_index("ix_graph_objects_to_id", "graph_objects", ["to_id"])
    op.create_index(
        "ix_graph_objects_temporal", "graph_objects", ["temporal_status", "valid_to"]
    )

    op.create_table(
        "graph_evidence_refs",
        sa.Column("id", _EVIDENCE_ID, primary_key=True, autoincrement=True),
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Text(), nullable=True),
        sa.Column("content_fragment_id", sa.Text(), nullable=True),
        sa.Column("source_anchor", _JSON, nullable=False),
        sa.ForeignKeyConstraint(["object_id"], ["graph_objects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("object_id", "ordinal", name="uq_graph_evidence_object_ordinal"),
    )
    op.create_index(
        "ix_graph_evidence_object_id", "graph_evidence_refs", ["object_id"]
    )
    op.create_index(
        "ix_graph_evidence_source_id", "graph_evidence_refs", ["source_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_graph_evidence_source_id", table_name="graph_evidence_refs")
    op.drop_index("ix_graph_evidence_object_id", table_name="graph_evidence_refs")
    op.drop_table("graph_evidence_refs")
    op.drop_index("ix_graph_objects_temporal", table_name="graph_objects")
    op.drop_index("ix_graph_objects_to_id", table_name="graph_objects")
    op.drop_index("ix_graph_objects_from_id", table_name="graph_objects")
    op.drop_index("ix_graph_objects_lookup", table_name="graph_objects")
    op.drop_table("graph_objects")
