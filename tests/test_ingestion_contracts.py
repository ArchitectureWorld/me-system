from __future__ import annotations

from datetime import datetime, timezone

import pytest

from me_system.contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    EvidenceRef,
    GraphNamespace,
    ReviewStatus,
    Sensitivity,
    TemporalStatus,
)
from me_system.errors import ContractValidationError
from me_system.ingestion.contracts import (
    ActorKind,
    CandidateRecord,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    ReviewEvent,
    ReviewEventType,
    candidate_payload_sha256,
)


STARTED = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
COMPLETED = datetime(2026, 7, 23, 12, 5, tzinfo=timezone.utc)


def evidence() -> EvidenceRef:
    return EvidenceRef(
        source_id="source:conversation:001",
        content_fragment_id="fragment:conversation:001:42",
        source_anchor={
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": "msg-42"},
        },
    )


def pending_change() -> CandidateGraphChange:
    return CandidateGraphChange(
        change_id="candidate:decision:artificial-light-only",
        target_graph=GraphNamespace.ME_BRAIN,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:agent-conversation:0.1.0",
        reason="explicit project constraint in user message",
        evidence_refs=(evidence(),),
        payload={
            "schema_version": "graph-node/0.1",
            "id": "brain:constraint:artificial-light-only-v2",
            "graph": "me_brain",
            "type": "Constraint",
            "label": "第一阶段只考虑人工照明",
            "properties": {"scope": "lighting_calculation"},
            "authority": AuthorityLevel.CANDIDATE.value,
            "confirmation_status": ConfirmationStatus.PENDING.value,
            "status": TemporalStatus.CURRENT.value,
            "valid_from": "2026-07-23T10:30:00Z",
            "valid_to": None,
            "sensitivity": Sensitivity.PROJECT_PRIVATE.value,
            "source_refs": [evidence().to_dict()],
        },
    )


def test_running_ingestion_run_round_trip() -> None:
    run = IngestionRun.from_dict(
        {
            "run_id": "run:conversation:001:adapter-0.1.0",
            "source_id": "source:conversation:001",
            "adapter_name": "agent-conversation",
            "adapter_version": "0.1.0",
            "status": "running",
            "started_at": STARTED,
            "completed_at": None,
            "input_item_count": 100,
            "processed_item_count": 50,
            "skipped_item_count": 2,
            "failed_item_count": 1,
            "fragment_count": 50,
            "candidate_count": 4,
            "coverage_ratio": 0.5,
            "quality_report": {"unknown_roles": 1},
            "log_ref": "file:///logs/run-001.jsonl",
            "error_summary": None,
        }
    )
    assert run.status is IngestionStatus.RUNNING
    assert run.to_dict()["started_at"] == "2026-07-23T12:00:00Z"


def test_final_ingestion_state_requires_completed_at() -> None:
    with pytest.raises(ContractValidationError, match="completed_at"):
        IngestionRun.from_dict(
            {
                "run_id": "run:1",
                "source_id": "source:1",
                "adapter_name": "conversation",
                "adapter_version": "0.1.0",
                "status": "completed",
                "started_at": STARTED,
                "completed_at": None,
                "input_item_count": 1,
                "processed_item_count": 1,
                "skipped_item_count": 0,
                "failed_item_count": 0,
                "fragment_count": 1,
                "candidate_count": 1,
                "coverage_ratio": 1,
                "quality_report": {},
            }
        )


def test_active_ingestion_state_rejects_completed_at() -> None:
    with pytest.raises(ContractValidationError, match="completed_at"):
        IngestionRun.from_dict(
            {
                "run_id": "run:1",
                "source_id": "source:1",
                "adapter_name": "conversation",
                "adapter_version": "0.1.0",
                "status": "running",
                "started_at": STARTED,
                "completed_at": COMPLETED,
                "input_item_count": 1,
                "processed_item_count": 1,
                "skipped_item_count": 0,
                "failed_item_count": 0,
                "fragment_count": 1,
                "candidate_count": 1,
                "coverage_ratio": 1,
                "quality_report": {},
            }
        )


