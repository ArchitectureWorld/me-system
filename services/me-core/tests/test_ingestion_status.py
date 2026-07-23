from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from me_core.contracts import Sensitivity
from me_core.errors import IngestionRunError, IngestionRunNotFoundError, SourceNotFoundError
from me_core.ingestion.contracts import (
    IngestionCounts,
    IngestionRun,
    IngestionStatus,
    SourceRecord,
)
from me_core.ingestion.source import SourceLedgerService
from me_core.ingestion.status import IngestionStatusService
from me_core.persistence.ingestion_repository import SqlAlchemyIngestionRepository
from me_core.persistence.models import create_schema
from me_core.persistence.testing import create_sqlite_test_engine


UTC = timezone.utc


def source() -> SourceRecord:
    return SourceRecord(
        source_id="source:conversation:001",
        source_type="agent_conversation",
        external_system="hermes",
        external_id="conversation-001",
        idempotency_key="hermes:conversation-001:v1",
        content_ref="file:///data/conversation-001.json",
        content_sha256="a" * 64,
        media_type="application/json",
        occurred_at=datetime(2026, 7, 22, 4, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 7, 23, 4, 0, tzinfo=UTC),
        sensitivity=Sensitivity.PROJECT_PRIVATE,
        metadata={},
    )


def pending_run(run_id: str = "run:001") -> IngestionRun:
    return IngestionRun(
        run_id=run_id,
        source_id=source().source_id,
        adapter_name="agent-conversation",
        adapter_version="0.1.0",
        pipeline_version="ingestion/0.1",
        status=IngestionStatus.PENDING,
        started_at=None,
        completed_at=None,
        counts=IngestionCounts(),
        coverage_ratio=0.0,
        quality_report={},
        log_ref=None,
        error_summary=None,
    )


def services(url: str = "sqlite+pysqlite:///:memory:") -> tuple[SourceLedgerService, IngestionStatusService]:
    engine = create_sqlite_test_engine(url)
    create_schema(engine)
    repository = SqlAlchemyIngestionRepository(engine)
    return SourceLedgerService(repository), IngestionStatusService(repository)


def ready_services(url: str = "sqlite+pysqlite:///:memory:") -> IngestionStatusService:
    ledger, status = services(url)
    ledger.register_source(source())
    return status


def test_create_and_get_pending_run() -> None:
    status = ready_services()
    value = status.create_run(pending_run())
    assert value.status is IngestionStatus.PENDING
    assert status.get_run(value.run_id) == value


def test_run_requires_existing_source() -> None:
    _, status = services()
    with pytest.raises(SourceNotFoundError):
        status.create_run(pending_run())


def test_duplicate_run_id_is_rejected() -> None:
    status = ready_services()
    status.create_run(pending_run())
    with pytest.raises(IngestionRunError, match="run_id"):
        status.create_run(pending_run())


def test_pending_run_starts_and_persists() -> None:
    status = ready_services()
    status.create_run(pending_run())
    started_at = datetime(2026, 7, 23, 5, 0, tzinfo=UTC)
    value = status.start_run("run:001", started_at=started_at)
    assert value.status is IngestionStatus.RUNNING
    assert value.started_at == started_at
    assert status.get_run("run:001") == value


@pytest.mark.parametrize(
    ("terminal", "coverage", "error_summary"),
    [
        (IngestionStatus.COMPLETED, 1.0, None),
        (IngestionStatus.PARTIAL, 0.7, "two items skipped"),
        (IngestionStatus.FAILED, 0.2, "normalization failed"),
    ],
)
def test_running_run_finishes_with_quality_and_counts(
    terminal: IngestionStatus,
    coverage: float,
    error_summary: str | None,
) -> None:
    status = ready_services()
    status.create_run(pending_run())
    status.start_run("run:001", started_at=datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    value = status.finish_run(
        "run:001",
        status=terminal,
        counts=IngestionCounts(
            input_item_count=10,
            processed_item_count=7,
            skipped_item_count=2,
            failed_item_count=1,
            fragment_count=7,
            candidate_count=2,
        ),
        coverage_ratio=coverage,
        quality_report={"unknown_roles": 1},
        log_ref="file:///logs/run-001.jsonl",
        error_summary=error_summary,
        completed_at=datetime(2026, 7, 23, 5, 5, tzinfo=UTC),
    )
    assert value.status is terminal
    assert value.counts.fragment_count == 7
    assert value.quality_report == {"unknown_roles": 1}
    assert status.get_run("run:001") == value


def test_illegal_transitions_are_rejected_and_original_row_is_unchanged() -> None:
    status = ready_services()
    status.create_run(pending_run())
    with pytest.raises(IngestionRunError, match="running"):
        status.finish_run(
            "run:001",
            status=IngestionStatus.COMPLETED,
            counts=IngestionCounts(),
            coverage_ratio=0.0,
            quality_report={},
        )
    assert status.get_run("run:001").status is IngestionStatus.PENDING

    status.start_run("run:001", started_at=datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    with pytest.raises(IngestionRunError, match="pending"):
        status.start_run("run:001", started_at=datetime(2026, 7, 23, 5, 1, tzinfo=UTC))

    status.finish_run(
        "run:001",
        status=IngestionStatus.COMPLETED,
        counts=IngestionCounts(),
        coverage_ratio=0.0,
        quality_report={},
        completed_at=datetime(2026, 7, 23, 5, 2, tzinfo=UTC),
    )
    with pytest.raises(IngestionRunError, match="running"):
        status.finish_run(
            "run:001",
            status=IngestionStatus.COMPLETED,
            counts=IngestionCounts(),
            coverage_ratio=0.0,
            quality_report={},
        )


def test_missing_run_raises_domain_error() -> None:
    with pytest.raises(IngestionRunNotFoundError, match="missing"):
        ready_services().get_run("run:missing")


def test_runs_are_listed_newest_started_first_with_pending_last() -> None:
    status = ready_services()
    for run_id in ("run:pending", "run:older", "run:newer"):
        status.create_run(pending_run(run_id))
    base = datetime(2026, 7, 23, 5, 0, tzinfo=UTC)
    status.start_run("run:older", started_at=base)
    status.start_run("run:newer", started_at=base + timedelta(minutes=5))
    assert [run.run_id for run in status.list_runs(source().source_id)] == [
        "run:newer",
        "run:older",
        "run:pending",
    ]


def test_run_survives_service_recreation(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'ingestion.db'}"
    first = ready_services(url)
    first.create_run(pending_run())
    first.start_run("run:001", started_at=datetime(2026, 7, 23, 5, 0, tzinfo=UTC))

    _, second = services(url)
    assert second.get_run("run:001").status is IngestionStatus.RUNNING


def test_error_summary_redacts_embedded_database_password() -> None:
    status = ready_services()
    status.create_run(pending_run())
    status.start_run("run:001", started_at=datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    value = status.finish_run(
        "run:001",
        status=IngestionStatus.FAILED,
        counts=IngestionCounts(input_item_count=1, failed_item_count=1),
        coverage_ratio=0.0,
        quality_report={"database_error": True},
        error_summary=(
            "could not connect to "
            "postgresql+psycopg://me_graph:super-secret@127.0.0.1:5432/me_graph"
        ),
        completed_at=datetime(2026, 7, 23, 5, 1, tzinfo=UTC),
    )
    assert "super-secret" not in (value.error_summary or "")
    assert "***" in (value.error_summary or "")
