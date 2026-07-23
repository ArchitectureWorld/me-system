from __future__ import annotations

from collections import deque

from ..contracts import GraphEdge, GraphNamespace, GraphNode
from ..errors import GraphObjectNotFoundError, ProjectAccessError
from ..store import GraphStore


class ProjectScopeGuard:
    """Enforce server-side project scope for read-only Hermes tools."""

    def __init__(
        self,
        store: GraphStore,
        *,
        allowed_project_ids: frozenset[str] | None,
        membership_depth: int = 3,
    ) -> None:
        self.store = store
        self._allowed = allowed_project_ids
        self._membership_depth = membership_depth

    def require_project(self, project_id: str) -> GraphNode:
        if self._allowed is not None and project_id not in self._allowed:
            raise ProjectAccessError(
                "requested project is outside the configured Hermes scope"
            )
        try:
            project = self.store.get_node(project_id)
        except GraphObjectNotFoundError as exc:
            raise ProjectAccessError(
                "requested project is outside the configured Hermes scope"
            ) from exc
        if project.graph is not GraphNamespace.ME_BRAIN or project.type != "Project":
            raise ProjectAccessError(
                "requested project is outside the configured Hermes scope"
            )
        return project

    def validate_requested_depth(self, depth: int) -> None:
        if not 0 <= depth <= self._membership_depth:
            raise ProjectAccessError(
                "requested depth exceeds the configured maximum depth of "
                f"{self._membership_depth}"
            )

    def project_member_ids(self, project_id: str) -> frozenset[str]:
        self.require_project(project_id)
        visited = {project_id}
        queue: deque[tuple[str, int]] = deque([(project_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= self._membership_depth:
                continue
            for edge in self.store.neighbors(current, direction="both"):
                if edge.graph is not GraphNamespace.ME_BRAIN:
                    continue
                other = edge.to_id if edge.from_id == current else edge.from_id
                try:
                    node = self.store.get_node(other)
                except GraphObjectNotFoundError:
                    continue
                if node.graph is not GraphNamespace.ME_BRAIN:
                    continue
                if node.type == "Project" and node.id != project_id:
                    continue
                if node.id not in visited:
                    visited.add(node.id)
                    queue.append((node.id, depth + 1))
        return frozenset(visited)

    def require_member(
        self, project_id: str, object_id: str
    ) -> GraphNode | GraphEdge:
        members = self.project_member_ids(project_id)
        try:
            obj = self.store.get_object(object_id)
        except GraphObjectNotFoundError as exc:
            raise ProjectAccessError(
                "requested graph object is outside the project scope"
            ) from exc
        if isinstance(obj, GraphNode):
            if obj.graph is not GraphNamespace.ME_BRAIN or obj.id not in members:
                raise ProjectAccessError(
                    "requested graph object is outside the project scope"
                )
            return obj
        if (
            obj.graph is not GraphNamespace.ME_BRAIN
            or obj.from_id not in members
            or obj.to_id not in members
        ):
            raise ProjectAccessError(
                "requested graph object is outside the project scope"
            )
        return obj
