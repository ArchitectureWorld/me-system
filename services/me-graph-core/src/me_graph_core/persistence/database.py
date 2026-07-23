from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError

from ..errors import GraphStoreConfigurationError, GraphStoreUnavailableError


def _parse_url(url: str | URL) -> URL:
    if isinstance(url, URL):
        return url
    normalized = str(url).strip()
    if not normalized:
        raise GraphStoreConfigurationError("database URL must not be empty")
    try:
        return make_url(normalized)
    except ArgumentError as exc:
        raise GraphStoreConfigurationError("database URL is invalid") from exc


def redact_database_url(url: str | URL) -> str:
    """Return a printable database URL without exposing its password."""

    return _parse_url(url).render_as_string(hide_password=True)


def create_database_engine(url: str | URL, *, production: bool = True) -> Engine:
    """Create a configured SQLAlchemy engine for graph storage.

    Production callers are deliberately restricted to the modern psycopg 3
    PostgreSQL dialect. Tests may opt into SQLite by setting
    ``production=False``.
    """

    parsed = _parse_url(url)
    if production and parsed.drivername != "postgresql+psycopg":
        raise GraphStoreConfigurationError(
            "production graph storage requires a postgresql+psycopg database URL"
        )
    try:
        return create_engine(parsed, pool_pre_ping=True)
    except (ModuleNotFoundError, NoSuchModuleError) as exc:
        raise GraphStoreUnavailableError(
            f"database driver is unavailable for {parsed.drivername}"
        ) from exc
