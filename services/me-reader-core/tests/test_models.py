from __future__ import annotations

import pytest

from me_reader_core.models import PaperValidationError, ZoteroPaper


def test_from_dict_builds_a_normalized_paper() -> None:
    paper = ZoteroPaper.from_dict(
        {
            "zotero_item_key": "ABCD1234",
            "zotero_attachment_key": "PDFX5678",
            "citation_key": "wang2026bim",
            "title": "建筑信息模型研究",
            "authors": ["王强", {"firstName": "Li", "lastName": "Ming"}],
            "year": 2026,
            "publication": "建筑科学",
            "doi": "10.1000/example",
        }
    )
    assert paper.zotero_item_key == "ABCD1234"
    assert paper.zotero_attachment_key == "PDFX5678"
    assert paper.authors == ("王强", "Li Ming")
    assert paper.year == "2026"


def test_from_dict_requires_item_key() -> None:
    with pytest.raises(PaperValidationError, match="zotero_item_key"):
        ZoteroPaper.from_dict({"title": "Missing key"})


def test_from_dict_requires_title() -> None:
    with pytest.raises(PaperValidationError, match="title"):
        ZoteroPaper.from_dict({"zotero_item_key": "ABCD1234"})


def test_attachment_key_is_optional() -> None:
    paper = ZoteroPaper.from_dict({"zotero_item_key": "ABCD1234", "title": "Metadata only"})
    assert paper.zotero_attachment_key is None
