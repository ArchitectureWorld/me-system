from __future__ import annotations

from dataclasses import replace
import json

from .contracts import (
    CandidateGraphChange,
    EvidenceRef,
    GraphEdge,
    GraphNode,
    ReviewStatus,
)
from .errors import CandidateReviewError, DuplicateGraphObjectError, GraphObjectNotFoundError
from .store import GraphStore


def _merge_evidence(*groups: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
    unique: dict[str, EvidenceRef] = {}
    for group in groups:
        for ref in group:
            key = json.dumps(ref.to_dict(), ensure_ascii=False, sort_keys=True)
            unique[key] = ref
    return tuple(unique[key] for key in sorted(unique))


class CandidateReviewService:
    def __init__(self, store: GraphStore) -> None:
        self._store = store
        self._changes: dict[str, CandidateGraphChange] = {}

    def submit(self, change: CandidateGraphChange) -> CandidateGraphChange:
        if change.change_id in self._changes:
            raise DuplicateGraphObjectError(f"candidate change already exists: {change.change_id}")
        if change.review_status is not ReviewStatus.PENDING:
            raise CandidateReviewError("only pending candidate changes can be submitted")
        self._changes[change.change_id] = change
        return change

    def get_change(self, change_id: str) -> CandidateGraphChange:
        try:
            return self._changes[change_id]
        except KeyError as exc:
            raise GraphObjectNotFoundError(f"candidate change not found: {change_id}") from exc

    def list_pending(self) -> tuple[CandidateGraphChange, ...]:
        return tuple(
            sorted(
                (change for change in self._changes.values() if change.review_status is ReviewStatus.PENDING),
                key=lambda change: change.change_id,
            )
        )

    def approve(self, change_id: str, reviewer_id: str, *, reviewer_kind: str = "human") -> None:
        change = self._require_pending(change_id)
        materialized = change.materialize()
        merged_refs = _merge_evidence(materialized.source_refs, change.evidence_refs)
        if isinstance(materialized, GraphNode):
            confirmed = replace(materialized, source_refs=merged_refs).as_confirmed(reviewer_kind=reviewer_kind)
            self._store.add_node(confirmed)
        elif isinstance(materialized, GraphEdge):
            confirmed = replace(materialized, source_refs=merged_refs).as_confirmed(reviewer_kind=reviewer_kind)
            self._store.add_edge(confirmed)
        else:
            raise CandidateReviewError(f"unsupported candidate operation: {change.operation}")
        self._changes[change_id] = replace(
            change,
            review_status=ReviewStatus.APPROVED,
            reviewed_by=reviewer_id,
            review_reason="approved",
        )

    def reject(self, change_id: str, reviewer_id: str, reason: str) -> None:
        change = self._require_pending(change_id)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise CandidateReviewError("rejection reason must not be empty")
        self._changes[change_id] = replace(
            change,
            review_status=ReviewStatus.REJECTED,
            reviewed_by=reviewer_id,
            review_reason=normalized_reason,
        )

    def _require_pending(self, change_id: str) -> CandidateGraphChange:
        change = self.get_change(change_id)
        if change.review_status is not ReviewStatus.PENDING:
            raise CandidateReviewError("candidate change is no longer pending")
        return change
