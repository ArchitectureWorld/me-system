from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from me_graph_core.fixtures import load_graph_fixture
from me_graph_core.hermes.resolver import ProjectResolver
from me_graph_core.store import InMemoryGraphStore

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"


def resolver(
    allowed: set[str] | None = None,
) -> tuple[ProjectResolver, InMemoryGraphStore]:
    store = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, store)
    return ProjectResolver(store, allowed_project_ids=allowed), store


def test_resolve_by_canonical_id() -> None:
    value, _ = resolver()
    result = value.resolve(query=PROJECT)
    assert result.status == "resolved"
    assert result.project_id == PROJECT
    assert result.match_type == "canonical_id"


def test_resolve_by_label_and_alias() -> None:
    value, _ = resolver()
    assert value.resolve(query="LIGHTING-PLATFORM").match_type == "label"
    alias = value.resolve(query="照明平台")
    assert alias.project_id == PROJECT
    assert alias.match_type == "alias"


def test_resolve_by_workspace_path() -> None:
    value, _ = resolver()
    result = value.resolve(
        working_directory="/workspace/lighting-platform/."
    )
    assert result.project_id == PROJECT
    assert result.match_type == "workspace_path"


def test_resolve_by_external_id() -> None:
    value, _ = resolver()
    result = value.resolve(
        external_system="github",
        external_id="ArchitectureWorld/lighting-platform",
    )
    assert result.project_id == PROJECT
    assert result.match_type == "external_id"


def test_resolver_precedence_prefers_canonical_id() -> None:
    value, _ = resolver()
    result = value.resolve(
        query=PROJECT,
        external_system="github",
        external_id="ArchitectureWorld/lighting-platform",
    )
    assert result.match_type == "canonical_id"


def test_ambiguous_match_returns_candidates() -> None:
    value, store = resolver()
    original = store.get_node(PROJECT)
    store.add_node(
        replace(
            original,
            id="brain:project:lighting-platform-copy",
            label="lighting-platform-copy",
        )
    )
    result = value.resolve(query="照明平台")
    assert result.status == "ambiguous"
    assert result.project_id is None
    assert [candidate.project_id for candidate in result.candidates] == [
        PROJECT,
        "brain:project:lighting-platform-copy",
    ]


def test_not_found_is_structured() -> None:
    value, _ = resolver()
    assert value.resolve(query="missing").to_dict() == {
        "status": "not_found",
        "project_id": None,
        "match_type": None,
        "matched_value": None,
        "confidence": 0.0,
        "candidates": [],
    }


def test_allowlist_hides_disallowed_projects() -> None:
    value, _ = resolver(allowed={"brain:project:other"})
    assert value.resolve(query="lighting-platform").status == "not_found"
