from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from me_core.fixtures import load_graph_fixture
from me_core.persistence.database import create_database_engine
from me_core.persistence.migrations import upgrade_database
from me_core.persistence.store import create_postgres_graph_store
from me_core.query import GraphQueryService


POSTGRES_URL = os.getenv("ME_GRAPH_TEST_POSTGRES_URL")
FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "graph" / "lighting-platform.json"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="ME_GRAPH_TEST_POSTGRES_URL is not configured",
)


def test_postgres_round_trip_lighting_fixture() -> None:
    assert POSTGRES_URL is not None
    schema = f"me_graph_test_{uuid4().hex}"
    base_engine = create_database_engine(POSTGRES_URL)
    parsed = make_url(POSTGRES_URL)
    isolated = parsed.update_query_dict({"options": f"-csearch_path={schema}"})
    isolated_url = isolated.render_as_string(hide_password=False)

    with base_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        upgrade_database(isolated_url)
        store = create_postgres_graph_store(isolated_url)
        load_graph_fixture(FIXTURE, store)
        query = GraphQueryService(store)
        snapshot = query.get_project_snapshot("brain:project:lighting-platform")
        ids = {node.id for node in snapshot.nodes}
        assert "brain:decision:radiance-primary" in ids
        assert "brain:decision:cycles-primary" not in ids
        assert snapshot.excluded["superseded"] == (
            "brain:decision:cycles-primary",
        )
        assert query.get_evidence("brain:decision:radiance-primary")[0].source_id == (
            "src:conversation:2026-07-14"
        )
    finally:
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        base_engine.dispose()
