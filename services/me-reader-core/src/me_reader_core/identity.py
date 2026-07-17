from __future__ import annotations

import re
import unicodedata

from .models import ZoteroPaper


_INVALID_FILENAME = re.compile(r"[\\/:*?\"<>|]+")
_WHITESPACE = re.compile(r"\s+")
_DASHES = re.compile(r"-+")


def _normalized_key(item_key: str) -> str:
    normalized = item_key.strip().lower()
    if not normalized:
        raise ValueError("item_key must not be empty")
    return normalized


def paper_id(item_key: str) -> str:
    return f"paper_zotero_{_normalized_key(item_key)}"


def document_id(item_key: str) -> str:
    return f"doc_zotero_{_normalized_key(item_key)}"


def _safe_stem(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = _INVALID_FILENAME.sub("-", normalized)
    normalized = _WHITESPACE.sub("-", normalized)
    normalized = _DASHES.sub("-", normalized).strip("-. ")
    return normalized or "untitled"


def paper_note_filename(paper: ZoteroPaper) -> str:
    stem = _safe_stem(paper.citation_key or paper.title)
    key = _safe_stem(paper.zotero_item_key.upper())
    return f"{stem}--{key}.md"
