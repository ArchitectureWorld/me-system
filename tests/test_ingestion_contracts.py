from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
from me_system.errors import ContractValidationError, IngestionStateError
from me_system.evidence.contracts import EvidenceFragment, SourceRecord
from me_system.ingestion.contracts import (
    ActorKind,
    CandidateGraphChangeRecord,
    CandidateReviewEvent,
    IngestionRun,
    IngestionStatus,
    ReviewEventType,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64


def source(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "source_id": "source:conversation:001",
        "source_type": "agent_conversation",
        "external_system": "hermes",
        "external_id": "conversation-001",
        "idempotency_key": "hermes:conversation-001:v1",
        "content_ref": "file:///data/conversation-001.json",
        "content_sha256": SHA_A,
        "media_type": "application/json",
        "occurred_at": NOW,
        "ingested_at": NOW + timedelta(minutes=1),
        "sensitivity": Sensitivity.PERSONAL_PRIVATE,
        "metadata": {"title": "Project conversation", "count": 2},
    }
    values.update(overrides)
    return SourceRecord(**values)


def fragment(**overrides: object) -> EvidenceFragment:
    values: dict[str, object] = {
        "fragment_id": "fragment:conversation:001:0001",
        "source_id": "source:conversation:001",
        "ordinal": 1,
        "fragment_type": "conversation_message",
        "text_content": "Radiance is the primary engine.",
        "source_anchor": {
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": "msg-1"},
        },
        "content_sha256": SHA_B,
        "occurred_at": NOW,
        "actor_id": "who:user:master",
        "metadata": {"role": "user"},
    }
    values.update(overrides)
    return EvidenceFragment(**values)


def candidate_change() -> CandidateGraphChange:
    ref = EvidenceRef(
        source_id="source:conversation:001",
        document_id="doc:conversation:001",
        version_id="docv:conversation:001:1",
        content_fragment_id="fragment:conversation:001:0001",
        source_anchor={
            "type": "conversation_message",
            "value": {"message_id": "msg-1"},
        },
    )
    payload = {
        "id": "brain:decision:radiance-primary",
        "graph": "me_brain",
        "type": "Decision",
        "label": "Radiance is the primary engine",
        "properties": {"value": "Radiance"},
        "authority": AuthorityLevel.CANDIDATE.value,
        "confirmation_status": ConfirmationStatus.PENDING.value,
        "status": TemporalStatus.CURRENT.value,
        "valid_from": NOW.isoformat(),
        "valid_to": None,
        "sensitivity": Sensitivity.PROJECT_PRIVATE.value,
        "source_refs": [ref.to_dict()],
    }
    return CandidateGraphChange(
        change_id="candidate:decision:radiance-primary",
        target_graph=GraphNamespace.ME_BRAIN,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:conversation:0.1.0",
        reason="Explicit project decision",
        evidence_refs=(ref,),
        payload=payload,
    )


def run(**overrides: object) -> IngestionRun:
    values: dict[str, object] = {
        "run_id": "run:conversation:001",
        "source_id": "source:conversation:001",
        "adapter_name": "agent-conversation",
        "adapter_version": "0.1.0",
        "status": IngestionStatus.PENDING,
        "started_at": NOW,
        "completed_at": None,
        "input_item_count": 2,
        "processed_item_count": 0,
        "skipped_item_count": 0,
        "failed_item_count": 0,
        "fragment_count": 0,
        "candidate_count": 0,
        "coverage_ratio": 0.0,
        "quality_report": {},
        "log_ref": None,
        "error_summary": None,
    }
    values.update(overrides)
    return IngestionRun(**values)


def test_source_round_trip_and_fingerprint_ignore_record_identity() -> None:
    value = source()
    assert SourceRecord.from_dict(value.to_dict()) == value
    same_snapshot = source(
        source_id="source:conversation:retry",
        ingested_at=NOW + timedelta(hours=1),
    )
    assert same_snapshot.fingerprint() == value.fingerprint()


def test_source_rejects_invalid_hash_and_naive_time() -> None:
    with pytest.raises(ContractValidationError, match="SHA-256"):
        source(content_sha256="not-a-hash")
    with pytest.raises(ContractValidationError, match="timezone"):
        source(occurred_at=datetime(2026, 7, 23, 10, 0))


def test_source_metadata_is_copied_and_fingerprint_is_stable() -> None:
    metadata = {"nested": {"value": 1}}
    value = source(metadata=metadata)
    metadata["nested"] = {"value": 2}
    assert value.metadata == {"nested": {"value": 1}}
    assert len(value.fingerprint()) == 64


def test_evidence_fragment_round_trip_and_anchor_validation() -> None:
    value = fragment()
    assert EvidenceFragment.from_dict(value.to_dict()) == value
    assert value.source_anchor["value"]["message_id"] == "msg-1"
    with pytest.raises(ContractValidationError, match="source_anchor.value"):
        fragment(source_anchor={"type": "message", "value": "msg-1"})


def test_evidence_fragment_rejects_negative_ordinal() -> None:
    with pytest.raises(ContractValidationError, match="ordinal"):
        fragment(ordinal=-1)


def test_ingestion_run_validates_counts_and_terminal_timestamp() -> None:
    with pytest.raises(ContractValidationError, match="counts"):
        run(processed_item_count=2, skipped_item_count=1)
    with pytest.raises(ContractValidationError, match="completed_at"):
        run(status=IngestionStatus.COMPLETED)
    with pytest.raises(ContractValidationError, match="coverage_ratio"):
        run(coverage_ratio=1.1)


def test_ingestion_run_supports_legal_state_transitions() -> None:
    running = run().start()
    assert running.status is IngestionStatus.RUNNING
    completed = running.finish(
        status=IngestionStatus.COMPLETED,
        completed_at=NOW + timedelta(minutes=2),
        input_item_count=2,
        processed_item_count=2,
        skipped_item_count=0,
        failed_item_count=0,
        fragment_count=2,
        candidate_count=1,
        coverage_ratio=1.0,
        quality_report={"complete": True},
    )
    assert completed.status is IngestionStatus.COMPLETED
    assert IngestionRun.from_dict(completed.to_dict()) == completed


def test_ingestion_run_rejects_terminal_restart_and_invalid_finish() -> None:
    with pytest.raises(IngestionStateError):
        run(status=IngestionStatus.RUNNING).start()
    with pytest.raises(IngestionStateError):
        run().finish(
            status=IngestionStatus.COMPLETED,
            completed_at=NOW + timedelta(minutes=1),
            input_item_count=2,
            processed_item_count=2,
            skipped_item_count=0,
            failed_item_count=0,
            fragment_count=2,
            candidate_count=1,
            coverage_ratio=1.0,
            quality_report={},
        )


def test_candidate_record_has_stable_payload_and_submission_hashes() -> None:
    change = candidate_change()
    record = CandidateGraphChangeRecord.from_change(
        change,
        idempotency_key="agent-conversation:source-001:radiance-primary",
        created_at=NOW,
        ingestion_run_id="run:conversation:001",
    )
    round_trip = CandidateGraphChangeRecord.from_dict(record.to_dict())
    assert round_trip == record
    assert len(record.payload_sha256) == 64
    assert len(record.submission_fingerprint()) == 64


def test_candidate_record_rejects_incorrect_payload_hash() -> None:
    record = CandidateGraphChangeRecord.from_change(
        candidate_change(),
        idempotency_key="candidate:key",
        created_at=NOW,
    )
    payload = record.to_dict()
    payload["payload_sha256"] = SHA_B
    with pytest.raises(ContractValidationError, match="payload_sha256"):
        CandidateGraphChangeRecord.from_dict(payload)


def test_pending_candidate_cannot_contain_review_metadata() -> None:
    with pytest.raises(ContractValidationError, match="pending"):
        CandidateGraphChangeRecord.from_change(
            candidate_change(),
            idempotency_key="candidate:key",
            created_at=NOW,
            reviewed_at=NOW,
        )


def test_review_event_round_trip_and_validation() -> None:
    event = CandidateReviewEvent(
        event_id="review-event:001",
        change_id="candidate:decision:radiance-primary",
        event_type=ReviewEventType.SUBMITTED,
        actor_id="adapter:conversation:0.1.0",
        actor_kind=ActorKind.ADAPTER,
        reason="Candidate submitted",
        created_at=NOW,
        metadata={"source_id": "source:conversation:001"},
    )
    assert CandidateReviewEvent.from_dict(event.to_dict()) == event
    with pytest.raises(ContractValidationError, match="timezone"):
        CandidateReviewEvent(
            event_id="review-event:bad",
            change_id="candidate:bad",
            event_type=ReviewEventType.REJECTED,
            actor_id="user",
            actor_kind=ActorKind.HUMAN,
            reason="bad",
            created_at=datetime(2026, 7, 23),
            metadata={},
        )
