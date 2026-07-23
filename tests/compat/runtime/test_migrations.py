from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from me_core.persistence.migrations import _project_root, upgrade_database
from me_core.persistence.models import Base


def test_project_root_can_be_overridden_for_installed_distribution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ME_SYSTEM_PROJECT_ROOT", str(tmp_path))

    assert _project_root() == tmp_path.resolve()


def test_upgrade_database_creates_schema(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    names = set(inspect(create_engine(url)).get_table_names())
    assert {"graph_objects", "graph_evidence_refs", "alembic_version"} <= names


def test_upgrade_database_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    upgrade_database(url, production=False)


def test_migration_matches_sqlalchemy_metadata(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
