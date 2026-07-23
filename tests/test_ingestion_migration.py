from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect

from me_system.persistence.migrations import upgrade_database


EXPECTED_NEW_TABLES = {
    "source_records",
    "evidence_fragments",
    "ingestion_runs",
    "candidate_graph_changes",
    "candidate_evidence_refs",
    "candidate_review_events",
}


def test_upgrade_database_creates_ingestion_schema(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'me-system.db'}"
    upgrade_database(url, production=False)
    names = set(inspect(create_engine(url)).get_table_names())
    assert EXPECTED_NEW_TABLES <= names
    assert "graph_objects" in names
    assert "alembic_version" in names


def test_upgrade_database_to_ingestion_head_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'me-system.db'}"
    upgrade_database(url, production=False)
    upgrade_database(url, production=False)
    engine = create_engine(url)
    version = engine.connect().exec_driver_sql(
        "SELECT version_num FROM alembic_version"
    ).scalar_one()
    assert version == "0002_ingestion"
