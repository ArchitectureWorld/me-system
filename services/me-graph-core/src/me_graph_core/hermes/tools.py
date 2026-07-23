from __future__ import annotations

import json
from collections.abc import Callable
from typing import TypeVar

from ..errors import (
    ContractValidationError,
    GraphCoreError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
    ProjectAccessError,
)
from ..query import GraphQueryService
from .access import ProjectScopeGuard
from .resolver import ProjectResolver

T = TypeVar("T")


def _ok(result: object) -> dict[str, object]:
    return {"ok": True, "result": result}


def _error(
    code: str, message: str, *, retryable: bool = False
) -> dict[str, object]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


def _safe(operation: Callable[[], T]) -> dict[str, object]:
    try:
        return _ok(operation())
    except ProjectAccessError as exc:
        return _error("PROJECT_NOT_ALLOWED", str(exc))
    except GraphObjectNotFoundError:
        return _error("NOT_FOUND", "requested graph object was not found")
    except (ContractValidationError, GraphNamespaceError, ValueError) as exc:
        return _error("INVALID_ARGUMENT", str(exc))
    except GraphCoreError:
        return _error(
            "GRAPH_SERVICE_ERROR",
            "graph service could not complete the request",
            retryable=True,
        )


def _deduplicate_refs(
    values: list[dict[str, object]],
) -> list[dict[str, object]]:
    unique: dict[str, dict[str, object]] = {}
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        unique[key] = value
    return [unique[key] for key in sorted(unique)]


def _restrict_brain_slice(
    value: dict[str, object],
    members: frozenset[str],
    *,
    summary: str | None = None,
) -> dict[str, object]:
    raw_nodes = value.get("nodes", [])
    raw_edges = value.get("edges", [])
    nodes = [
        node
        for node in raw_nodes
        if isinstance(node, dict)
        and node.get("id") in members
        and node.get("graph") == "me_brain"
    ]
    node_ids = {str(node["id"]) for node in nodes}
    edges = [
        edge
        for edge in raw_edges
        if isinstance(edge, dict)
        and edge.get("graph") == "me_brain"
        and edge.get("from_id") in node_ids
        and edge.get("to_id") in node_ids
    ]
    refs: list[dict[str, object]] = []
    for item in [*nodes, *edges]:
        item_refs = item.get("source_refs", [])
        if isinstance(item_refs, list):
            refs.extend(ref for ref in item_refs if isinstance(ref, dict))
    restricted = dict(value)
    restricted["graph"] = "me_brain"
    restricted["nodes"] = nodes
    restricted["edges"] = edges
    restricted["evidence_handles"] = _deduplicate_refs(refs)
    if summary is not None:
        restricted["summary"] = summary
    return restricted


class HermesReadOnlyTools:
    """Pure read-only tool service used by FastMCP and contract tests."""

    def __init__(
        self,
        *,
        resolver: ProjectResolver,
        query: GraphQueryService,
        guard: ProjectScopeGuard,
        hermes_user_id: str,
        max_subgraph_depth: int,
    ) -> None:
        self._resolver = resolver
        self._query = query
        self._guard = guard
        self._hermes_user_id = hermes_user_id
        self._max_depth = max_subgraph_depth

    def resolve_project(
        self,
        *,
        query: str | None = None,
        working_directory: str | None = None,
        external_system: str | None = None,
        external_id: str | None = None,
    ) -> dict[str, object]:
        return _safe(
            lambda: self._resolver.resolve(
                query=query,
                working_directory=working_directory,
                external_system=external_system,
                external_id=external_id,
            ).to_dict()
        )

    def get_snapshot(self, project_id: str) -> dict[str, object]:
        def operation() -> dict[str, object]:
            self._guard.require_project(project_id)
            return self._query.get_project_snapshot(project_id).to_dict()

        return _safe(operation)

    def expand_subgraph(
        self,
        project_id: str,
        node_id: str,
        *,
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> dict[str, object]:
        def operation() -> dict[str, object]:
            if not 0 <= depth <= self._max_depth:
                raise ValueError(
                    "depth must be between 0 and the configured maximum of "
                    f"{self._max_depth}"
                )
            self._guard.require_member(project_id, node_id)
            members = self._guard.project_member_ids(project_id)
            value = self._query.expand_subgraph(
                node_id,
                depth=depth,
                edge_types=set(edge_types) if edge_types else None,
            ).to_dict()
            return _restrict_brain_slice(
                value,
                members,
                summary=f"项目范围内从 {node_id} 展开 {depth} 层",
            )

        return _safe(operation)

    def trace_decision(
        self, project_id: str, decision_id: str
    ) -> dict[str, object]:
        def operation() -> dict[str, object]:
            self._guard.require_member(project_id, decision_id)
            members = self._guard.project_member_ids(project_id)
            value = self._query.trace_decision(decision_id).to_dict()
            return _restrict_brain_slice(value, members)

        return _safe(operation)

    def get_evidence(
        self, project_id: str, object_id: str
    ) -> dict[str, object]:
        def operation() -> list[dict[str, object]]:
            self._guard.require_member(project_id, object_id)
            return [
                ref.to_dict()
                for ref in self._query.get_evidence(object_id)
            ]

        return _safe(operation)

    def get_task_profile(
        self, project_id: str, task_type: str
    ) -> dict[str, object]:
        def operation() -> dict[str, object]:
            self._guard.require_project(project_id)
            return self._query.get_task_profile(
                self._hermes_user_id,
                project_id,
                task_type,
            ).to_dict()

        return _safe(operation)
