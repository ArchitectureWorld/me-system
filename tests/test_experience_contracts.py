from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from me_system.experience.contracts import (
    AcceptanceCheck,
    AcceptanceReport,
    CheckStatus,
)
from me_system.experience.renderer import render_report_html


START = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def check(
    check_id: str,
    status: CheckStatus,
    *,
    title: str | None = None,
    summary: str = "验收完成",
) -> AcceptanceCheck:
    return AcceptanceCheck(
        check_id=check_id,
        title=title or check_id,
        status=status,
        summary=summary,
        evidence={"node_id": f"brain:task:{check_id}"},
        duration_ms=12,
        error_type=None if status is not CheckStatus.FAIL else "RuntimeError",
        error_message=None if status is not CheckStatus.FAIL else "脱敏错误",
    )


def report(*checks: AcceptanceCheck) -> AcceptanceReport:
    return AcceptanceReport(
        run_id="experience:abc12345",
        started_at=START,
        completed_at=START + timedelta(milliseconds=120),
        checks=checks,
        highlights={"current_engine": "Radiance"},
        technical={"tool_names": ["brain_get_snapshot", "who_get_task_profile"]},
        version="0.1.0",
    )


def test_report_passes_only_when_every_check_passes() -> None:
    value = report(
        check("database", CheckStatus.PASS),
        check("mcp", CheckStatus.PASS),
    )

    assert value.status == "pass"
    assert value.passed_count == 2
    assert value.failed_count == 0
    assert value.duration_ms == 120


def test_report_fails_when_any_check_fails() -> None:
    value = report(
        check("database", CheckStatus.PASS),
        check("mcp", CheckStatus.FAIL),
    )

    assert value.status == "fail"
    assert value.passed_count == 1
    assert value.failed_count == 1


def test_report_is_partial_when_a_check_is_skipped() -> None:
    value = report(
        check("database", CheckStatus.PASS),
        check("mcp", CheckStatus.SKIPPED),
    )

    assert value.status == "partial"


def test_report_json_round_trip_preserves_derived_status() -> None:
    value = report(check("database", CheckStatus.PASS))

    encoded = json.dumps(value.to_dict(), ensure_ascii=False)
    decoded = AcceptanceReport.from_dict(json.loads(encoded))

    assert decoded == value
    assert decoded.to_dict()["status"] == "pass"


def test_renderer_escapes_untrusted_text_and_exposes_json_download() -> None:
    value = report(
        check(
            "database",
            CheckStatus.PASS,
            title="<script>alert('x')</script>",
            summary="数据库已就绪",
        )
    )

    html = render_report_html(value)

    assert "<script>alert('x')</script>" not in html
    assert "&lt;script&gt;" in html
    assert "全部通过" in html
    assert "/api/report" in html
    assert "/api/run" in html
    assert "重新验收" in html


def test_renderer_shows_failure_without_traceback() -> None:
    value = report(check("mcp", CheckStatus.FAIL, summary="MCP 验收失败"))

    html = render_report_html(value)

    assert "验收未通过" in html
    assert "RuntimeError" in html
    assert "Traceback" not in html
