from __future__ import annotations


def _required_key(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def item_select_uri(item_key: str) -> str:
    key = _required_key(item_key, "item_key")
    return f"zotero://select/library/items/{key}"


def pdf_open_uri(attachment_key: str | None, page: int | None = None) -> str | None:
    if attachment_key is None or not attachment_key.strip():
        return None
    if page is not None and page <= 0:
        raise ValueError("page must be a positive integer")
    key = attachment_key.strip()
    uri = f"zotero://open-pdf/library/items/{key}"
    return f"{uri}?page={page}" if page is not None else uri
