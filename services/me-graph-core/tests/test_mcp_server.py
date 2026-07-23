from __future__ import annotations

import asyncio
from pathlib import Path

from me_graph_core.fixtures import load_graph_fixture
from me_graph_core.hermes.access import ProjectScopeGuard
from me_graph_core.hermes.mcp_server import TOOL_NAMES, create_mcp_server
from me_graph_core.hermes.resolver import ProjectResolver
from me_graph_core.hermes.tools import HermesReadOnlyTools
from me_graph_core.query import GraphQueryService
from me_graph_core.store import InMemoryGraphStore

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"


def server():
    store = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, store)
    allowed = frozenset({PROJECT})
    return create_mcp_server(
        HermesReadOnlyTools(
            resolver=ProjectResolver(
                store,
                allowed_project_ids=allowed,
            ),
            query=GraphQueryService(store),
            guard=ProjectScopeGuard(
                store,
                allowed_project_ids=allowed,
                membership_depth=3,
            ),
            hermes_user_id="who:user:master",
            max_subgraph_depth=2,
        )
    )


def test_mcp_exposes_exactly_six_read_only_tools() -> None:
    async def run() -> None:
        available = await server().list_tools()
        assert tuple(tool.name for tool in available) == TOOL_NAMES

    asyncio.run(run())
