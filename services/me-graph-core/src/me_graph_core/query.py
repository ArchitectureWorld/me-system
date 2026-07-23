from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from typing import Iterable

from .contracts import EvidenceRef, GraphEdge, GraphNamespace, GraphNode, GraphSlice, TemporalStatus
from .errors import ContractValidationError, GraphNamespaceError
from .store import GraphStore


_PROJECT_EDGE_TYPES = {
    "HAS_DECISION",
    "HAS_REQUIREMENT",
    "HAS_TASK",
    "HAS_ISSUE",
    "HAS_ARTIFACT",
    "HAS_CONSTRAINT",
}
_USER_EDGE_TYPES = {
    "HAS_ROLE",
    "HAS_CAPABILITY",
    "HAS_COLLABORATION_RULE",
    "PREFERS",
    "HAS_GOAL",
}


def _slice_id(kind: str, roots: Iterable[str], as_of: datetime | None) -> str:
    payload = json.dumps(
        {"kind": kind, "roots": sorted(roots), "as_of": as_of.isoformat() if as_of else None},
        sort_keys=True,
    )
    return f"slice:{kind}:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"


def _active_node(node: GraphNode, as_of: datetime | None) -> bool:
    if as_of is None:
        return node.status is TemporalStatus.CURRENT
    moment = as_of.astimezone(timezone.utc)
    if node.valid_from is not None and moment < node.valid_from:
        return False
    if node.valid_to is not None and moment >= node.valid_to:
        return False
    return True


def _active_edge(edge: GraphEdge, as_of: datetime | None) -> bool:
    if as_of is None:
        return edge.valid_to is None
    moment = as_of.astimezone(timezone.utc)
    if edge.valid_from is not None and moment < edge.valid_from:
        return False
    if edge.valid_to is not None and moment >= edge.valid_to:
        return False
    return True


