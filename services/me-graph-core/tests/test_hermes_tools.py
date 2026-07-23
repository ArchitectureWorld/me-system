from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from me_graph_core.fixtures import load_graph_fixture
from me_graph_core.hermes.access import ProjectScopeGuard
from me_graph_core.hermes.resolver import ProjectResolver
from me_graph_core.hermes.tools import HermesReadOnlyTools
from me_graph_core.query import GraphQueryService
from me_graph_core.store import InMemoryGraphStore

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "graph"
    / "lighting-platform.json"
)
PROJECT = "brain:project:lighting-platform"


def graph_store() -> InMemoryGraphStore:
    store = InMemoryGraphStore()
    load_graph_fixture(FIXTURE, store)
    return store


def tools_for_store(
    store: InMemoryGraphStore,
    allowed: frozenset[str] | None = frozenset({PROJECT}),
) -> HermesReadOnlyTools:
    return HermesReadOnlyTools(
        resolver=ProjectResolver(store, allowed_project_ids=allowed),
        query=GraphQueryService(store),
        guard=ProjectScopeGuard(
            store,
            allowed_project_ids=allowed,
            membership_depth=3,
        ),
        hermes_user_id="who:user:master",
        max_subgraph_depth=2,
    )


def tools(
    allowed: frozenset[str] | None = frozenset({PROJECT}),
) -> HermesReadOnlyTools:
    return tools_for_store(graph_store(), allowed)


def assert_ok(value: dict[str, object]) -> object:
    assert value["ok"] is True
    return value["result"]


def test_resolve_project_tool() -> None:
    result = assert_ok(tools().resolve_project(query="照明平台"))
    assert result["project_id"] == PROJECT
    assert result["match_type"] == "alias"


def test_snapshot_excludes_superseded_decision() -> None:
    result = assert_ok(tools().get_snapshot(PROJECT))
    ids = {node["id"] for node in result["nodes"]}
    assert "brain:decision:radiance-primary" in ids
    assert "brain:decision:cycles-primary" not in ids
    assert result["excluded"]["superseded"] == [
        "brain:decision:cycles-primary"
    ]


def test_expand_filters_bridge_and_who_nodes() -> None:
    result = assert_ok(
        tools().expand_subgraph(PROJECT, PROJECT, depth=1)
    )
    assert all(node["graph"] == "me_brain" for node in result["nodes"])
    assert all(edge["graph"] == "me_brain" for edge in result["edges"])
    assert "who:user:master" not in {
        node["id"] for node in result["nodes"]
    }


def test_trace_decision_and_evidence() -> None:
    trace = assert_ok(
        tools().trace_decision(
            PROJECT,
            "brain:decision:radiance-primary",
        )
    )
    assert {node["id"] for node in trace["nodes"]} == {
        "brain:decision:radiance-primary",
        "brain:decision:cycles-primary",
    }
    refs = assert_ok(
        tools().get_evidence(
            PROJECT,
            "brain:decision:radiance-primary",
        )
    )
    assert refs[0]["source_id"] == "src:conversation:2026-07-14"


def test_trace_decision_filters_cross_project_history() -> None:
    store = graph_store()
    current_project = store.get_node(PROJECT)
    current_decision = store.get_node("brain:decision:radiance-primary")
    ownership = store.get_edge("edge:project-has-radiance")
    history = store.get_edge("edge:radiance-supersedes-cycles")

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
    store.add_node(other_project)
    store.add_node(other_decision)
    store.add_edge(
        replace(
            ownership,
            id="edge:other-has-decision",
            from_id=other_project.id,
            to_id=other_decision.id,
        )
    )
    store.add_edge(
        replace(
            history,
            id="edge:cross-project-history",
            from_id=current_decision.id,
            to_id=other_decision.id,
        )
    )

    trace = assert_ok(
        tools_for_store(store).trace_decision(
            PROJECT,
            current_decision.id,
        )
    )
    assert other_decision.id not in {
        node["id"] for node in trace["nodes"]
    }
    assert "edge:cross-project-history" not in {
        edge["id"] for edge in trace["edges"]
    }


def test_task_profile_uses_fixed_user() -> None:
    result = assert_ok(
        tools().get_task_profile(PROJECT, "implementation")
    )
    ids = {node["id"] for node in result["nodes"]}
    assert "who:user:master" in ids
    assert "who:collaboration-rule:direct-execution" in ids
    assert "who:collaboration-rule:architecture-first" not in ids


def test_denied_project_has_safe_error_envelope() -> None:
    value = tools(
        frozenset({"brain:project:other"})
    ).get_snapshot(PROJECT)
    assert value == {
        "ok": False,
        "error": {
            "code": "PROJECT_NOT_ALLOWED",
            "message": (
                "requested project is outside the configured Hermes scope"
            ),
            "retryable": False,
        },
    }


def test_depth_violation_is_structured() -> None:
    value = tools().expand_subgraph(PROJECT, PROJECT, depth=3)
    assert value["ok"] is False
    assert value["error"]["code"] == "INVALID_ARGUMENT"


def test_bridge_evidence_cannot_be_read() -> None:
    value = tools().get_evidence(
        PROJECT,
        "edge:bridge:user-participates-lighting",
    )
    assert value["ok"] is False
    assert value["error"]["code"] == "PROJECT_NOT_ALLOWED"
