from __future__ import annotations

import pytest

from me_reader_core.zotero_links import item_select_uri, pdf_open_uri


def test_item_select_uri() -> None:
    assert item_select_uri("ABCD1234") == "zotero://select/library/items/ABCD1234"


def test_pdf_open_uri_without_page() -> None:
    assert pdf_open_uri("PDFX5678") == "zotero://open-pdf/library/items/PDFX5678"


def test_pdf_open_uri_with_page() -> None:
    assert pdf_open_uri("PDFX5678", page=12) == "zotero://open-pdf/library/items/PDFX5678?page=12"


def test_pdf_open_uri_returns_none_without_attachment() -> None:
    assert pdf_open_uri("") is None


def test_pdf_open_uri_rejects_non_positive_page() -> None:
    with pytest.raises(ValueError, match="positive"):
        pdf_open_uri("PDFX5678", page=0)