def test_ingestion_counts_cannot_exceed_input() -> None:
    with pytest.raises(ContractValidationError, match="input_item_count"):
        IngestionRun.from_dict(
            {
                "run_id": "run:1",
                "source_id": "source:1",
                "adapter_name": "conversation",
                "adapter_version": "0.1.0",
                "status": "running",
                "started_at": STARTED,
                "input_item_count": 2,
                "processed_item_count": 2,
                "skipped_item_count": 1,
                "failed_item_count": 0,
                "fragment_count": 2,
                "candidate_count": 1,
                "coverage_ratio": 1,
                "quality_report": {},
            }
        )


@pytest.mark.parametrize("ratio", [-0.01, 1.01])
def test_ingestion_coverage_is_bounded(ratio: float) -> None:
    with pytest.raises(ContractValidationError, match="coverage_ratio"):
        IngestionRun.from_dict(
            {
                "run_id": "run:1",
                "source_id": "source:1",
                "adapter_name": "conversation",
                "adapter_version": "0.1.0",
                "status": "running",
                "started_at": STARTED,
                "input_item_count": 1,
                "processed_item_count": 0,
                "skipped_item_count": 0,
                "failed_item_count": 0,
                "fragment_count": 0,
                "candidate_count": 0,
                "coverage_ratio": ratio,
                "quality_report": {},
            }
        )


def test_ingestion_result_applies_only_final_state() -> None:
    run = IngestionRun.new(
        run_id="run:1",
        source_id="source:1",
        adapter_name="conversation",
        adapter_version="0.1.0",
        started_at=STARTED,
        input_item_count=10,
    ).as_running()
    result = IngestionResult(
        status=IngestionStatus.PARTIAL,
        completed_at=COMPLETED,
        processed_item_count=8,
        skipped_item_count=1,
        failed_item_count=1,
        fragment_count=8,
        candidate_count=3,
        coverage_ratio=0.8,
        quality_report={"unknown": 1},
        log_ref=None,
        error_summary="one item could not be parsed",
    )
    completed = run.complete(result)
    assert completed.status is IngestionStatus.PARTIAL
    assert completed.completed_at == COMPLETED


def test_candidate_payload_hash_is_deterministic() -> None:
    payload = pending_change().payload
    reordered = {key: payload[key] for key in reversed(tuple(payload))}
    assert candidate_payload_sha256(payload) == candidate_payload_sha256(reordered)


def test_candidate_record_round_trip_and_hash_validation() -> None:
    change = pending_change()
    record = CandidateRecord(
        change=change,
        idempotency_key="agent-conversation:source:conversation:001:0.1.0:constraint:artificial-light",
        payload_sha256=candidate_payload_sha256(change.payload),
        created_at=STARTED,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id="run:conversation:001:adapter-0.1.0",
    )
    rebuilt = CandidateRecord.from_dict(record.to_dict())
    assert rebuilt == record
    assert rebuilt.change.review_status is ReviewStatus.PENDING


def test_candidate_record_rejects_incorrect_hash() -> None:
    with pytest.raises(ContractValidationError, match="payload_sha256"):
        CandidateRecord(
            change=pending_change(),
            idempotency_key="candidate-key",
            payload_sha256="0" * 64,
            created_at=STARTED,
            reviewed_at=None,
            approved_object_id=None,
            ingestion_run_id=None,
        )


def test_pending_candidate_rejects_reviewed_at() -> None:
    change = pending_change()
    with pytest.raises(ContractValidationError, match="reviewed_at"):
        CandidateRecord(
            change=change,
            idempotency_key="candidate-key",
            payload_sha256=candidate_payload_sha256(change.payload),
            created_at=STARTED,
            reviewed_at=COMPLETED,
            approved_object_id=None,
            ingestion_run_id=None,
        )


def test_review_event_round_trip() -> None:
    event = ReviewEvent.from_dict(
        {
            "event_id": "review-event:candidate-1:submitted",
            "change_id": "candidate:1",
            "event_type": "submitted",
            "actor_id": "adapter:conversation:0.1.0",
            "actor_kind": "adapter",
            "reason": "candidate submitted",
            "created_at": STARTED,
            "metadata": {"source_id": "source:conversation:001"},
        }
    )
    assert event.event_type is ReviewEventType.SUBMITTED
    assert event.actor_kind is ActorKind.ADAPTER
    assert event.to_dict()["created_at"] == "2026-07-23T12:00:00Z"
