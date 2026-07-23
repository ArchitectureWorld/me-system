from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sqlalchemy import text
from sqlalchemy.engine import make_url

from me_core.fixtures import load_graph_fixture
from me_core.hermes.mcp_server import TOOL_NAMES
from me_core.persistence.database import create_database_engine
from me_core.persistence.migrations import upgrade_database
from me_core.persistence.store import create_postgres_graph_store

POSTGRES_URL = os.getenv("ME_GRAPH_TEST_POSTGRES_URL")
FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="ME_GRAPH_TEST_POSTGRES_URL is not configured",
)


def test_hermes_stdio_mcp_end_to_end() -> None:
    assert POSTGRES_URL is not None
    schema = f"me_graph_mcp_test_{uuid4().hex}"
    base_engine = create_database_engine(POSTGRES_URL)
    parsed = make_url(POSTGRES_URL)
    isolated = parsed.update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    isolated_url = isolated.render_as_string(hide_password=False)

    with base_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    async def run() -> None:
        upgrade_database(isolated_url)
        store = create_postgres_graph_store(isolated_url)
        load_graph_fixture(FIXTURE, store)
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "me_core.hermes.mcp_server"],
            env={
                **os.environ,
                "ME_GRAPH_DATABASE_URL": isolated_url,
                "ME_GRAPH_HERMES_USER_ID": "who:user:master",
                "ME_GRAPH_ALLOWED_PROJECT_IDS": PROJECT,
                "ME_GRAPH_MAX_SUBGRAPH_DEPTH": "2",
                "ME_GRAPH_MCP_LOG_LEVEL": "ERROR",
            },
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                assert tuple(tool.name for tool in listed.tools) == TOOL_NAMES

                resolved = await session.call_tool(
                    "brain_resolve_project",
                    {"query": "照明平台"},
                )
                assert not resolved.isError
                assert resolved.structuredContent["ok"] is True
                assert (
                    resolved.structuredContent["result"]["project_id"]
                    == PROJECT
                )

                snapshot = await session.call_tool(
                    "brain_get_snapshot",
                    {"project_id": PROJECT},
                )
                ids = {
                    node["id"]
                    for node in snapshot.structuredContent["result"]["nodes"]
                }
                assert "brain:decision:radiance-primary" in ids
                assert "brain:decision:cycles-primary" not in ids

                profile = await session.call_tool(
                    "who_get_task_profile",
                    {
                        "project_id": PROJECT,
                        "task_type": "implementation",
                    },
                )
                profile_ids = {
                    node["id"]
                    for node in profile.structuredContent["result"]["nodes"]
                }
                assert (
                    "who:collaboration-rule:direct-execution"
                    in profile_ids
                )
                assert (
                    "who:collaboration-rule:architecture-first"
                    not in profile_ids
                )

                denied = await session.call_tool(
                    "brain_get_snapshot",
                    {"project_id": "brain:project:not-allowed"},
                )
                assert denied.structuredContent["ok"] is False
                assert (
                    denied.structuredContent["error"]["code"]
                    == "PROJECT_NOT_ALLOWED"
                )

    try:
        asyncio.run(run())
    finally:
        with base_engine.begin() as connection:
            connection.execute(
                text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            )
        base_engine.dispose()
