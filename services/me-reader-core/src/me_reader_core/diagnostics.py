from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os

from .models import ZoteroPaper
from .zotero_links import item_select_uri, pdf_open_uri


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    code: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    generated_at: str
    vault_path: Path
    checks: tuple[DiagnosticCheck, ...]
    paper_key: str | None = None

    @property
    def overall_status(self) -> str:
        statuses = {check.status for check in self.checks}
        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses:
            return "WARN"
        return "PASS"

    def to_markdown(self) -> str:
        lines = [
            "# ME-Reader Diagnostic Report",
            "",
            f"- **Generated:** {self.generated_at}",
            f"- **Overall status:** {self.overall_status}",
            f"- **Vault:** `{self.vault_path}`",
            f"- **Zotero item key:** `{self.paper_key or 'not supplied'}`",
            "",
            "## Checks",
            "",
        ]
        lines.extend(
            f"- **{check.status}** `{check.code}` — {check.message}"
            for check in self.checks
        )
        lines.extend(
            [
                "",
                "## Sharing guidance",
                "",
                "This report contains configuration status only. It does not include PDF text, API keys, or personal notes.",
                "",
            ]
        )
        return "\n".join(lines)

    def write(self, output_path: Path) -> Path:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path


def run_diagnostics(vault_path: Path, paper: ZoteroPaper | None) -> DiagnosticReport:
    vault = Path(vault_path).expanduser().resolve()
    checks: list[DiagnosticCheck] = []

    if not vault.exists():
        checks.append(DiagnosticCheck("vault_exists", "FAIL", "The Obsidian vault directory does not exist."))
    elif not vault.is_dir():
        checks.append(DiagnosticCheck("vault_exists", "FAIL", "The configured vault path is not a directory."))
    else:
        checks.append(DiagnosticCheck("vault_exists", "PASS", "The Obsidian vault directory exists."))
        if os.access(vault, os.W_OK):
            checks.append(DiagnosticCheck("vault_writable", "PASS", "The vault directory is writable."))
        else:
            checks.append(DiagnosticCheck("vault_writable", "FAIL", "The vault directory is not writable."))
        papers_dir = vault / "papers"
        status = "PASS" if papers_dir.exists() else "WARN"
        message = "The papers directory exists." if papers_dir.exists() else "The papers directory will be created on first note generation."
        checks.append(DiagnosticCheck("papers_directory", status, message))

    if paper is None:
        checks.append(DiagnosticCheck("paper_metadata", "WARN", "No Zotero paper record was supplied for validation."))
    else:
        checks.append(DiagnosticCheck("paper_metadata", "PASS", f"Paper metadata is valid for item {paper.zotero_item_key}."))
        item_select_uri(paper.zotero_item_key)
        if paper.zotero_attachment_key:
            pdf_open_uri(paper.zotero_attachment_key)
            checks.append(DiagnosticCheck("zotero_pdf_link", "PASS", "A Zotero PDF return link can be generated."))
        else:
            checks.append(DiagnosticCheck("zotero_pdf_link", "WARN", "No PDF attachment key is available."))

    return DiagnosticReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        vault_path=vault,
        checks=tuple(checks),
        paper_key=paper.zotero_item_key if paper else None,
    )
