from __future__ import annotations

from pathlib import Path

from me_reader_core.diagnostics import run_diagnostics
from me_reader_core.models import ZoteroPaper


def test_diagnostics_reports_missing_vault(tmp_path: Path) -> None:
    report = run_diagnostics(tmp_path / "missing", None)
    assert report.overall_status == "FAIL"
    assert any(check.code == "vault_exists" and check.status == "FAIL" for check in report.checks)


def test_diagnostics_writes_readable_markdown(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    paper = ZoteroPaper.from_dict({"zotero_item_key": "ABCD1234", "title": "Test paper"})
    report = run_diagnostics(vault, paper)
    output = report.write(tmp_path / "diagnostic.md")
    text = output.read_text(encoding="utf-8")
    assert "# ME-Reader Diagnostic Report" in text
    assert "ABCD1234" in text
    assert report.overall_status in {"PASS", "WARN"}
