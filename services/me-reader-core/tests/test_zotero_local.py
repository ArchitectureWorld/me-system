from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from typing import Iterator

import pytest

from me_reader_core.zotero_local import ZoteroLocalApiError, ZoteroLocalClient


@contextmanager
def zotero_server(routes: dict[str, tuple[int, object, dict[str, str] | None]]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            route = routes.get(self.path)
            if route is None:
                self.send_response(404)
                self.end_headers()
                return
            status, body, headers = route
            payload = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_fetch_paper_reads_item_and_selects_pdf_attachment() -> None:
    routes = {
        "/api/users/0/items/ABCD1234": (
            200,
            {
                "key": "ABCD1234",
                "data": {
                    "itemType": "journalArticle",
                    "title": "建筑信息模型研究",
                    "creators": [
                        {"creatorType": "author", "firstName": "王", "lastName": "强"},
                        {"creatorType": "author", "name": "研究团队"},
                    ],
                    "date": "2026-05-01",
                    "publicationTitle": "建筑科学",
                    "DOI": "10.1000/example",
                    "extra": "Citation Key: wang2026bim",
                },
            },
            None,
        ),
        "/api/users/0/items/ABCD1234/children": (
            200,
            [
                {"key": "NOTE1234", "data": {"itemType": "note"}},
                {
                    "key": "PDFX5678",
                    "data": {
                        "itemType": "attachment",
                        "contentType": "application/pdf",
                        "filename": "paper.pdf",
                        "linkMode": "linked_file",
                    },
                },
            ],
            None,
        ),
    }
    with zotero_server(routes) as base_url:
        paper = ZoteroLocalClient(base_url).fetch_paper("ABCD1234")

    assert paper.zotero_item_key == "ABCD1234"
    assert paper.zotero_attachment_key == "PDFX5678"
    assert paper.citation_key == "wang2026bim"
    assert paper.authors == ("王 强", "研究团队")
    assert paper.year == "2026"
    assert paper.publication == "建筑科学"


def test_fetch_paper_allows_metadata_only_item() -> None:
    routes = {
        "/api/users/0/items/ABCD1234": (
            200,
            {"key": "ABCD1234", "data": {"title": "Metadata only", "creators": []}},
            None,
        ),
        "/api/users/0/items/ABCD1234/children": (200, [], None),
    }
    with zotero_server(routes) as base_url:
        paper = ZoteroLocalClient(base_url).fetch_paper("ABCD1234")

    assert paper.zotero_attachment_key is None


def test_probe_reads_api_version_header() -> None:
    routes = {
        "/api/": (200, {"ok": True}, {"Zotero-API-Version": "3", "Zotero-Schema-Version": "42"})
    }
    with zotero_server(routes) as base_url:
        probe = ZoteroLocalClient(base_url).probe()

    assert probe.api_version == "3"
    assert probe.schema_version == "42"


def test_403_has_enable_local_api_guidance() -> None:
    routes = {"/api/users/0/items/ABCD1234": (403, {"error": "Forbidden"}, None)}
    with zotero_server(routes) as base_url:
        with pytest.raises(ZoteroLocalApiError, match="Allow other applications"):
            ZoteroLocalClient(base_url).fetch_paper("ABCD1234")
