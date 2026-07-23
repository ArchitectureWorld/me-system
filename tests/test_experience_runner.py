from __future__ import annotations

from pathlib import Path

from me_system.experience.contracts import CheckStatus
from me_system.experience.runner import run_acceptance
from me_system.persistence.database import create_database_engine
from me_system.persistence.source_repository import SqlAlchemySourceRepository


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "graph" / "lighting-platform.json"


def test_core_acceptance_runs_real_dual_graph_flow_on_sqlite(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'experience.db'}"

    report = run_acceptance(
        database_url,
        FIXTURE,
        include_mcp=False,
        allow_test_database=True,
    )

    assert len(report.checks) == 8
    assert [item.status for item in report.checks[:7]] == [CheckStatus.PASS] * 7
    assert report.checks[7].status is CheckStatus.SKIPPED
    assert report.status == "partial"
    assert report.failed_count == 0
    assert report.highlights["current_engine"] == "Radiance"
    assert report.highlights["brain_task"] == "小白一键体验验收"
    assert "一键验收任务直接执行" in str(report.highlights["collaboration_rule"])

    engine = create_database_engine(database_url, production=False)
    repository = SqlAlchemySourceRepository(engine)
    source = repository.get(str(report.technical["source_id"]))
    fragments = repository.list_fragments(source.source_id)
    assert len(fragments) == 1
    assert "小白一键体验验收" in (fragments[0].text_content or "")


def test_core_acceptance_can_run_twice_without_identity_conflicts(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'experience.db'}"

    first = run_acceptance(
        database_url,
        FIXTURE,
        include_mcp=False,
        allow_test_database=True,
    )
    second = run_acceptance(
        database_url,
        FIXTURE,
        include_mcp=False,
        allow_test_database=True,
    )

    assert first.failed_count == 0
    assert second.failed_count == 0
    assert first.run_id != second.run_id
    assert first.technical["source_id"] != second.technical["source_id"]
    assert first.technical["brain_task_id"] != second.technical["brain_task_id"]
    assert first.technical["who_rule_id"] != second.technical["who_rule_id"]


def test_core_acceptance_returns_report_instead_of_leaking_traceback(tmp_path: Path) -> None:
    missing_fixture = tmp_path / "missing.json"
    database_url = f"sqlite+pysqlite:///{tmp_path / 'experience.db'}"

    report = run_acceptance(
        database_url,
        missing_fixture,
        include_mcp=False,
        allow_test_database=True,
    )

    assert report.status == "fail"
    assert report.failed_count >= 1
    error_text = " ".join(
        item.error_message or "" for item in report.checks if item.status is CheckStatus.FAIL
    )
    assert "Traceback" not in error_text
    assert database_url not in error_text
