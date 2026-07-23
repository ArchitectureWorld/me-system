from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from me_system.experience.contracts import CheckStatus
from me_system.experience.runner import run_acceptance
from me_system.hermes.mcp_server import TOOL_NAMES
from me_system.persistence.database import create_database_engine


POSTGRES_URL = os.getenv("ME_GRAPH_TEST_POSTGRES_URL")
FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "graph" / "lighting-platform.json"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="ME_GRAPH_TEST_POSTGRES_URL is not configured",
)


def test_one_click_acceptance_passes_postgres_and_real_stdio_mcp() -> None:
    assert POSTGRES_URL is not None
    schema = f"me_experience_test_{uuid4().hex}"
    base_engine = create_database_engine(POSTGRES_URL)
    parsed = make_url(POSTGRES_URL)
    isolated = parsed.update_query_dict({"options": f"-csearch_path={schema}"})
    isolated_url = isolated.render_as_string(hide_password=False)

    with base_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        report = run_acceptance(
            isolated_url,
            FIXTURE,
            include_mcp=True,
        )

        assert report.status == "pass", report.to_dict()
        assert len(report.checks) == 8
        assert all(item.status is CheckStatus.PASS for item in report.checks)
        assert tuple(report.technical["tool_names"]) == TOOL_NAMES
        assert report.technical["brain_task_id"]
        assert report.technical["who_rule_id"]
        assert report.highlights["current_engine"] == "Radiance"
    finally:
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        base_engine.dispose()
