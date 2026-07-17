from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import PaperValidationError, ZoteroPaper


_CITATION_KEY = re.compile(r"^\s*Citation Key\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
_YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ZoteroLocalApiError(RuntimeError):
    """Raised when the local Zotero API cannot provide the requested data."""


@dataclass(frozen=True, slots=True)
class ZoteroProbe:
    api_version: str | None
    schema_version: str | None


class ZoteroLocalClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        normalized = base_url.strip().rstrip("/")
        if not normalized:
            raise ValueError("zotero base URL must not be empty")
        parsed = urlparse(normalized)
        if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
            raise ValueError("zotero base URL must use HTTP on localhost or a loopback address")
        self.base_url = normalized
        self.timeout_seconds = timeout_seconds

    def _request_json(self, path: str) -> tuple[Any, Mapping[str, str]]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Zotero-API-Version": "3",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body) if body else None
                return payload, response.headers
        except HTTPError as exc:
            if exc.code == 403:
                raise ZoteroLocalApiError(
                    "Zotero Local API returned 403. In Zotero Settings → Advanced, enable "
                    "'Allow other applications on this computer to communicate with Zotero'."
                ) from exc
            if exc.code == 404:
                raise ZoteroLocalApiError(f"Zotero item or endpoint was not found: {path}") from exc
            raise ZoteroLocalApiError(f"Zotero Local API returned HTTP {exc.code} for {path}") from exc
        except URLError as exc:
            raise ZoteroLocalApiError(
                f"Unable to connect to Zotero Local API at {self.base_url}. "
                "Check that the correct Zotero instance is running and the configured port is correct."
            ) from exc
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ZoteroLocalApiError(f"Zotero Local API returned invalid JSON for {path}") from exc

    def probe(self) -> ZoteroProbe:
        _, headers = self._request_json("")
        return ZoteroProbe(
            api_version=headers.get("Zotero-API-Version"),
            schema_version=headers.get("Zotero-Schema-Version"),
        )

    def fetch_paper(self, item_key: str, citation_key_override: str | None = None) -> ZoteroPaper:
        key = item_key.strip()
        if not key:
            raise PaperValidationError("Missing required field: zotero_item_key")
        item_payload, _ = self._request_json(f"users/0/items/{key}")
        children_payload, _ = self._request_json(f"users/0/items/{key}/children")
        if not isinstance(item_payload, Mapping):
            raise ZoteroLocalApiError("Zotero item response must be a JSON object")
        data = item_payload.get("data")
        if not isinstance(data, Mapping):
            raise ZoteroLocalApiError("Zotero item response does not contain item data")
        if not isinstance(children_payload, list):
            raise ZoteroLocalApiError("Zotero children response must be a JSON array")

        attachment_key = self._select_pdf_attachment(children_payload)
        citation_key = citation_key_override or self._citation_key(data.get("extra"))
        return ZoteroPaper.from_dict(
            {
                "zotero_item_key": str(item_payload.get("key") or key),
                "zotero_attachment_key": attachment_key,
                "citation_key": citation_key,
                "title": data.get("title"),
                "authors": self._authors(data.get("creators")),
                "year": self._year(data.get("date")),
                "publication": data.get("publicationTitle") or data.get("proceedingsTitle") or data.get("bookTitle"),
                "doi": data.get("DOI"),
            }
        )

    @staticmethod
    def _citation_key(extra: object) -> str | None:
        if not isinstance(extra, str):
            return None
        match = _CITATION_KEY.search(extra)
        return match.group(1) if match else None

    @staticmethod
    def _year(date_value: object) -> str | None:
        if date_value is None:
            return None
        match = _YEAR.search(str(date_value))
        return match.group(1) if match else None

    @staticmethod
    def _authors(creators: object) -> list[str]:
        if not isinstance(creators, list):
            return []
        names: list[str] = []
        for creator in creators:
            if not isinstance(creator, Mapping):
                continue
            creator_type = str(creator.get("creatorType") or "author")
            if creator_type != "author":
                continue
            single_name = str(creator.get("name") or "").strip()
            if single_name:
                names.append(single_name)
                continue
            first = str(creator.get("firstName") or "").strip()
            last = str(creator.get("lastName") or "").strip()
            name = " ".join(part for part in (first, last) if part)
            if name:
                names.append(name)
        return names

    @staticmethod
    def _select_pdf_attachment(children: list[object]) -> str | None:
        candidates: list[tuple[int, str]] = []
        for child in children:
            if not isinstance(child, Mapping):
                continue
            data = child.get("data")
            if not isinstance(data, Mapping) or data.get("itemType") != "attachment":
                continue
            content_type = str(data.get("contentType") or "").lower()
            filename = str(data.get("filename") or "").lower()
            if content_type != "application/pdf" and not filename.endswith(".pdf"):
                continue
            key = str(child.get("key") or "").strip()
            if not key:
                continue
            link_mode = str(data.get("linkMode") or "")
            priority = 0 if link_mode in {"imported_file", "linked_file"} else 1
            candidates.append((priority, key))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][1]
