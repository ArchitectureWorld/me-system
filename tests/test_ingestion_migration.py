from __future__ import annotations

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from me_system.persistence.migrations import upgrade_database
from me_system.persistence.models import Base


EXPECTED_TABLES = {
    "source_records",
    "evidence_fragments",
    "ingestion_runs",
    "candidate_graph_changes",
    "candidate_evidence_refs",
    "candidate_review_events",
}


def migrated_database(tmp_path: Path):
    url = f"sqlite+pysqlite:///{tmp_path / 'ingestion.db'}"
    upgrade_database(url, production=False)
    return url, create_engine(url)


def test_upgrade_creates_all_ingestion_tables_and_indexes(tmp_path: Path) -> None:
    _, engine = migrated_database(tmp_path)
    inspector = inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    candidate_indexes = {item["name"] for item in inspector.get_indexes("candidate_graph_changes")}
    assert {
        "ix_candidate_review_status_created",
        "ix_candidate_target_status",
        "ix_candidate_ingestion_run",
    } <= candidate_indexes
    fragment_indexes = {item["name"] for item in inspector.get_indexes("evidence_fragments")}
    assert "ix_evidence_fragments_source_ordinal" in fragment_indexes


def test_ingestion_migration_is_idempotent(tmp_path: Path) -> None:
    url, _ = migrated_database(tmp_path)
    upgrade_database(url, production=False)


def test_migration_matches_sqlalchemy_metadata(tmp_path: Path) -> None:
    _, engine = migrated_database(tmp_path)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []


def test_database_rejects_invalid_ingestion_status(tmp_path: Path) -> None:
    _, engine = migrated_database(tmp_path)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO source_records (
                source_id, source_type, idempotency_key, content_ref,
                content_sha256, ingested_at, sensitivity, metadata
            ) VALUES (
                'source:1', 'test', 'key:1', 'file:///source',
                :hash, '2026-07-23T10:00:00+00:00', 'project_private', '{}'
            )
            """,
            {"hash": "a" * 64},
        )
        with pytest.raises(IntegrityError):
            connection.exec_driver_sql(
                """
                INSERT INTO ingestion_runs (
                    run_id, source_id, adapter_name, adapter_version, status,
                    started_at, input_item_count, processed_item_count,
                    skipped_item_count, failed_item_count, fragment_count,
                    candidate_count, coverage_ratio, quality_report
                ) VALUES (
                    'run:bad', 'source:1', 'adapter', '0.1', 'invalid',
                    '2026-07-23T10:00:00+00:00', 0, 0, 0, 0, 0, 0, 0, '{}'
                )
                """
            )


def test_database_rejects_counts_above_input(tmp_path: Path) -> None:
    _, engine = migrated_database(tmp_path)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO source_records (
                source_id, source_type, idempotency_key, content_ref,
                content_sha256, ingested_at, sensitivity, metadata
            ) VALUES (
                'source:2', 'test', 'key:2', 'file:///source',
                :hash, '2026-07-23T10:00:00+00:00', 'project_private', '{}'
            )
            """,
            {"hash": "b" * 64},
        )
        with pytest.raises(IntegrityError):
            connection.exec_driver_sql(
                """
                INSERT INTO ingestion_runs (
                    run_id, source_id, adapter_name, adapter_version, status,
                    started_at, input_item_count, processed_item_count,
                    skipped_item_count, failed_item_count, fragment_count,
                    candidate_count, coverage_ratio, quality_report
                ) VALUES (
                    'run:counts', 'source:2', 'adapter', '0.1', 'running',
                    '2026-07-23T10:00:00+00:00', 1, 1, 1, 0, 0, 0, 0, '{}'
                )
                """
            )