def _unique_evidence(nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> tuple[EvidenceRef, ...]:
    unique: dict[str, EvidenceRef] = {}
    for obj in (*tuple(nodes), *tuple(edges)):
        for ref in obj.source_refs:
            key = json.dumps(ref.to_dict(), ensure_ascii=False, sort_keys=True)
            unique[key] = ref
    return tuple(unique[key] for key in sorted(unique))


class GraphQueryService:
    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def get_project_snapshot(self, project_id: str, as_of: datetime | None = None) -> GraphSlice:
        project = self._store.get_node(project_id)
        if project.graph is not GraphNamespace.ME_BRAIN or project.type != "Project":
            raise GraphNamespaceError("project snapshot requires a ME-Brain Project node")
        nodes: dict[str, GraphNode] = {project.id: project}
        selected_edges: dict[str, GraphEdge] = {}
        excluded_superseded: set[str] = set()
        for edge in self._store.neighbors(project.id, edge_types=_PROJECT_EDGE_TYPES, direction="out"):
            if not _active_edge(edge, as_of):
                continue
            target = self._store.get_node(edge.to_id)
            if _active_node(target, as_of):
                nodes[target.id] = target
                selected_edges[edge.id] = edge
            elif target.status in {TemporalStatus.SUPERSEDED, TemporalStatus.HISTORICAL}:
                excluded_superseded.add(target.id)
        for node in tuple(nodes.values()):
            if node.type == "Decision":
                for edge in self._store.neighbors(node.id, edge_types={"SUPERSEDES"}, direction="out"):
                    target = self._store.get_node(edge.to_id)
                    if target.status in {TemporalStatus.SUPERSEDED, TemporalStatus.HISTORICAL}:
                        excluded_superseded.add(target.id)
        for edge in self._store.list_edges(GraphNamespace.ME_BRAIN):
            if edge.from_id in nodes and edge.to_id in nodes and _active_edge(edge, as_of):
                selected_edges[edge.id] = edge
        sorted_nodes = tuple(sorted(nodes.values(), key=lambda item: item.id))
        sorted_edges = tuple(sorted(selected_edges.values(), key=lambda item: item.id))
        return GraphSlice(
            slice_id=_slice_id("project-snapshot", (project.id,), as_of),
            graph=GraphNamespace.ME_BRAIN,
            as_of_time=as_of or datetime.now(timezone.utc),
            root_ids=(project.id,),
            summary=f"{project.label} 当前子图：{len(sorted_nodes)} 个节点，{len(sorted_edges)} 条关系",
            nodes=sorted_nodes,
            edges=sorted_edges,
            evidence_handles=_unique_evidence(sorted_nodes, sorted_edges),
            excluded={"superseded": tuple(sorted(excluded_superseded)), "unauthorized": ()},
            truncated=False,
        )

    def expand_subgraph(
        self,
        node_id: str,
        depth: int = 1,
        edge_types: set[str] | None = None,
    ) -> GraphSlice:
        if depth < 0:
            raise ContractValidationError("depth must be zero or greater")
        root = self._store.get_node(node_id)
        visited_nodes: dict[str, GraphNode] = {root.id: root}
        visited_edges: dict[str, GraphEdge] = {}
        queue: deque[tuple[str, int]] = deque([(root.id, 0)])
        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for edge in self._store.neighbors(current_id, edge_types=edge_types, direction="both"):
                visited_edges[edge.id] = edge
                other_id = edge.to_id if edge.from_id == current_id else edge.from_id
                if other_id not in visited_nodes:
                    other = self._store.get_node(other_id)
                    visited_nodes[other.id] = other
                    queue.append((other.id, current_depth + 1))
        nodes = tuple(sorted(visited_nodes.values(), key=lambda item: item.id))
        edges = tuple(sorted(visited_edges.values(), key=lambda item: item.id))
        return GraphSlice(
            slice_id=_slice_id("expand", (root.id,), None),
            graph=root.graph,
            as_of_time=datetime.now(timezone.utc),
            root_ids=(root.id,),
            summary=f"从 {root.label} 展开 {depth} 层",
            nodes=nodes,
            edges=edges,
            evidence_handles=_unique_evidence(nodes, edges),
            excluded={"superseded": (), "unauthorized": ()},
            truncated=False,
        )

    def trace_decision(self, decision_id: str) -> GraphSlice:
        decision = self._store.get_node(decision_id)
        if decision.graph is not GraphNamespace.ME_BRAIN or decision.type != "Decision":
            raise GraphNamespaceError("decision trace requires a ME-Brain Decision node")
        nodes: dict[str, GraphNode] = {decision.id: decision}
        edges: dict[str, GraphEdge] = {}
        queue: deque[str] = deque([decision.id])
        while queue:
            current_id = queue.popleft()
            for edge in self._store.neighbors(current_id, edge_types={"SUPERSEDES"}, direction="both"):
                edges[edge.id] = edge
                other_id = edge.to_id if edge.from_id == current_id else edge.from_id
                if other_id not in nodes:
                    nodes[other_id] = self._store.get_node(other_id)
                    queue.append(other_id)
        sorted_nodes = tuple(sorted(nodes.values(), key=lambda item: item.id))
        sorted_edges = tuple(sorted(edges.values(), key=lambda item: item.id))
        return GraphSlice(
            slice_id=_slice_id("decision-trace", (decision.id,), None),
            graph=GraphNamespace.ME_BRAIN,
            as_of_time=datetime.now(timezone.utc),
            root_ids=(decision.id,),
            summary=f"{decision.label} 的决策演化链",
            nodes=sorted_nodes,
            edges=sorted_edges,
            evidence_handles=_unique_evidence(sorted_nodes, sorted_edges),
            excluded={"superseded": (), "unauthorized": ()},
            truncated=False,
        )

    def get_evidence(self, node_or_edge_id: str) -> tuple[EvidenceRef, ...]:
        obj = self._store.get_object(node_or_edge_id)
        return obj.source_refs

    def get_task_profile(
        self,
        user_id: str,
        project_id: str,
        task_type: str,
    ) -> GraphSlice:
        user = self._store.get_node(user_id)
        project = self._store.get_node(project_id)
        if user.graph is not GraphNamespace.ME_WHO or user.type != "User":
            raise GraphNamespaceError("task profile requires a ME-Who User node")
        if project.graph is not GraphNamespace.ME_BRAIN or project.type != "Project":
            raise GraphNamespaceError("task profile project must be a ME-Brain Project node")
        nodes: dict[str, GraphNode] = {user.id: user}
        edges: dict[str, GraphEdge] = {}
        for edge in self._store.neighbors(user.id, edge_types=_USER_EDGE_TYPES, direction="out"):
            target = self._store.get_node(edge.to_id)
            if target.status is not TemporalStatus.CURRENT:
                continue
            if target.type == "CollaborationRule":
                task_types = target.properties.get("task_types", [])
                project_ids = target.properties.get("project_ids", [])
                if task_types and task_type not in task_types:
                    continue
                if project_ids and project_id not in project_ids:
                    continue
            nodes[target.id] = target
            edges[edge.id] = edge
        sorted_nodes = tuple(sorted(nodes.values(), key=lambda item: item.id))
        sorted_edges = tuple(sorted(edges.values(), key=lambda item: item.id))
        return GraphSlice(
            slice_id=_slice_id("task-profile", (user.id, project.id, task_type), None),
            graph=GraphNamespace.ME_WHO,
            as_of_time=datetime.now(timezone.utc),
            root_ids=(user.id,),
            summary=f"{user.label} 在 {project.label} 的 {task_type} 任务画像",
            nodes=sorted_nodes,
            edges=sorted_edges,
            evidence_handles=_unique_evidence(sorted_nodes, sorted_edges),
            excluded={"superseded": (), "unauthorized": ()},
            truncated=False,
        )
