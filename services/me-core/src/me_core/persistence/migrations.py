from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy.exc import SQLAlchemyError

from ..errors import GraphMigrationError
from .database import create_database_engine, redact_database_url


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def alembic_config(database_url: str, *, production: bool = True) -> Config:
    engine = create_database_engine(database_url, production=production)
    engine.dispose()
    root = _project_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("prepend_sys_path", str(root / "src"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_database(database_url: str, *, production: bool = True) -> None:
    """Upgrade a graph database to the current migration head."""

    try:
        command.upgrade(alembic_config(database_url, production=production), "head")
    except (CommandError, SQLAlchemyError, OSError) as exc:
        safe_url = redact_database_url(database_url)
        raise GraphMigrationError(f"unable to upgrade graph database at {safe_url}") from exc
