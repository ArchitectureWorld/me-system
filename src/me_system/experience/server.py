from __future__ import annotations

from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Callable

from .contracts import AcceptanceCheck, AcceptanceReport, CheckStatus
from .renderer import render_report_html


ReportRunner = Callable[[], AcceptanceReport]


def _fatal_report(exc: Exception) -> AcceptanceReport:
    now = datetime.now(timezone.utc)
    message = (str(exc).strip() or type(exc).__name__)[:320]
    message = message.replace("Traceback", "错误详情")
    return AcceptanceReport(
        run_id=f"experience:fatal-{now.strftime('%H%M%S')}",
        started_at=now,
        completed_at=now,
        checks=(
            AcceptanceCheck(
                check_id="startup",
                title="体验服务启动",
                status=CheckStatus.FAIL,
                summary="验收服务已启动，但核心验收未能执行。",
                evidence={},
                duration_ms=0,
                error_type=type(exc).__name__,
                error_message=message,
            ),
        ),
        highlights={"next_action": "查看 Docker experience 服务日志"},
        technical={},
        version="0.1.0",
    )


class ExperienceApplication:
    """Thread-safe current acceptance report and rerun coordinator."""

    def __init__(self, runner: ReportRunner) -> None:
        self._runner = runner
        self._lock = Lock()
        self._report = self._execute()

    def _execute(self) -> AcceptanceReport:
        try:
            value = self._runner()
            if not isinstance(value, AcceptanceReport):
                raise TypeError("experience runner must return AcceptanceReport")
            return value
        except Exception as exc:  # Keep the dashboard available for diagnosis.
            return _fatal_report(exc)

    @property
    def report(self) -> AcceptanceReport:
        with self._lock:
            return self._report

    def rerun(self) -> AcceptanceReport:
        with self._lock:
            self._report = self._execute()
            return self._report


class _ExperienceServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        application: ExperienceApplication,
    ) -> None:
        self.application = application
        super().__init__(server_address, handler_class)


def _handler_class() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server: _ExperienceServer

        def _headers(
            self,
            status: int,
            content_type: str,
            length: int,
            *,
            disposition: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if disposition is not None:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()

        def _json(
            self,
            status: int,
            payload: object,
            *,
            disposition: str | None = None,
        ) -> None:
            body = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            self._headers(
                status,
                "application/json; charset=utf-8",
                len(body),
                disposition=disposition,
            )
            self.wfile.write(body)

        def _html(self, status: int, body_text: str) -> None:
            body = body_text.encode("utf-8")
            self._headers(status, "text/html; charset=utf-8", len(body))
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path == "/":
                self._html(200, render_report_html(self.server.application.report))
                return
            if self.path == "/healthz":
                self._json(
                    200,
                    {
                        "status": "ok",
                        "acceptance": self.server.application.report.status,
                    },
                )
                return
            if self.path == "/api/report":
                self._json(
                    200,
                    self.server.application.report.to_dict(),
                    disposition='attachment; filename="me-system-acceptance.json"',
                )
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/api/run":
                self._json(404, {"error": "not_found"})
                return
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            if content_length:
                self.rfile.read(content_length)
            self._json(200, self.server.application.rerun().to_dict())

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def create_server(
    host: str,
    port: int,
    application: ExperienceApplication,
) -> ThreadingHTTPServer:
    return _ExperienceServer((host, int(port)), _handler_class(), application)
