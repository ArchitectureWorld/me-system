from __future__ import annotations

from datetime import datetime, timezone

import pytest

from me_system.contracts import Sensitivity
from me_system.errors import ContractValidationError
from me_system.evidence.contracts import EvidenceFragment, FragmentType, SourceRecord


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64


def source(**overrides: object) -> SourceRecord:
    payload: dict[str, object] = {
        "source_id": "source:conversation:001",
        "source_type": "agent_conversation",
        "external_system": "hermes",
        "external_id": "conversation-001",
        "idempotency_key": "hermes:conversation-001:export-1",
        "content_ref": "file:///data/conversation-001.json",
        "content_sha256": HASH_A,
        "media_type": "application/json",
        "occurred_at": "2026-07-23T10:00:00Z",
        "ingested_at": NOW,
        "sensitivity": "personal_private",
        "metadata": {"title": "照明平台讨论", "participants": ["master", "hermes"]},
    }
    payload.update(overrides)
    return SourceRecord.from_dict(payload)


def fragment(**overrides: object) -> EvidenceFragment:
    payload: dict[str, object] = {
        "fragment_id": "fragment:conversation:001:42",
        "source_id": "source:conversation:001",
        "ordinal": 42,
        "fragment_type": "conversation_message",
        "text_content": "第一阶段只考虑人工照明。",
        "source_anchor": {
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": "msg-42"},
        },
        "content_sha256": HASH_B,
        "occurred_at": "2026-07-23T10:30:00Z",
        "actor_id": "who:user:master",
        "metadata": {"role": "user"},
    }
    payload.update(overrides)
    return EvidenceFragment.from_dict(payload)


def test_source_record_normalizes_enums_time_and_mapping() -> None:
    value = source()
    assert value.sensitivity is Sensitivity.PERSONAL_PRIVATE
    assert value.occurred_at == datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)
    assert value.to_dict() == {
        "schema_version": "source-record/0.1",
        "source_id": "source:conversation:001",
        "source_type": "agent_conversation",
        "external_system": "hermes",
        "external_id": "conversation-001",
        "idempotency_key": "hermes:conversation-001:export-1",
        "content_ref": "file:///data/conversation-001.json",
        "content_sha256": HASH_A,
        "media_type": "application/json",
        "occurred_at": "2026-07-23T10:00:00Z",
        "ingested_at": "2026-07-23T12:00:00Z",
        "sensitivity": "personal_private",
        "metadata": {"title": "照明平台讨论", "participants": ["master", "hermes"]},
    }


def test_source_identity_payload_excludes_ingestion_time_and_source_id() -> None:
    first = source()
    retry = source(
        source_id="source:conversation:retry",
        ingested_at="2026-07-24T12:00:00Z",
    )
    assert first.identity_payload() == retry.identity_payload()


@pytest.mark.parametrize("content_hash", ["", "abc", "G" * 64, "a" * 63])
def test_source_rejects_invalid_sha256(content_hash: str) -> None:
    with pytest.raises(ContractValidationError, match="content_sha256"):
        source(content_sha256=content_hash)


def test_source_requires_timezone_aware_ingested_at() -> None:
    with pytest.raises(ContractValidationError, match="timezone"):
        source(ingested_at="2026-07-23T12:00:00")


def test_fragment_normalizes_anchor_and_type() -> None:
    value = fragment()
    assert value.fragment_type is FragmentType.CONVERSATION_MESSAGE
    assert value.source_anchor["value"]["message_id"] == "msg-42"
    assert value.to_evidence_ref().to_dict() == {
        "source_id": "source:conversation:001",
        "document_id": None,
        "version_id": None,
        "content_fragment_id": "fragment:conversation:001:42",
        "source_anchor": {
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": "msg-42"},
        },
    }


def test_fragment_rejects_negative_ordinal() -> None:
    with pytest.raises(ContractValidationError, match="ordinal"):
        fragment(ordinal=-1)


def test_fragment_requires_structured_anchor_value() -> None:
    with pytest.raises(ContractValidationError, match="source_anchor.value"):
        fragment(source_anchor={"type": "conversation_message", "value": "msg-42"})


def test_fragment_type_is_closed_for_v01() -> None:
    with pytest.raises(ContractValidationError, match="fragment_type"):
        fragment(fragment_type="image_region")
