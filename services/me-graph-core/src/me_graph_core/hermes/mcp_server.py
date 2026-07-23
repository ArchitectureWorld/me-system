from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping

from mcp.server.fastmcp import FastMCP

from ..persistence.store import create_postgres_graph_store
from ..query import GraphQueryService
from .access import ProjectScopeGuard
from .resolver import ProjectResolver
from .settings import HermesServerSettings
from .tools import HermesReadOnlyTools

TOOL_NAMES = (
    "brain_resolve_project",
    "brain_get_snapshot",
    "brain_expand_subgraph",
    "brain_trace_decision",
    "brain_get_evidence",
    "who_get_task_profile",
)


def create_mcp_server(
    tools: HermesReadOnlyTools,
    *,
    log_level: str = "WARNING",
) -> FastMCP:
    mcp = FastMCP(
        name="ME-System Graph",
        instructions=(
            "Read-only ME-Brain and task-scoped ME-Who graph tools. "
            "Resolve a project before reading its snapshot. "
            "Use subgraph and evidence tools only when needed."
        ),
        json_response=True,
        log_level=log_level,
    )

    @mcp.tool()
    def brain_resolve_project(
        query: str | None = None,
        working_directory: str | None = None,
        external_system: str | None = None,
        external_id: str | None = None,
    ) -> dict[str, object]:
        """Resolve an allowed project by exact ID, name, alias, path, or external ID."""

        return tools.resolve_project(
            query=query,
            working_directory=working_directory,
            external_system=external_system,
            external_id=external_id,
        )

    @mcp.tool()
    def brain_get_snapshot(project_id: str) -> dict[str, object]:
        """Read the current project graph slice, excluding superseded facts."""

        return tools.get_snapshot(project_id)

    @mcp.tool()
    def brain_expand_subgraph(
        project_id: str,
        node_id: str,
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> dict[str, object]:
        """Expand a bounded ME-Brain subgraph inside an authorized project."""

        return tools.expand_subgraph(
            project_id,
            node_id,
            depth=depth,
            edge_types=edge_types,
        )

    @mcp.tool()
    def brain_trace_decision(
        project_id: str,
        decision_id: str,
    ) -> dict[str, object]:
        """Trace the current and historical SUPERSEDES chain for a decision."""

        return tools.trace_decision(project_id, decision_id)

    @mcp.tool()
    def brain_get_evidence(
        project_id: str,
        object_id: str,
    ) -> dict[str, object]:
        """Return stable evidence references for an authorized graph object."""

        return tools.get_evidence(project_id, object_id)

    @mcp.tool()
    def who_get_task_profile(
        project_id: str,
        task_type: str,
    ) -> dict[str, object]:
        """Read task-scoped ME-Who rules for the server-configured user."""

        return tools.get_task_profile(project_id, task_type)

    return mcp


def build_server_from_env(
    env: Mapping[str, str] | None = None,
) -> FastMCP:
    values = os.environ if env is None else env
    settings = HermesServerSettings.from_env(values)
    store = create_postgres_graph_store(settings.database_url)
    tools = HermesReadOnlyTools(
        resolver=ProjectResolver(
            store,
            allowed_project_ids=settings.allowed_project_ids,
        ),
        query=GraphQueryService(store),
        guard=ProjectScopeGuard(
            store,
            allowed_project_ids=settings.allowed_project_ids,
            membership_depth=3,
        ),
        hermes_user_id=settings.hermes_user_id,
        max_subgraph_depth=settings.max_subgraph_depth,
    )
    return create_mcp_server(tools, log_level=settings.log_level)


def main() -> None:
    try:
        build_server_from_env().run(transport="stdio")
    except Exception as exc:
        # stdout belongs exclusively to MCP framing.
        logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
        logging.error("ME-System MCP failed to start: %s", type(exc).__name__)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
