from __future__ import annotations

from me_reader_core.identity import document_id, paper_id, paper_note_filename
from me_reader_core.models import ZoteroPaper


def make_paper(**overrides: object) -> ZoteroPaper:
    data: dict[str, object] = {"zotero_item_key": "ABCD1234", "title": "A / Study: BIM?"}
    data.update(overrides)
    return ZoteroPaper.from_dict(data)


def test_ids_are_stable_and_key_based() -> None:
    assert paper_id("ABCD1234") == "paper_zotero_abcd1234"
    assert document_id("ABCD1234") == "doc_zotero_abcd1234"


def test_filename_prefers_citation_key_and_keeps_item_suffix() -> None:
    assert paper_note_filename(make_paper(citation_key="wang2026bim")) == "wang2026bim--ABCD1234.md"


def test_filename_falls_back_to_safe_title() -> None:
    filename = paper_note_filename(make_paper())
    assert filename == "A-Study-BIM--ABCD1234.md"
    assert "/" not in filename
    assert "\\" not in filename


def test_filename_supports_chinese_titles() -> None:
    assert paper_note_filename(make_paper(title="建筑照明 方法研究")) == "建筑照明-方法研究--ABCD1234.md"
