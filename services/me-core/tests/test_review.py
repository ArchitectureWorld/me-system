from __future__ import annotations

import pytest

from me_core.contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    EvidenceRef,
    GraphNamespace,
    GraphNode,
    ReviewStatus,
    Sensitivity,
    TemporalStatus,
)
from me_core.errors import CandidateReviewError, GraphObjectNotFoundError
from me_core.review import CandidateReviewService
from me_core.store import InMemoryGraphStore


def evidence(source_id: str) -> EvidenceRef:
    return EvidenceRef(source_id=source_id, source_anchor={"type": "fixture", "value": {"id": source_id}})


def candidate_node() -> GraphNode:
    return GraphNode(
        id="brain:decision:new-route",
        graph=GraphNamespace.ME_BRAIN,
        type="Decision",
        label="采用新的主路线",
        properties={},
        authority=AuthorityLevel.CANDIDATE,
        confirmation_status=ConfirmationStatus.PENDING,
        status=TemporalStatus.CURRENT,
        valid_from=None,
        valid_to=None,
        sensitivity=Sensitivity.PROJECT_PRIVATE,
        source_refs=(evidence("src:payload"),),
    )


def change() -> CandidateGraphChange:
    return CandidateGraphChange(
        change_id="change:new-route",
        target_graph=GraphNamespace.ME_BRAIN,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="hermes-primary",
        reason="用户明确提出新路线",
        evidence_refs=(evidence("src:submission"),),
        payload=candidate_node().to_dict(),
        review_status=ReviewStatus.PENDING,
    )


def test_submit_keeps_candidate_out_of_canonical_store() -> None:
    store = InMemoryGraphStore()
    review = CandidateReviewService(store)
    review.submit(change())
    with pytest.raises(GraphObjectNotFoundError):
        store.get_node("brain:decision:new-route")
    assert review.list_pending()[0].change_id == "change:new-route"


def test_approve_promotes_candidate_and_preserves_all_evidence() -> None:
    store = InMemoryGraphStore()
    review = CandidateReviewService(store)
    review.submit(change())
    review.approve("change:new-route", reviewer_id="user:master")
    node = store.get_node("brain:decision:new-route")
    assert node.authority is AuthorityLevel.HUMAN_CONFIRMED
    assert node.confirmation_status is ConfirmationStatus.HUMAN_CONFIRMED
    assert {ref.source_id for ref in node.source_refs} == {"src:payload", "src:submission"}
    assert review.get_change("change:new-route").review_status is ReviewStatus.APPROVED


def test_reject_does_not_modify_canonical_store() -> None:
    store = InMemoryGraphStore()
    review = CandidateReviewService(store)
    review.submit(change())
    review.reject("change:new-route", reviewer_id="user:master", reason="不是正式决策")
    with pytest.raises(GraphObjectNotFoundError):
        store.get_node("brain:decision:new-route")
    rejected = review.get_change("change:new-route")
    assert rejected.review_status is ReviewStatus.REJECTED
    assert rejected.review_reason == "不是正式决策"


def test_candidate_cannot_be_reviewed_twice() -> None:
    store = InMemoryGraphStore()
    review = CandidateReviewService(store)
    review.submit(change())
    review.reject("change:new-route", reviewer_id="user:master", reason="not confirmed")
    with pytest.raises(CandidateReviewError, match="pending"):
        review.approve("change:new-route", reviewer_id="user:master")
