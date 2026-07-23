from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "graph" / "lighting-platform.json"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "me_graph_core", *args],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_load_fixture_reports_graph_counts() -> None:
    result = run_cli("load-fixture", "--fixture", str(FIXTURE))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["nodes"] == {"me_brain": 10, "me_who": 5}
    assert payload["edges"]["bridge"] == 1


def test_project_snapshot_returns_current_radiance_decision() -> None:
    result = run_cli(
        "project-snapshot",
        "--fixture",
        str(FIXTURE),
        "--project-id",
        "brain:project:lighting-platform",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ids = {node["id"] for node in payload["nodes"]}
    assert "brain:decision:radiance-primary" in ids
    assert "brain:decision:cycles-primary" not in ids


def test_trace_decision_returns_history() -> None:
    result = run_cli(
        "trace-decision",
        "--fixture",
        str(FIXTURE),
        "--decision-id",
        "brain:decision:radiance-primary",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert {node["id"] for node in payload["nodes"]} == {
        "brain:decision:radiance-primary",
        "brain:decision:cycles-primary",
    }


def test_task_profile_filters_collaboration_rules() -> None:
    result = run_cli(
        "task-profile",
        "--fixture",
        str(FIXTURE),
        "--user-id",
        "who:user:master",
        "--project-id",
        "brain:project:lighting-platform",
        "--task-type",
        "implementation",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ids = {node["id"] for node in payload["nodes"]}
    assert "who:collaboration-rule:direct-execution" in ids
    assert "who:collaboration-rule:architecture-first" not in ids


def test_invalid_identifier_returns_structured_error() -> None:
    result = run_cli(
        "project-snapshot",
        "--fixture",
        str(FIXTURE),
        "--project-id",
        "brain:project:missing",
    )
    assert result.returncode == 2
    payload = json.loads(result.stderr)
    assert payload["error_type"] == "GraphObjectNotFoundError"
