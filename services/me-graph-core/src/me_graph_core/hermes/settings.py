from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..errors import HermesConfigurationError


def _required(env: Mapping[str, str], key: str) -> str:
    value = str(env.get(key, "")).strip()
    if not value:
        raise HermesConfigurationError(f"{key} is required")
    return value


@dataclass(frozen=True, slots=True)
class HermesServerSettings:
    database_url: str
    hermes_user_id: str
    allowed_project_ids: frozenset[str] | None
    max_subgraph_depth: int = 2
    log_level: str = "WARNING"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "HermesServerSettings":
        database_url = _required(env, "ME_GRAPH_DATABASE_URL")
        user_id = _required(env, "ME_GRAPH_HERMES_USER_ID")
        allowed_value = _required(env, "ME_GRAPH_ALLOWED_PROJECT_IDS")
        if not user_id.startswith("who:"):
            raise HermesConfigurationError(
                "ME_GRAPH_HERMES_USER_ID must be a ME-Who ID"
            )
        if allowed_value == "*":
            allowed = None
        else:
            values = frozenset(
                item.strip() for item in allowed_value.split(",") if item.strip()
            )
            if not values or any(
                not item.startswith("brain:project:") for item in values
            ):
                raise HermesConfigurationError(
                    "ME_GRAPH_ALLOWED_PROJECT_IDS must contain canonical "
                    "ME-Brain project IDs or *"
                )
            allowed = values
        raw_depth = str(env.get("ME_GRAPH_MAX_SUBGRAPH_DEPTH", "2")).strip()
        try:
            depth = int(raw_depth)
        except ValueError as exc:
            raise HermesConfigurationError(
                "ME_GRAPH_MAX_SUBGRAPH_DEPTH must be an integer"
            ) from exc
        if not 0 <= depth <= 3:
            raise HermesConfigurationError(
                "ME_GRAPH_MAX_SUBGRAPH_DEPTH must be between 0 and 3"
            )
        log_level = (
            str(env.get("ME_GRAPH_MCP_LOG_LEVEL", "WARNING")).strip().upper()
            or "WARNING"
        )
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise HermesConfigurationError(
                "ME_GRAPH_MCP_LOG_LEVEL must be a standard Python log level"
            )
        return cls(database_url, user_id, allowed, depth, log_level)
