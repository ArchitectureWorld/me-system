from __future__ import annotations

import pytest

from me_core.errors import GraphStoreConfigurationError
from me_core.persistence.database import create_database_engine, redact_database_url


def test_production_engine_requires_postgresql_psycopg() -> None:
    with pytest.raises(GraphStoreConfigurationError, match=r"postgresql\+psycopg"):
        create_database_engine("sqlite+pysqlite:///:memory:")


def test_test_engine_allows_sqlite() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:", production=False)
    assert engine.dialect.name == "sqlite"


def test_redact_database_url_hides_password() -> None:
    value = redact_database_url("postgresql+psycopg://user:secret@db/me_graph")
    assert "secret" not in value
    assert "***" in value


def test_empty_url_is_rejected_without_leaking_input() -> None:
    with pytest.raises(GraphStoreConfigurationError, match="must not be empty"):
        create_database_engine("")
