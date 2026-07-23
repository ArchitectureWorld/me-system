from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from me_system.contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    EvidenceRef,
    GraphNamespace,
    Sensitivity,
    TemporalStatus,
)
from me_system.errors import CandidateConflictError, CandidateNotFoundError
from me_system.evidence.contracts import EvidenceFragment, FragmentType, SourceRecord
from me_system.ingestion.contracts import CandidateRecord, candidate_payload_sha256
from me_system.persistence.candidate_repository import SqlAlchemyCandidateRepository
from me_system.persistence.models import create_schema
from me_system.persistence.source_repository import SqlAlchemySourceRepository
from me_system.persistence.testing import create_sqlite_test_engine


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def evidence() -> EvidenceRef:
    return EvidenceRef(
        source_id="source:conversation:001",
        content_fragment_id="fragment:conversation:001:42",
        source_anchor={
            "type": "conversation_message",
            "value": {"message_id": "msg-42"},
        },
    )


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
        occurred_at=NOW,
        ingested_at=NOW,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
        metadata={},
    )


def fragment() -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id="fragment:conversation:001:42",
        source_id=source().source_id,
        ordinal=42,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content="第一阶段只考虑人工照明。",
        source_anchor=evidence().source_anchor,
        content_sha256="b" * 64,
        occurred_at=NOW,
        actor_id="who:user:master",
        metadata={},
    )


def candidate(
    *,
    change_id: str = "candidate:constraint:artificial-light",
    idempotency_key: str = "conversation:001:0.1.0:constraint:artificial-light",
    target_graph: GraphNamespace = GraphNamespace.ME_BRAIN,
    object_id: str = "brain:constraint:artificial-light-only-v2",
    label: str = "第一阶段只考虑人工照明",
) -> CandidateRecord:
    payload = {
        "schema_version": "graph-node/0.1",
        "id": object_id,
        "graph": target_graph.value,
        "type": "Constraint" if target_graph is GraphNamespace.ME_BRAIN else "CollaborationRule",
        "label": label,
        "properties": {},
        "authority": AuthorityLevel.CANDIDATE.value,
        "confirmation_status": ConfirmationStatus.PENDING.value,
        "status": TemporalStatus.CURRENT.value,
        "valid_from": "2026-07-23T10:30:00Z",
        "valid_to": None,
        "sensitivity": (
            Sensitivity.PROJECT_PRIVATE.value
            if target_graph is GraphNamespace.ME_BRAIN
            else Sensitivity.PERSONAL_PRIVATE.value
        ),
        "source_refs": [evidence().to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=target_graph,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:agent-conversation:0.1.0",
        reason="explicit statement",
        evidence_refs=(evidence(),),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=idempotency_key,
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=None,
    )


def repositories(url: str = "sqlite+pysqlite:///:memory:"):
    engine = create_sqlite_test_engine(url)
    create_schema(engine)
    sources = SqlAlchemySourceRepository(engine)
    sources.register(source())
    sources.add_fragments(source().source_id, (fragment(),))
    return engine, sources, SqlAlchemyCandidateRepository(engine)


def test_submit_get_and_submitted_event() -> None:
    _, _, repository = repositories()
    value = candidate()
    assert repository.submit(value) == value
    assert repository.get(value.change.change_id) == value
    events = repository.list_events(value.change.change_id)
    assert [event.event_type.value for event in events] == ["submitted"]
    assert events[0].actor_kind.value == "adapter"


def test_identical_retry_returns_existing_candidate_without_duplicate_event() -> None:
    _, _, repository = repositories()
    first = candidate()
    retry = candidate(change_id="candidate:retry")
    assert repository.submit(first) == first
    assert repository.submit(retry) == first
    assert len(repository.list_events(first.change.change_id)) == 1


def test_candidate_retry_with_changed_payload_is_rejected() -> None:
    _, _, repository = repositories()
    repository.submit(candidate())
    changed = candidate(change_id="candidate:retry", label="已改变的约束")
    with pytest.raises(CandidateConflictError):
        repository.submit(changed)


def test_missing_candidate_is_explicit() -> None:
    _, _, repository = repositories()
    with pytest.raises(CandidateNotFoundError):
        repository.get("candidate:missing")


def test_list_pending_filters_graph_and_source() -> None:
    _, _, repository = repositories()
    brain = candidate()
    who = candidate(
        change_id="candidate:who:direct-execution",
        idempotency_key="conversation:001:0.1.0:who:direct-execution",
        target_graph=GraphNamespace.ME_WHO,
        object_id="who:collaboration-rule:direct-execution-v2",
        label="明确任务直接执行",
    )
    repository.submit(brain)
    repository.submit(who)
    assert repository.list_pending(target_graph=GraphNamespace.ME_BRAIN) == (brain,)
    assert repository.list_pending(target_graph=GraphNamespace.ME_WHO) == (who,)
    assert repository.list_pending(source_id=source().source_id) == (brain, who)


def test_pending_limit_is_validated() -> None:
    _, _, repository = repositories()
    with pytest.raises(ValueError, match="limit"):
        repository.list_pending(limit=0)
    with pytest.raises(ValueError, match="limit"):
        repository.list_pending(limit=1001)


def test_candidate_survives_repository_recreation(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'me-system.db'}"
    engine1, _, repository1 = repositories(url)
    value = candidate()
    repository1.submit(value)
    engine1.dispose()

    engine2 = create_sqlite_test_engine(url)
    repository2 = SqlAlchemyCandidateRepository(engine2)
    assert repository2.get(value.change.change_id) == value
    assert len(repository2.list_events(value.change.change_id)) == 1
