from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from me_system.contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    EvidenceRef,
    GraphEdge,
    GraphNamespace,
    GraphNode,
    ReviewStatus,
    Sensitivity,
    TemporalStatus,
)
from me_system.errors import (
    CandidateStateError,
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
    ReviewTransactionError,
)
from me_system.evidence.contracts import EvidenceFragment, FragmentType, SourceRecord
from me_system.ingestion.contracts import CandidateRecord, candidate_payload_sha256
from me_system.ingestion.review import PersistentReviewService
from me_system.persistence.candidate_repository import SqlAlchemyCandidateRepository
from me_system.persistence.models import CandidateReviewEventRow, create_schema
from me_system.persistence.source_repository import SqlAlchemySourceRepository
from me_system.persistence.store import SqlAlchemyGraphStore
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
        source_id=evidence().source_id,
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
        fragment_id=evidence().content_fragment_id or "",
        source_id=evidence().source_id,
        ordinal=42,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content="第一阶段只考虑人工照明。",
        source_anchor=evidence().source_anchor,
        content_sha256="b" * 64,
        occurred_at=NOW,
        actor_id="who:user:master",
        metadata={},
    )


def canonical_node(node_id: str, graph: GraphNamespace) -> GraphNode:
    return GraphNode(
        id=node_id,
        graph=graph,
        type="Project" if graph is GraphNamespace.ME_BRAIN else "User",
        label=node_id,
        properties={},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        status=TemporalStatus.CURRENT,
        valid_from=NOW,
        valid_to=None,
        sensitivity=(
            Sensitivity.PROJECT_PRIVATE
            if graph is GraphNamespace.ME_BRAIN
            else Sensitivity.PERSONAL_PRIVATE
        ),
        source_refs=(evidence(),),
    )


