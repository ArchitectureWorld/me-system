from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import unicodedata
from typing import Literal

from ..contracts import GraphNamespace, GraphNode
from ..store import GraphStore

ResolutionStatus = Literal["resolved", "ambiguous", "not_found"]
MatchType = Literal["canonical_id", "external_id", "workspace_path", "label", "alias"]


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _normalize_path(value: str) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _external_ids(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        _normalize_text(str(key)): _normalize_text(str(item))
        for key, item in value.items()
        if str(key).strip() and str(item).strip()
    }


@dataclass(frozen=True, slots=True)
class ProjectCandidate:
    project_id: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"project_id": self.project_id, "label": self.label}


@dataclass(frozen=True, slots=True)
class ProjectResolution:
    status: ResolutionStatus
    project_id: str | None
    match_type: MatchType | None
    matched_value: str | None
    confidence: float
    candidates: tuple[ProjectCandidate, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "project_id": self.project_id,
            "match_type": self.match_type,
            "matched_value": self.matched_value,
            "confidence": self.confidence,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


class ProjectResolver:
    """Resolve exact project identifiers without model guessing or fuzzy search."""

    def __init__(
        self,
        store: GraphStore,
        *,
        allowed_project_ids: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.store = store
        self._allowed = None if allowed_project_ids is None else frozenset(allowed_project_ids)

    def _projects(self) -> tuple[GraphNode, ...]:
        return tuple(
            node
            for node in self.store.list_nodes(GraphNamespace.ME_BRAIN)
            if node.type == "Project"
            and (self._allowed is None or node.id in self._allowed)
        )

    def resolve(
        self,
        *,
        query: str | None = None,
        working_directory: str | None = None,
        external_system: str | None = None,
        external_id: str | None = None,
    ) -> ProjectResolution:
        if not any(
            value is not None and str(value).strip()
            for value in (query, working_directory, external_system, external_id)
        ):
            return ProjectResolution("not_found", None, None, None, 0.0)

        projects = self._projects()
        matchers: list[
            tuple[MatchType, str | None, Callable[[GraphNode], bool]]
        ] = []
        if query and query.strip():
            normalized_query = _normalize_text(query)
            matchers.append(
                (
                    "canonical_id",
                    query,
                    lambda node: _normalize_text(node.id) == normalized_query,
                )
            )
        if external_system and external_id and external_system.strip() and external_id.strip():
            system = _normalize_text(external_system)
            identifier = _normalize_text(external_id)
            matchers.append(
                (
                    "external_id",
                    external_id,
                    lambda node: _external_ids(node.properties.get("external_ids")).get(system)
                    == identifier,
                )
            )
        if working_directory and working_directory.strip():
            normalized_directory = _normalize_path(working_directory)
            matchers.append(
                (
                    "workspace_path",
                    normalized_directory,
                    lambda node: normalized_directory
                    in {
                        _normalize_path(path)
                        for path in _string_list(node.properties.get("workspace_paths"))
                    },
                )
            )
        if query and query.strip():
            normalized_query = _normalize_text(query)
            matchers.append(
                (
                    "label",
                    query,
                    lambda node: _normalize_text(node.label) == normalized_query,
                )
            )
            matchers.append(
                (
                    "alias",
                    query,
                    lambda node: normalized_query
                    in {
                        _normalize_text(alias)
                        for alias in _string_list(node.properties.get("aliases"))
                    },
                )
            )

        for match_type, matched_value, predicate in matchers:
            matches = tuple(project for project in projects if predicate(project))
            if len(matches) == 1:
                project = matches[0]
                return ProjectResolution(
                    "resolved",
                    project.id,
                    match_type,
                    matched_value,
                    1.0,
                    (ProjectCandidate(project.id, project.label),),
                )
            if len(matches) > 1:
                candidates = tuple(
                    ProjectCandidate(project.id, project.label)
                    for project in sorted(matches, key=lambda item: item.id)
                )
                return ProjectResolution(
                    "ambiguous",
                    None,
                    match_type,
                    matched_value,
                    0.0,
                    candidates,
                )

        return ProjectResolution("not_found", None, None, None, 0.0)
