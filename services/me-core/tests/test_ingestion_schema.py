from __future__ import annotations

from sqlalchemy import inspect

from me_core.persistence.models import create_schema
from me_core.persistence.testing import create_sqlite_test_engine


EXPECTED_TABLES = {
    "graph_objects",
    "graph_evidence_refs",
    "source_records",
    "evidence_fragments",
    "ingestion_runs",
}


def inspector():
    engine = create_sqlite_test_engine()
    create_schema(engine)
    return inspect(engine)


def test_schema_contains_ingestion_ledger_tables() -> None:
    assert set(inspector().get_table_names()) == EXPECTED_TABLES


def test_source_records_have_idempotency_and_external_identity_indexes() -> None:
    value = inspector()
    unique_names = {
        item["name"] for item in value.get_unique_constraints("source_records")
    }
    index_columns = {
        tuple(item["column_names"]) for item in value.get_indexes("source_records")
    }
    assert "uq_source_records_idempotency_key" in unique_names
    assert ("external_system", "external_id") in index_columns


def test_evidence_fragments_are_ordered_within_a_source() -> None:
    value = inspector()
    unique_names = {
        item["name"] for item in value.get_unique_constraints("evidence_fragments")
    }
    foreign_keys = value.get_foreign_keys("evidence_fragments")
    assert "uq_evidence_fragments_source_ordinal" in unique_names
    assert any(
        key["constrained_columns"] == ["source_id"]
        and key["referred_table"] == "source_records"
        and key["referred_columns"] == ["source_id"]
        for key in foreign_keys
    )


def test_ingestion_runs_have_state_count_and_coverage_constraints() -> None:
    names = {
        item["name"] for item in inspector().get_check_constraints("ingestion_runs")
    }
    assert {
        "ck_ingestion_runs_status",
        "ck_ingestion_runs_counts_non_negative",
        "ck_ingestion_runs_counts_within_input",
        "ck_ingestion_runs_coverage",
        "ck_ingestion_runs_timestamps",
    } <= names


def test_ingestion_runs_have_status_and_source_indexes() -> None:
    index_columns = {
        tuple(item["column_names"]) for item in inspector().get_indexes("ingestion_runs")
    }
    assert ("source_id", "started_at") in index_columns
    assert ("status", "started_at") in index_columns
