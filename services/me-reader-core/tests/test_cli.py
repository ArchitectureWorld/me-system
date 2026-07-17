from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def run_cli(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    return subprocess.run(
        [sys.executable, "-m", "me_reader_core", *args],
        cwd=project_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_creates_note_and_returns_json(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    item = tmp_path / "item.json"
    item.write_text(
        json.dumps(
            {
                "zotero_item_key": "ABCD1234",
                "zotero_attachment_key": "PDFX5678",
                "citation_key": "wang2026bim",
                "title": "建筑信息模型研究",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = run_cli(
        project_root,
        "create-paper-note",
        "--item-json",
        str(item),
        "--vault",
        str(tmp_path / "vault"),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "created"
    assert Path(payload["note_path"]).exists()


def test_cli_invalid_input_returns_nonzero(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    item = tmp_path / "item.json"
    item.write_text('{"title": "No key"}', encoding="utf-8")
    result = run_cli(
        project_root,
        "create-paper-note",
        "--item-json",
        str(item),
        "--vault",
        str(tmp_path / "vault"),
    )
    assert result.returncode == 2
    payload = json.loads(result.stderr)
    assert "zotero_item_key" in payload["error"]
