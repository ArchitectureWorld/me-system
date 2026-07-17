from __future__ import annotations

from pathlib import Path

from me_reader_core.models import ZoteroPaper
from me_reader_core.obsidian import create_or_find_paper_note


def make_paper() -> ZoteroPaper:
    return ZoteroPaper.from_dict(
        {
            "zotero_item_key": "ABCD1234",
            "zotero_attachment_key": "PDFX5678",
            "citation_key": "wang2026bim",
            "title": "建筑信息模型研究",
            "authors": ["王强", "李明"],
            "year": "2026",
            "publication": "建筑科学",
            "doi": "10.1000/example",
        }
    )


def test_create_paper_note_with_frontmatter_and_links(tmp_path: Path) -> None:
    result = create_or_find_paper_note(tmp_path / "vault", make_paper())
    assert result.status == "created"
    assert result.path.exists()
    content = result.path.read_text(encoding="utf-8")
    assert "mebrain_id: paper_zotero_abcd1234" in content
    assert "zotero_item_key: ABCD1234" in content
    assert "zotero://select/library/items/ABCD1234" in content
    assert "zotero://open-pdf/library/items/PDFX5678" in content
    assert "<!-- USER-CONTENT:START -->" in content
    assert "<!-- AGENT-CONTENT:START -->" in content


def test_second_run_finds_existing_note_without_duplicate(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    first = create_or_find_paper_note(vault, make_paper())
    second = create_or_find_paper_note(vault, make_paper())
    assert first.path == second.path
    assert second.status == "existing"
    assert list((vault / "papers").glob("*.md")) == [first.path]


def test_second_run_preserves_manual_user_content(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    first = create_or_find_paper_note(vault, make_paper())
    content = first.path.read_text(encoding="utf-8")
    content = content.replace(
        "<!-- USER-CONTENT:START -->\n<!-- USER-CONTENT:END -->",
        "<!-- USER-CONTENT:START -->\n我的人工阅读记录。\n<!-- USER-CONTENT:END -->",
    )
    first.path.write_text(content, encoding="utf-8")
    create_or_find_paper_note(vault, make_paper())
    assert "我的人工阅读记录。" in first.path.read_text(encoding="utf-8")