def node_candidate(
    *,
    change_id: str = "candidate:constraint:artificial-light",
    object_id: str = "brain:constraint:artificial-light-v2",
    target_graph: GraphNamespace = GraphNamespace.ME_BRAIN,
) -> CandidateRecord:
    payload = {
        "schema_version": "graph-node/0.1",
        "id": object_id,
        "graph": target_graph.value,
        "type": "Constraint" if target_graph is GraphNamespace.ME_BRAIN else "CollaborationRule",
        "label": "第一阶段只考虑人工照明",
        "properties": {},
        "authority": "candidate",
        "confirmation_status": "pending",
        "status": "current",
        "valid_from": "2026-07-23T10:30:00Z",
        "valid_to": None,
        "sensitivity": (
            "project_private"
            if target_graph is GraphNamespace.ME_BRAIN
            else "personal_private"
        ),
        "source_refs": [evidence().to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=target_graph,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:conversation:0.1.0",
        reason="explicit statement",
        evidence_refs=(evidence(),),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=f"idempotency:{change_id}",
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=None,
    )


def edge_candidate(
    *,
    change_id: str,
    edge_id: str,
    graph: GraphNamespace,
    from_id: str,
    to_id: str,
) -> CandidateRecord:
    payload = {
        "schema_version": "graph-edge/0.1",
        "id": edge_id,
        "graph": graph.value,
        "type": "RELATED_TO",
        "from_id": from_id,
        "to_id": to_id,
        "properties": {},
        "authority": "candidate",
        "confirmation_status": "pending",
        "confidence": 1,
        "valid_from": "2026-07-23T10:30:00Z",
        "valid_to": None,
        "sensitivity": "restricted" if graph is GraphNamespace.BRIDGE else "project_private",
        "source_refs": [evidence().to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=graph,
        operation=ChangeOperation.ADD_EDGE,
        submitted_by="adapter:conversation:0.1.0",
        reason="explicit relation",
        evidence_refs=(evidence(),),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=f"idempotency:{change_id}",
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=None,
    )


def system():
    engine = create_sqlite_test_engine()
    create_schema(engine)
    sources = SqlAlchemySourceRepository(engine)
    sources.register(source())
    sources.add_fragments(source().source_id, (fragment(),))
    candidates = SqlAlchemyCandidateRepository(engine)
    graph = SqlAlchemyGraphStore(engine)
    review = PersistentReviewService(engine)
    return engine, sources, candidates, graph, review


def test_approve_node_updates_candidate_graph_and_event_atomically() -> None:
    _, _, candidates, graph, review = system()
    value = node_candidate()
    candidates.submit(value)
    approved = review.approve(value.change.change_id, "who:user:master")
    assert isinstance(approved, GraphNode)
    assert approved.authority is AuthorityLevel.HUMAN_CONFIRMED
    assert graph.get_node(approved.id) == approved
    persisted = candidates.get(value.change.change_id)
    assert persisted.change.review_status is ReviewStatus.APPROVED
    assert persisted.approved_object_id == approved.id
    assert [event.event_type.value for event in candidates.list_events(value.change.change_id)] == [
        "submitted",
        "approved",
    ]


def test_approve_edge_uses_same_graph_namespace_rules() -> None:
    _, _, candidates, graph, review = system()
    first = canonical_node("brain:project:first", GraphNamespace.ME_BRAIN)
    second = canonical_node("brain:project:second", GraphNamespace.ME_BRAIN)
    graph.add_node(first)
    graph.add_node(second)
    value = edge_candidate(
        change_id="candidate:edge:related",
        edge_id="edge:first-related-second",
        graph=GraphNamespace.ME_BRAIN,
        from_id=first.id,
        to_id=second.id,
    )
    candidates.submit(value)
    approved = review.approve(
        value.change.change_id,
        "rule:deterministic-link",
        reviewer_kind="rule",
    )
    assert isinstance(approved, GraphEdge)
    assert approved.authority is AuthorityLevel.RULE_CONFIRMED
    assert graph.get_edge(approved.id) == approved


def test_reject_preserves_history_without_writing_graph() -> None:
    _, _, candidates, graph, review = system()
    value = node_candidate()
    candidates.submit(value)
    review.reject(value.change.change_id, "who:user:master", "not a stable project fact")
    persisted = candidates.get(value.change.change_id)
    assert persisted.change.review_status is ReviewStatus.REJECTED
    with pytest.raises(GraphObjectNotFoundError):
        graph.get_node(value.change.materialize().id)
    assert [event.event_type.value for event in candidates.list_events(value.change.change_id)] == [
        "submitted",
        "rejected",
    ]


def test_candidate_cannot_be_reviewed_twice() -> None:
    _, _, candidates, _, review = system()
    value = node_candidate()
    candidates.submit(value)
    review.reject(value.change.change_id, "who:user:master", "reject")
    with pytest.raises(CandidateStateError):
        review.approve(value.change.change_id, "who:user:master")


def test_duplicate_graph_id_rolls_back_candidate_and_event() -> None:
    _, _, candidates, graph, review = system()
    value = node_candidate()
    graph.add_node(
        canonical_node(value.change.materialize().id, GraphNamespace.ME_BRAIN)
    )
    candidates.submit(value)
    with pytest.raises(DuplicateGraphObjectError):
        review.approve(value.change.change_id, "who:user:master")
    assert candidates.get(value.change.change_id).change.review_status is ReviewStatus.PENDING
    assert [event.event_type.value for event in candidates.list_events(value.change.change_id)] == [
        "submitted"
    ]


def test_missing_edge_endpoint_rolls_back() -> None:
    _, _, candidates, graph, review = system()
    first = canonical_node("brain:project:first", GraphNamespace.ME_BRAIN)
    graph.add_node(first)
    value = edge_candidate(
        change_id="candidate:edge:missing",
        edge_id="edge:first-missing",
        graph=GraphNamespace.ME_BRAIN,
        from_id=first.id,
        to_id="brain:project:missing",
    )
    candidates.submit(value)
    with pytest.raises(GraphObjectNotFoundError):
        review.approve(value.change.change_id, "who:user:master")
    assert candidates.get(value.change.change_id).change.review_status is ReviewStatus.PENDING


def test_illegal_cross_graph_edge_rolls_back() -> None:
    _, _, candidates, graph, review = system()
    brain = canonical_node("brain:project:first", GraphNamespace.ME_BRAIN)
    who = canonical_node("who:user:master", GraphNamespace.ME_WHO)
    graph.add_node(brain)
    graph.add_node(who)
    value = edge_candidate(
        change_id="candidate:edge:cross",
        edge_id="edge:illegal-cross",
        graph=GraphNamespace.ME_BRAIN,
        from_id=brain.id,
        to_id=who.id,
    )
    candidates.submit(value)
    with pytest.raises(GraphNamespaceError):
        review.approve(value.change.change_id, "who:user:master")
    assert candidates.get(value.change.change_id).change.review_status is ReviewStatus.PENDING


def test_review_event_failure_rolls_back_graph_and_candidate() -> None:
    engine, _, candidates, graph, review = system()
    value = node_candidate()
    candidates.submit(value)
    with Session(engine) as session, session.begin():
        session.add(
            CandidateReviewEventRow(
                event_id=f"review-event:{value.change.change_id}:approved",
                change_id=value.change.change_id,
                event_type="approved",
                actor_id="test",
                actor_kind="human",
                reason="reserved event id",
                created_at=NOW,
                metadata_json={},
            )
        )
    with pytest.raises(ReviewTransactionError):
        review.approve(value.change.change_id, "who:user:master")
    assert candidates.get(value.change.change_id).change.review_status is ReviewStatus.PENDING
    with pytest.raises(GraphObjectNotFoundError):
        graph.get_node(value.change.materialize().id)
