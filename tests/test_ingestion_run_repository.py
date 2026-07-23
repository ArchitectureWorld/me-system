from __future__ import annotations

from datetime import datetime, timezone

import pytest

from me_system.contracts import Sensitivity
from me_system.errors import IngestionStateError, SourceNotFoundError
from me_system.evidence.contracts import SourceRecord
from me_system.ingestion.contracts import IngestionResult, IngestionRun, IngestionStatus
from me_system.persistence.models import create_schema
from me_system.persistence.source_repository import SqlAlchemySourceRepository
from me_system.persistence.testing import create_sqlite_test_engine


STARTED = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
COMPLETED = datetime(2026, 7, 23, 12, 5, tzinfo=timezone.utc)


def source() -> SourceRecord:
    return SourceRecord(
        source_id="source:conversation:001",
        source_type="agent_conversation",
        external_system="hermes",
        external_id="conversation-001",
        idempotency_key="hermes:conversation-001:export-1",
        content_ref="file:///data/conversation-001.json",
        content_sha256="a" * 64,
        media_type="application/json",
        occurred_at=STARTED,
        ingested_at=STARTED,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
        metadata={},
    )


def run() -> IngestionRun:
    return IngestionRun.new(
        run_id="run:conversation:001:0.1.0",
        source_id=source().source_id,
        adapter_name="agent-conversation",
        adapter_version="0.1.0",
        started_at=STARTED,
        input_item_count=10,
    )


@pytest.fixture
def repository() -> SqlAlchemySourceRepository:
    engine = create_sqlite_test_engine()
    create_schema(engine)
    value = SqlAlchemySourceRepository(engine)
    value.register(source())
    return value


def test_create_get_and_start_ingestion_run(repository: SqlAlchemySourceRepository) -> None:
    pending = repository.create_run(run())
    assert pending.status is IngestionStatus.PENDING
    running = repository.start_run(pending.run_id)
    assert running.status is IngestionStatus.RUNNING
    assert repository.get_run(pending.run_id) == running


def test_run_requires_existing_source() -> None:
    engine = create_sqlite_test_engine()
    create_schema(engine)
    repository = SqlAlchemySourceRepository(engine)
    with pytest.raises(SourceNotFoundError):
        repository.create_run(run())


def test_complete_run_persists_coverage_and_quality(repository: SqlAlchemySourceRepository) -> None:
    repository.create_run(run())
    repository.start_run(run().run_id)
    completed = repository.complete_run(
        run().run_id,
        IngestionResult(
            status=IngestionStatus.PARTIAL,
            completed_at=COMPLETED,
            processed_item_count=8,
            skipped_item_count=1,
            failed_item_count=1,
            fragment_count=8,
            candidate_count=3,
            coverage_ratio=0.8,
            quality_report={"unknown_roles": 1},
            log_ref="file:///logs/run-001.jsonl",
            error_summary="one message could not be parsed",
        ),
    )
    assert completed.status is IngestionStatus.PARTIAL
    assert completed.coverage_ratio == 0.8
    assert completed.quality_report == {"unknown_roles": 1}
    assert repository.get_run(run().run_id) == completed


def test_completed_run_cannot_restart_or_complete_twice(repository: SqlAlchemySourceRepository) -> None:
    repository.create_run(run())
    repository.start_run(run().run_id)
    result = IngestionResult(
        status=IngestionStatus.COMPLETED,
        completed_at=COMPLETED,
        processed_item_count=10,
        skipped_item_count=0,
        failed_item_count=0,
        fragment_count=10,
        candidate_count=2,
        coverage_ratio=1,
        quality_report={},
    )
    repository.complete_run(run().run_id, result)
    with pytest.raises(IngestionStateError):
        repository.start_run(run().run_id)
    with pytest.raises(IngestionStateError):
        repository.complete_run(run().run_id, result)


def test_duplicate_run_id_is_rejected(repository: SqlAlchemySourceRepository) -> None:
    repository.create_run(run())
    with pytest.raises(IngestionStateError):
        repository.create_run(run())
