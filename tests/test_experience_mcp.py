from __future__ import annotations

import pytest

from me_system.experience.mcp_check import validate_mcp_results
from me_system.hermes.mcp_server import TOOL_NAMES


BRAIN_TASK = "brain:task:one-click-acceptance-test"
WHO_RULE = "who:collaboration-rule:one-click-test"


def snapshot(*node_ids: str) -> dict[str, object]:
    return {
        "ok": True,
        "result": {"nodes": [{"id": value} for value in node_ids]},
    }


def profile(*node_ids: str) -> dict[str, object]:
    return {
        "ok": True,
        "result": {"nodes": [{"id": value} for value in node_ids]},
    }


def test_validate_mcp_results_accepts_exact_read_only_tool_set() -> None:
    result = validate_mcp_results(
        TOOL_NAMES,
        snapshot("brain:project:lighting-platform", BRAIN_TASK),
        profile("who:user:master", WHO_RULE),
        brain_task_id=BRAIN_TASK,
        who_rule_id=WHO_RULE,
    )

    assert tuple(result["tool_names"]) == TOOL_NAMES
    assert result["brain_task_visible"] is True
    assert result["who_rule_visible"] is True


def test_validate_mcp_results_rejects_any_extra_write_tool() -> None:
    with pytest.raises(ValueError, match="six read-only tools"):
        validate_mcp_results(
            (*TOOL_NAMES, "candidate_approve"),
            snapshot(BRAIN_TASK),
            profile(WHO_RULE),
            brain_task_id=BRAIN_TASK,
            who_rule_id=WHO_RULE,
        )


def test_validate_mcp_results_rejects_missing_brain_task() -> None:
    with pytest.raises(ValueError, match="ME-Brain Task"):
        validate_mcp_results(
            TOOL_NAMES,
            snapshot("brain:project:lighting-platform"),
            profile(WHO_RULE),
            brain_task_id=BRAIN_TASK,
            who_rule_id=WHO_RULE,
        )


def test_validate_mcp_results_rejects_missing_who_rule() -> None:
    with pytest.raises(ValueError, match="ME-Who CollaborationRule"):
        validate_mcp_results(
            TOOL_NAMES,
            snapshot(BRAIN_TASK),
            profile("who:user:master"),
            brain_task_id=BRAIN_TASK,
            who_rule_id=WHO_RULE,
        )
