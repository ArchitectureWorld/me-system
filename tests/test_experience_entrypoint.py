from __future__ import annotations

from pathlib import Path

from me_system.experience.__main__ import _parser


def test_entrypoint_uses_configured_project_root_and_loopback_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ME_SYSTEM_PROJECT_ROOT", str(tmp_path))

    args = _parser().parse_args(
        [
            "--database-url",
            f"sqlite+pysqlite:///{tmp_path / 'experience.db'}",
            "--allow-test-database",
            "--no-mcp",
        ]
    )

    assert args.fixture == (
        tmp_path / "examples" / "graph" / "lighting-platform.json"
    ).resolve()
    assert args.host == "127.0.0.1"
    assert args.port == 8765
