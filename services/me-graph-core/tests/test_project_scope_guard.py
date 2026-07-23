from __future__ import annotations

from pathlib import Path

import pytest

from me_graph_core.errors import ProjectAccessError
from me_graph_core.fixtures import load_graph_fixture
from me_graph_core.hermes.access import ProjectScopeGuard
from me_graph_core.store import InMemoryGraphStore

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"


def guard(
    allowed: frozenset[str] | None = frozenset({PROJECT}),
) -> ProjectScopeGuard:
    store = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, store)
    return ProjectScopeGuard(
        store,
        allowed_project_ids=allowed,
        membership_depth=3,
    )


def test_allowed_project_is_accepted() -> None:
    guard().require_project(PROJECT)


def test_denied_project_is_rejected_without_listing_allowlist() -> None:
    with pytest.raises(ProjectAccessError, match="outside") as exc:
        guard(
            frozenset({"brain:project:other"})
        ).require_project(PROJECT)
    assert "other" not in str(exc.value)


def test_current_and_historical_project_nodes_are_members() -> None:
    value = guard()
    value.require_member(PROJECT, "brain:decision:radiance-primary")
    value.require_member(PROJECT, "brain:decision:cycles-primary")
    value.require_member(PROJECT, "edge:radiance-supersedes-cycles")


def test_bridge_and_who_objects_are_never_project_members() -> None:
    value = guard()
    with pytest.raises(ProjectAccessError):
        value.require_member(PROJECT, "who:user:master")
    with pytest.raises(ProjectAccessError):
        value.require_member(
            PROJECT,
            "edge:bridge:user-participates-lighting",
        )


def test_depth_limit_is_enforced() -> None:
    with pytest.raises(ProjectAccessError, match="depth"):
        guard().validate_requested_depth(4)
