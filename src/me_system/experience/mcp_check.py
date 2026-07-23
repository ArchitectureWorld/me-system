from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..hermes.mcp_server import TOOL_NAMES


PROJECT_ID = "brain:project:lighting-platform"
USER_ID = "who:user:master"
TASK_TYPE = "experience_acceptance"


def _node_ids(payload: Mapping[str, object], name: str) -> tuple[str, ...]:
    if payload.get("ok") is not True:
        raise ValueError(f"{name} MCP query did not return ok=true")
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ValueError(f"{name} MCP query result is missing")
    nodes = result.get("nodes")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
        raise ValueError(f"{name} MCP query nodes are missing")
    values: list[str] = []
    for item in nodes:
        if isinstance(item, Mapping) and item.get("id") is not None:
            values.append(str(item["id"]))
    return tuple(values)


def validate_mcp_results(
    tool_names: Sequence[str],
    snapshot_payload: Mapping[str, object],
    profile_payload: Mapping[str, object],
    *,
    brain_task_id: str,
    who_rule_id: str,
) -> dict[str, object]:
    names = tuple(str(value) for value in tool_names)
    if names != TOOL_NAMES:
        raise ValueError("MCP must expose exactly the six read-only tools")
    snapshot_ids = _node_ids(snapshot_payload, "brain_get_snapshot")
    profile_ids = _node_ids(profile_payload, "who_get_task_profile")
    if brain_task_id not in snapshot_ids:
        raise ValueError("ME-Brain Task is missing from the MCP project snapshot")
    if who_rule_id not in profile_ids:
        raise ValueError("ME-Who CollaborationRule is missing from the MCP task profile")
    return {
        "tool_names": list(names),
        "brain_task_visible": True,
        "who_rule_visible": True,
        "snapshot_node_count": len(snapshot_ids),
        "profile_node_count": len(profile_ids),
        "brain_task_id": brain_task_id,
        "who_rule_id": who_rule_id,
    }


async def _run_mcp_check(
    database_url: str,
    brain_task_id: str,
    who_rule_id: str,
) -> dict[str, object]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "me_system.hermes.mcp_server"],
        env={
            **os.environ,
            "ME_GRAPH_DATABASE_URL": database_url,
            "ME_GRAPH_HERMES_USER_ID": USER_ID,
            "ME_GRAPH_ALLOWED_PROJECT_IDS": PROJECT_ID,
            "ME_GRAPH_MAX_SUBGRAPH_DEPTH": "2",
            "ME_GRAPH_MCP_LOG_LEVEL": "ERROR",
        },
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            snapshot = await session.call_tool(
                "brain_get_snapshot",
                {"project_id": PROJECT_ID},
            )
            profile = await session.call_tool(
                "who_get_task_profile",
                {"project_id": PROJECT_ID, "task_type": TASK_TYPE},
            )
            if snapshot.isError:
                raise ValueError("brain_get_snapshot returned an MCP error")
            if profile.isError:
                raise ValueError("who_get_task_profile returned an MCP error")
            if not isinstance(snapshot.structuredContent, Mapping):
                raise ValueError("brain_get_snapshot returned no structured content")
            if not isinstance(profile.structuredContent, Mapping):
                raise ValueError("who_get_task_profile returned no structured content")
            return validate_mcp_results(
                tuple(tool.name for tool in listed.tools),
                snapshot.structuredContent,
                profile.structuredContent,
                brain_task_id=brain_task_id,
                who_rule_id=who_rule_id,
            )


def run_mcp_check(
    database_url: str,
    brain_task_id: str,
    who_rule_id: str,
) -> dict[str, object]:
    """Run the real Hermes stdio server and validate read-only dual-graph results."""

    return asyncio.run(_run_mcp_check(database_url, brain_task_id, who_rule_id))
