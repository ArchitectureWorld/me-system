from __future__ import annotations

from sqlalchemy import inspect

from me_system.persistence.models import Base, create_schema
from me_system.persistence.testing import create_sqlite_test_engine


EXPECTED_TABLES = {
    "graph_objects",
    "graph_evidence_refs",
    "source_records",
    "evidence_fragments",
    "ingestion_runs",
    "candidate_graph_changes",
    "candidate_evidence_refs",
    "candidate_review_events",
}


def test_create_schema_includes_graph_and_ingestion_tables() -> None:
    engine = create_sqlite_test_engine()
    create_schema(engine)
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_metadata_declares_required_foreign_keys() -> None:
    tables = Base.metadata.tables
    foreign_keys = {
        (table_name, column.name, fk.target_fullname)
        for table_name, table in tables.items()
        for column in table.columns
        for fk in column.foreign_keys
    }
    assert ("evidence_fragments", "source_id", "source_records.source_id") in foreign_keys
    assert ("ingestion_runs", "source_id", "source_records.source_id") in foreign_keys
    assert (
        "candidate_graph_changes",
        "ingestion_run_id",
        "ingestion_runs.run_id",
    ) in foreign_keys
    assert (
        "candidate_graph_changes",
        "approved_object_id",
        "graph_objects.id",
    ) in foreign_keys
    assert (
        "candidate_evidence_refs",
        "change_id",
        "candidate_graph_changes.change_id",
    ) in foreign_keys
    assert (
        "candidate_review_events",
        "change_id",
        "candidate_graph_changes.change_id",
    ) in foreign_keys


def test_candidate_and_source_idempotency_keys_are_unique() -> None:
    tables = Base.metadata.tables
    source_unique = {
        tuple(column.name for column in constraint.columns)
        for constraint in tables["source_records"].constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    candidate_unique = {
        tuple(column.name for column in constraint.columns)
        for constraint in tables["candidate_graph_changes"].constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("idempotency_key",) in source_unique
    assert ("idempotency_key",) in candidate_unique
