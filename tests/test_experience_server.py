from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from me_system.experience.contracts import AcceptanceCheck, AcceptanceReport, CheckStatus
from me_system.experience.server import ExperienceApplication, create_server


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def make_report(run_number: int) -> AcceptanceReport:
    return AcceptanceReport(
        run_id=f"experience:run-{run_number}",
        started_at=NOW,
        completed_at=NOW + timedelta(milliseconds=10),
        checks=(
            AcceptanceCheck(
                check_id="database",
                title="数据库与迁移",
                status=CheckStatus.PASS,
                summary="通过",
                evidence={"run_number": run_number},
                duration_ms=10,
            ),
        ),
        highlights={"current_engine": "Radiance"},
        technical={"run_number": run_number},
        version="0.1.0",
    )


def test_server_exposes_health_html_report_and_rerun() -> None:
    counter = {"value": 0}

    def runner() -> AcceptanceReport:
        counter["value"] += 1
        return make_report(counter["value"])

    application = ExperienceApplication(runner)
    server = create_server("127.0.0.1", 0, application)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base}/healthz") as response:
            health = json.loads(response.read())
            assert response.headers["Cache-Control"] == "no-store"
        assert health == {"status": "ok", "acceptance": "pass"}

        with urlopen(f"{base}/") as response:
            html = response.read().decode("utf-8")
        assert "全部通过" in html
        assert "experience:run-1" in html

        with urlopen(f"{base}/api/report") as response:
            payload = json.loads(response.read())
            assert "attachment" in response.headers["Content-Disposition"]
        assert payload["run_id"] == "experience:run-1"

        request = Request(f"{base}/api/run", method="POST", data=b"")
        with urlopen(request) as response:
            rerun = json.loads(response.read())
        assert rerun["run_id"] == "experience:run-2"
        assert counter["value"] == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_server_returns_json_404_without_traceback() -> None:
    application = ExperienceApplication(lambda: make_report(1))
    server = create_server("127.0.0.1", 0, application)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest_http_error(f"http://127.0.0.1:{server.server_port}/missing") as payload:
            assert payload == {"error": "not_found"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class pytest_http_error:
    def __init__(self, url: str) -> None:
        self.url = url
        self.payload: dict[str, object] | None = None

    def __enter__(self) -> dict[str, object]:
        try:
            urlopen(self.url)
        except HTTPError as exc:
            assert exc.code == 404
            text = exc.read().decode("utf-8")
            assert "Traceback" not in text
            self.payload = json.loads(text)
            return self.payload
        raise AssertionError("expected HTTP 404")

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False
