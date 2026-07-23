from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from me_core.contracts import Sensitivity
from me_core.errors import ContractValidationError
from me_core.ingestion.contracts import (
    EvidenceFragment,
    FragmentType,
    IngestionCounts,
    IngestionRun,
    IngestionStatus,
    SourceRecord,
)


UTC = timezone.utc


def source(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "source_id": "source:conversation:001",
        "source_type": "agent_conversation",
        "external_system": "hermes",
        "external_id": "conversation-001",
        "idempotency_key": "hermes:conversation-001:v1",
        "content_ref": "file:///data/conversation-001.json",
        "content_sha256": "a" * 64,
        "media_type": "application/json",
        "occurred_at": datetime(2026, 7, 22, 12, 0, tzinfo=timezone(timedelta(hours=8))),
        "ingested_at": datetime(2026, 7, 23, 4, 0, tzinfo=UTC),
        "sensitivity": Sensitivity.PROJECT_PRIVATE,
        "metadata": {"project_id": "brain:project:lighting-platform"},
    }
    values.update(overrides)
    return SourceRecord(**values)


def fragment(**overrides: object) -> EvidenceFragment:
    values: dict[str, object] = {
        "fragment_id": "fragment:conversation:001:42",
        "source_id": "source:conversation:001",
        "ordinal": 42,
        "fragment_type": FragmentType.CONVERSATION_MESSAGE,
        "text_content": "第一阶段只考虑人工照明。",
        "source_anchor": {
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": "msg-42"},
        },
        "content_sha256": "b" * 64,
        "occurred_at": datetime(2026, 7, 22, 4, 0, tzinfo=UTC),
        "actor_id": "who:user:master",
        "sensitivity": Sensitivity.PROJECT_PRIVATE,
        "metadata": {"language": "zh-CN"},
    }
    values.update(overrides)
    return EvidenceFragment(**values)


def pending_run(**overrides: object) -> IngestionRun:
    values: dict[str, object] = {
        "run_id": "run:conversation:001:v1",
        "source_id": "source:conversation:001",
        "adapter_name": "agent-conversation",
        "adapter_version": "0.1.0",
        "pipeline_version": "ingestion/0.1",
        "status": IngestionStatus.PENDING,
        "started_at": None,
        "completed_at": None,
        "counts": IngestionCounts(),
        "coverage_ratio": 0.0,
        "quality_report": {},
        "log_ref": None,
        "error_summary": None,
    }
    values.update(overrides)
    return IngestionRun(**values)


def test_source_round_trip_normalizes_timestamps_to_utc() -> None:
    value = source()
    restored = SourceRecord.from_dict(value.to_dict())
    assert restored == value
    assert restored.occurred_at == datetime(2026, 7, 22, 4, 0, tzinfo=UTC)
    assert restored.to_dict()["schema_version"] == "source-record/0.1"


def test_source_identity_ignores_storage_location_and_registration_metadata() -> None:
    first = source()
    replay = replace(
        first,
        source_id="source:conversation:replayed",
        content_ref="file:///new/location/conversation-001.json",
        ingested_at=datetime(2026, 7, 24, 4, 0, tzinfo=UTC),
    )
    assert first.identity_digest() == replay.identity_digest()
    assert first.identity_digest() != replace(first, content_sha256="c" * 64).identity_digest()


@pytest.mark.parametrize("digest", ["abc", "A" * 64, "g" * 64, "a" * 63])
def test_source_rejects_invalid_sha256(digest: str) -> None:
    with pytest.raises(ContractValidationError, match="content_sha256"):
        source(content_sha256=digest)


def test_fragment_round_trip_preserves_anchor_and_sensitivity() -> None:
    value = fragment()
    restored = EvidenceFragment.from_dict(value.to_dict())
    assert restored == value
    assert restored.source_anchor["value"]["message_id"] == "msg-42"
    assert restored.sensitivity is Sensitivity.PROJECT_PRIVATE


@pytest.mark.parametrize("ordinal", [-1, -10])
def test_fragment_rejects_negative_ordinal(ordinal: int) -> None:
    with pytest.raises(ContractValidationError, match="ordinal"):
        fragment(ordinal=ordinal)


def test_pending_run_can_start_and_finish_completed() -> None:
    created = pending_run()
    started = created.start(datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    assert started.status is IngestionStatus.RUNNING
    assert started.started_at == datetime(2026, 7, 23, 5, 0, tzinfo=UTC)

    finished = started.finish(
        status=IngestionStatus.COMPLETED,
        completed_at=datetime(2026, 7, 23, 5, 5, tzinfo=UTC),
        counts=IngestionCounts(
            input_item_count=10,
            processed_item_count=10,
            fragment_count=10,
            candidate_count=3,
        ),
        coverage_ratio=1.0,
        quality_report={"unknown_roles": 0},
        log_ref="file:///logs/run-001.jsonl",
    )
    assert finished.status is IngestionStatus.COMPLETED
    assert finished.counts.fragment_count == 10
    assert IngestionRun.from_dict(finished.to_dict()) == finished


@pytest.mark.parametrize("status", [IngestionStatus.PARTIAL, IngestionStatus.FAILED])
def test_running_run_can_finish_with_non_success_terminal_state(status: IngestionStatus) -> None:
    started = pending_run().start(datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    finished = started.finish(
        status=status,
        completed_at=datetime(2026, 7, 23, 5, 1, tzinfo=UTC),
        counts=IngestionCounts(
            input_item_count=10,
            processed_item_count=7,
            skipped_item_count=1,
            failed_item_count=2,
            fragment_count=7,
            candidate_count=1,
        ),
        coverage_ratio=0.7,
        quality_report={"failed_items": 2},
        error_summary="two items could not be normalized" if status is IngestionStatus.FAILED else None,
    )
    assert finished.status is status


@pytest.mark.parametrize(
    "count_values",
    [
        {"input_item_count": -1},
        {"input_item_count": 1, "processed_item_count": 2},
        {
            "input_item_count": 2,
            "processed_item_count": 1,
            "skipped_item_count": 1,
            "failed_item_count": 1,
        },
    ],
)
def test_ingestion_counts_reject_invalid_values(count_values: dict[str, int]) -> None:
    with pytest.raises(ContractValidationError):
        IngestionCounts(**count_values)


@pytest.mark.parametrize("coverage", [-0.1, 1.1])
def test_ingestion_run_rejects_invalid_coverage(coverage: float) -> None:
    with pytest.raises(ContractValidationError, match="coverage_ratio"):
        pending_run(coverage_ratio=coverage)


def test_terminal_run_requires_started_and_completed_timestamps() -> None:
    with pytest.raises(ContractValidationError, match="completed_at"):
        pending_run(
            status=IngestionStatus.COMPLETED,
            started_at=datetime(2026, 7, 23, 5, 0, tzinfo=UTC),
            completed_at=None,
        )


def test_running_run_cannot_start_twice_or_finish_as_running() -> None:
    started = pending_run().start(datetime(2026, 7, 23, 5, 0, tzinfo=UTC))
    with pytest.raises(ContractValidationError, match="pending"):
        started.start(datetime(2026, 7, 23, 5, 1, tzinfo=UTC))
    with pytest.raises(ContractValidationError, match="terminal"):
        started.finish(
            status=IngestionStatus.RUNNING,
            completed_at=datetime(2026, 7, 23, 5, 2, tzinfo=UTC),
            counts=IngestionCounts(),
            coverage_ratio=0.0,
            quality_report={},
        )
