from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


class PaperValidationError(ValueError):
    """Raised when a Zotero paper record cannot be used safely."""


def _required_text(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if value is None or not str(value).strip():
        raise PaperValidationError(f"Missing required field: {key}")
    return str(value).strip()


def _optional_text(data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        normalized = value.strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, Sequence):
        raise PaperValidationError("authors must be a string or a list")

    authors: list[str] = []
    for author in value:
        if isinstance(author, str):
            name = author.strip()
        elif isinstance(author, Mapping):
            first = str(author.get("firstName") or author.get("first_name") or "").strip()
            last = str(author.get("lastName") or author.get("last_name") or "").strip()
            name = " ".join(part for part in (first, last) if part)
        else:
            raise PaperValidationError("each author must be text or a name mapping")
        if name:
            authors.append(name)
    return tuple(authors)


@dataclass(frozen=True, slots=True)
class ZoteroPaper:
    zotero_item_key: str
    title: str
    zotero_attachment_key: str | None = None
    citation_key: str | None = None
    authors: tuple[str, ...] = ()
    year: str | None = None
    publication: str | None = None
    doi: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ZoteroPaper":
        return cls(
            zotero_item_key=_required_text(data, "zotero_item_key"),
            title=_required_text(data, "title"),
            zotero_attachment_key=_optional_text(data, "zotero_attachment_key"),
            citation_key=_optional_text(data, "citation_key"),
            authors=_normalize_authors(data.get("authors")),
            year=_optional_text(data, "year"),
            publication=_optional_text(data, "publication"),
            doi=_optional_text(data, "doi"),
        )

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["authors"] = list(self.authors)
        return result
