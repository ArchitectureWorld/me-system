from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "experience" / "compose.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_compose_exposes_only_dashboard_and_keeps_postgres_private() -> None:
    text = read(COMPOSE)
    postgres_block = text.split("  postgres:", 1)[1].split("  experience:", 1)[0]
    experience_block = text.split("  experience:", 1)[1]

    assert "postgres:16" in postgres_block
    assert "ports:" not in postgres_block
    assert '"8765:8765"' in experience_block
    assert "ME_GRAPH_DATABASE_URL" in experience_block
    assert "condition: service_healthy" in experience_block


def test_dockerfile_runs_real_experience_module_with_migration_root() -> None:
    text = read(ROOT / "deploy" / "experience" / "Dockerfile")

    assert "FROM python:3.12" in text
    assert "pip install --no-cache-dir ." in text
    assert "ME_SYSTEM_PROJECT_ROOT=/app" in text
    assert '"-m", "me_system.experience"' in text
    assert "EXPOSE 8765" in text


def test_all_launchers_use_the_same_compose_and_dashboard_url() -> None:
    paths = [ROOT / "体验.sh", ROOT / "体验.command", ROOT / "体验.bat"]
    for path in paths:
        text = read(path)
        assert "deploy/experience/compose.yml" in text.replace("\\", "/")
        assert "http://localhost:8765" in text
        assert "docker compose" in text


def test_unix_launchers_are_executable_after_checkout() -> None:
    for path in [ROOT / "体验.sh", ROOT / "体验.command", ROOT / "停止体验.sh"]:
        assert os.access(path, os.X_OK), f"{path.name} must be executable"


def test_stop_launchers_remove_only_experience_stack() -> None:
    for path in [ROOT / "停止体验.sh", ROOT / "停止体验.bat"]:
        text = read(path)
        assert "deploy/experience/compose.yml" in text.replace("\\", "/")
        assert "down" in text
        assert "docker system prune" not in text


def test_readme_makes_one_click_experience_the_primary_onboarding() -> None:
    text = read(ROOT / "README.md")
    heading_position = text.index("小白一键体验")
    architecture_position = text.index("一句话架构")

    assert heading_position < architecture_position
    assert "体验.bat" in text
    assert "体验.command" in text
    assert "体验.sh" in text
    assert "Docker Desktop" in text
    assert "http://localhost:8765" in text


def test_docker_context_excludes_local_and_private_artifacts() -> None:
    text = read(ROOT / ".dockerignore")

    assert ".git" in text
    assert ".env" in text
    assert "__pycache__" in text
    assert ".pytest_cache" in text
