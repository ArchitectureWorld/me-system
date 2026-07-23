from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from me_core.errors import ProjectAccessError
from me_core.fixtures import load_graph_fixture
from me_core.hermes.access import ProjectScopeGuard
from me_core.store import InMemoryGraphStore

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"


def store() -> InMemoryGraphStore:
    value = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, value)
    return value


def guard(
    allowed: frozenset[str] | None = frozenset({PROJECT}),
) -> ProjectScopeGuard:
    return ProjectScopeGuard(
        store(),
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


def test_arbitrary_relation_does_not_import_another_project_node() -> None:
    graph = store()
    current_project = graph.get_node(PROJECT)
    current_decision = graph.get_node("brain:decision:radiance-primary")
    ownership = graph.get_edge("edge:project-has-radiance")
    history = graph.get_edge("edge:radiance-supersedes-cycles")

    other_project = replace(
        current_project,
        id="brain:project:other",
        label="other",
        properties={"aliases": ["other"]},
    )
    other_decision = replace(
        current_decision,
        id="brain:decision:other",
        label="Other project decision",
    )
    graph.add_node(other_project)
    graph.add_node(other_decision)
    graph.add_edge(
        replace(
            ownership,
            id="edge:other-has-decision",
            from_id=other_project.id,
            to_id=other_decision.id,
        )
    )
    graph.add_edge(
        replace(
            history,
            id="edge:cross-project-history",
            from_id=current_decision.id,
            to_id=other_decision.id,
        )
    )

    value = ProjectScopeGuard(
        graph,
        allowed_project_ids=frozenset({PROJECT}),
        membership_depth=3,
    )
    with pytest.raises(ProjectAccessError):
        value.require_member(PROJECT, other_decision.id)


def test_depth_limit_is_enforced() -> None:
    with pytest.raises(ProjectAccessError, match="depth"):
        guard().validate_requested_depth(4)
