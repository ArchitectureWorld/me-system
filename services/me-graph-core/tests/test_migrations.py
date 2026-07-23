from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect

from me_graph_core.persistence.migrations import upgrade_database


def test_upgrade_database_creates_schema(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    names = set(inspect(create_engine(url)).get_table_names())
    assert {"graph_objects", "graph_evidence_refs", "alembic_version"} <= names


def test_upgrade_database_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    upgrade_database(url, production=False)
