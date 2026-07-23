from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ..contracts import EvidenceRef, GraphEdge, GraphNode, ReviewStatus
from ..errors import (
    CandidateNotFoundError,
    CandidateStateError,
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
    ReviewTransactionError,
)
from ..persistence.candidate_repository import _event_row, _to_candidate
from ..persistence.graph_writer import write_graph_edge, write_graph_node
from ..persistence.models import CandidateGraphChangeRow
from .contracts import ActorKind, ReviewEvent, ReviewEventType


def _required_text(value: object, name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise CandidateStateError(f"{name} must not be empty")
    return text


def _merge_evidence(*groups: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
    unique: dict[str, EvidenceRef] = {}
    for group in groups:
        for ref in group:
            key = json.dumps(
                ref.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            unique[key] = ref
    return tuple(unique[key] for key in sorted(unique))


def _review_time(created_at: datetime) -> datetime:
    """Return a review time strictly after submission despite clock skew."""

    created = created_at.astimezone(timezone.utc)
    return max(datetime.now(timezone.utc), created + timedelta(microseconds=1))


class PersistentReviewService:
    """Atomically review a persistent candidate and update the canonical graph."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def approve(
        self,
        change_id: str,
        reviewer_id: str,
        *,
        reviewer_kind: str = "human",
        reason: str = "approved",
    ) -> GraphNode | GraphEdge:
        reviewer_id = _required_text(reviewer_id, "reviewer_id")
        reason = _required_text(reason, "reason")
        if reviewer_kind not in {ActorKind.HUMAN.value, ActorKind.RULE.value}:
            raise CandidateStateError(
                "reviewer_kind must be human or rule for canonical approval"
            )
        try:
            with self._sessions.begin() as session:
                row = session.scalar(
                    select(CandidateGraphChangeRow)
                    .where(CandidateGraphChangeRow.change_id == change_id)
                    .with_for_update()
                )
                if row is None:
                    raise CandidateNotFoundError(f"candidate not found: {change_id}")
                candidate = _to_candidate(session, row)
                if candidate.change.review_status is not ReviewStatus.PENDING:
                    raise CandidateStateError("candidate is no longer pending")
                reviewed_at = _review_time(candidate.created_at)
                materialized = candidate.change.materialize()
                merged_refs = _merge_evidence(
                    materialized.source_refs,
                    candidate.change.evidence_refs,
                )
                confirmed = replace(
                    materialized,
                    source_refs=merged_refs,
                ).as_confirmed(reviewer_kind=reviewer_kind)
                if isinstance(confirmed, GraphNode):
                    write_graph_node(session, confirmed)
                else:
                    write_graph_edge(session, confirmed)
                row.review_status = ReviewStatus.APPROVED.value
                row.reviewed_at = reviewed_at
                row.reviewed_by = reviewer_id
                row.review_reason = reason
                row.approved_object_id = confirmed.id
                session.add(
                    _event_row(
                        ReviewEvent(
                            event_id=f"review-event:{change_id}:approved",
                            change_id=change_id,
                            event_type=ReviewEventType.APPROVED,
                            actor_id=reviewer_id,
                            actor_kind=ActorKind(reviewer_kind),
                            reason=reason,
                            created_at=reviewed_at,
                            metadata={"approved_object_id": confirmed.id},
                        )
                    )
                )
                session.flush()
                return confirmed
        except (
            CandidateNotFoundError,
            CandidateStateError,
            DuplicateGraphObjectError,
            GraphObjectNotFoundError,
            GraphNamespaceError,
        ):
            raise
        except IntegrityError as exc:
            raise ReviewTransactionError(
                "candidate approval could not commit atomically"
            ) from exc
        except SQLAlchemyError as exc:
            raise ReviewTransactionError(
                "candidate approval could not complete"
            ) from exc

    def reject(
        self,
        change_id: str,
        reviewer_id: str,
        reason: str,
        *,
        reviewer_kind: str = "human",
    ) -> None:
        reviewer_id = _required_text(reviewer_id, "reviewer_id")
        reason = _required_text(reason, "reason")
        try:
            actor_kind = ActorKind(reviewer_kind)
        except ValueError as exc:
            raise CandidateStateError(
                "reviewer_kind must be adapter, agent, human, or rule"
            ) from exc
        try:
            with self._sessions.begin() as session:
                row = session.scalar(
                    select(CandidateGraphChangeRow)
                    .where(CandidateGraphChangeRow.change_id == change_id)
                    .with_for_update()
                )
                if row is None:
                    raise CandidateNotFoundError(f"candidate not found: {change_id}")
                candidate = _to_candidate(session, row)
                if candidate.change.review_status is not ReviewStatus.PENDING:
                    raise CandidateStateError("candidate is no longer pending")
                reviewed_at = _review_time(candidate.created_at)
                row.review_status = ReviewStatus.REJECTED.value
                row.reviewed_at = reviewed_at
                row.reviewed_by = reviewer_id
                row.review_reason = reason
                row.approved_object_id = None
                session.add(
                    _event_row(
                        ReviewEvent(
                            event_id=f"review-event:{change_id}:rejected",
                            change_id=change_id,
                            event_type=ReviewEventType.REJECTED,
                            actor_id=reviewer_id,
                            actor_kind=actor_kind,
                            reason=reason,
                            created_at=reviewed_at,
                            metadata={},
                        )
                    )
                )
                session.flush()
        except (CandidateNotFoundError, CandidateStateError):
            raise
        except IntegrityError as exc:
            raise ReviewTransactionError(
                "candidate rejection could not commit atomically"
            ) from exc
        except SQLAlchemyError as exc:
            raise ReviewTransactionError(
                "candidate rejection could not complete"
            ) from exc
