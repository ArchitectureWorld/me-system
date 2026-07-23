from __future__ import annotations

from collections import deque

from ..contracts import GraphEdge, GraphNamespace, GraphNode
from ..errors import GraphObjectNotFoundError, ProjectAccessError
from ..store import GraphStore

_PROJECT_OWNERSHIP_EDGE_TYPES = {
    "HAS_DECISION",
    "HAS_REQUIREMENT",
    "HAS_TASK",
    "HAS_ISSUE",
    "HAS_ARTIFACT",
    "HAS_CONSTRAINT",
}


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

    def _decision_owned_by_other_project(
        self,
        project_id: str,
        decision_id: str,
    ) -> bool:
        owners: set[str] = set()
        for edge in self.store.neighbors(
            decision_id,
            edge_types={"HAS_DECISION"},
            direction="in",
        ):
            try:
                owner = self.store.get_node(edge.from_id)
            except GraphObjectNotFoundError:
                continue
            if (
                owner.graph is GraphNamespace.ME_BRAIN
                and owner.type == "Project"
            ):
                owners.add(owner.id)
        return bool(owners and project_id not in owners)

    def project_member_ids(self, project_id: str) -> frozenset[str]:
        """Return explicitly owned objects plus bounded decision history.

        Arbitrary semantic relations never expand the authorization boundary.
        Historical decisions inherit scope only when another project does not
        explicitly own them.
        """

        self.require_project(project_id)
        members = {project_id}
        decisions: deque[tuple[str, int]] = deque()

        for edge in self.store.neighbors(
            project_id,
            edge_types=_PROJECT_OWNERSHIP_EDGE_TYPES,
            direction="out",
        ):
            try:
                node = self.store.get_node(edge.to_id)
            except GraphObjectNotFoundError:
                continue
            if node.graph is not GraphNamespace.ME_BRAIN or node.type == "Project":
                continue
            members.add(node.id)
            if node.type == "Decision":
                decisions.append((node.id, 1))

        while decisions:
            current_id, depth = decisions.popleft()
            if depth >= self._membership_depth:
                continue
            for edge in self.store.neighbors(
                current_id,
                edge_types={"SUPERSEDES"},
                direction="both",
            ):
                other_id = (
                    edge.to_id if edge.from_id == current_id else edge.from_id
                )
                try:
                    node = self.store.get_node(other_id)
                except GraphObjectNotFoundError:
                    continue
                if (
                    node.graph is not GraphNamespace.ME_BRAIN
                    or node.type != "Decision"
                    or node.id in members
                    or self._decision_owned_by_other_project(
                        project_id,
                        node.id,
                    )
                ):
                    continue
                members.add(node.id)
                decisions.append((node.id, depth + 1))

        return frozenset(members)

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
