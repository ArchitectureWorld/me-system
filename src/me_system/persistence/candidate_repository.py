from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..contracts import CandidateGraphChange, EvidenceRef, GraphNamespace, ReviewStatus
from ..errors import (
    CandidateConflictError,
    CandidateNotFoundError,
    GraphStoreUnavailableError,
)
from ..ingestion.contracts import (
    ActorKind,
    CandidateRecord,
    ReviewEvent,
    ReviewEventType,
)
from .models import (
    CandidateEvidenceRefRow,
    CandidateGraphChangeRow,
    CandidateReviewEventRow,
    EvidenceFragmentRow,
    IngestionRunRow,
    SourceRecordRow,
)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _candidate_row(value: CandidateRecord) -> CandidateGraphChangeRow:
    change = value.change
    return CandidateGraphChangeRow(
        change_id=change.change_id,
        target_graph=change.target_graph.value,
        operation=change.operation.value,
        submitted_by=change.submitted_by,
        reason=change.reason,
        payload=dict(change.payload),
        payload_sha256=value.payload_sha256,
        idempotency_key=value.idempotency_key,
        review_status=change.review_status.value,
        created_at=value.created_at,
        reviewed_at=value.reviewed_at,
        reviewed_by=change.reviewed_by,
        review_reason=change.review_reason,
        approved_object_id=value.approved_object_id,
        ingestion_run_id=value.ingestion_run_id,
    )


def _candidate_evidence_rows(value: CandidateRecord) -> list[CandidateEvidenceRefRow]:
    return [
        CandidateEvidenceRefRow(
            change_id=value.change.change_id,
            ordinal=ordinal,
            source_id=ref.source_id,
            document_id=ref.document_id,
            version_id=ref.version_id,
            content_fragment_id=ref.content_fragment_id,
            source_anchor={
                "type": ref.source_anchor["type"],
                "value": dict(ref.source_anchor["value"]),
            },
        )
        for ordinal, ref in enumerate(value.change.evidence_refs)
    ]


def _evidence_refs(session: Session, change_id: str) -> tuple[EvidenceRef, ...]:
    rows = session.scalars(
        select(CandidateEvidenceRefRow)
        .where(CandidateEvidenceRefRow.change_id == change_id)
        .order_by(CandidateEvidenceRefRow.ordinal)
    ).all()
    return tuple(
        EvidenceRef.from_dict(
            {
                "source_id": row.source_id,
                "document_id": row.document_id,
                "version_id": row.version_id,
                "content_fragment_id": row.content_fragment_id,
                "source_anchor": dict(row.source_anchor),
            }
        )
        for row in rows
    )


def _to_candidate(session: Session, row: CandidateGraphChangeRow) -> CandidateRecord:
    change = CandidateGraphChange(
        change_id=row.change_id,
        target_graph=row.target_graph,
        operation=row.operation,
        submitted_by=row.submitted_by,
        reason=row.reason,
        evidence_refs=_evidence_refs(session, row.change_id),
        payload=dict(row.payload),
        review_status=row.review_status,
        reviewed_by=row.reviewed_by,
        review_reason=row.review_reason,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=row.idempotency_key,
        payload_sha256=row.payload_sha256,
        created_at=_aware(row.created_at),
        reviewed_at=_aware(row.reviewed_at),
        approved_object_id=row.approved_object_id,
        ingestion_run_id=row.ingestion_run_id,
    )


def _actor_kind(submitted_by: str) -> ActorKind:
    prefix = submitted_by.split(":", 1)[0]
    try:
        return ActorKind(prefix)
    except ValueError:
        return ActorKind.AGENT


def _submitted_event(value: CandidateRecord) -> ReviewEvent:
    return ReviewEvent(
        event_id=f"review-event:{value.change.change_id}:submitted",
        change_id=value.change.change_id,
        event_type=ReviewEventType.SUBMITTED,
        actor_id=value.change.submitted_by,
        actor_kind=_actor_kind(value.change.submitted_by),
        reason="candidate submitted",
        created_at=value.created_at,
        metadata={
            "ingestion_run_id": value.ingestion_run_id,
            "target_graph": value.change.target_graph.value,
        },
    )


def _event_row(value: ReviewEvent) -> CandidateReviewEventRow:
    return CandidateReviewEventRow(
        event_id=value.event_id,
        change_id=value.change_id,
        event_type=value.event_type.value,
        actor_id=value.actor_id,
        actor_kind=value.actor_kind.value,
        reason=value.reason,
        created_at=value.created_at,
        metadata_json=dict(value.metadata),
    )


def _to_event(row: CandidateReviewEventRow) -> ReviewEvent:
    return ReviewEvent(
        event_id=row.event_id,
        change_id=row.change_id,
        event_type=row.event_type,
        actor_id=row.actor_id,
        actor_kind=row.actor_kind,
        reason=row.reason,
        created_at=_aware(row.created_at),
        metadata=dict(row.metadata_json),
    )


class SqlAlchemyCandidateRepository:
    """Persistent idempotent queue for candidate ME-Brain and ME-Who changes."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def submit(self, candidate: CandidateRecord) -> CandidateRecord:
        if candidate.change.review_status is not ReviewStatus.PENDING:
            raise CandidateConflictError("only pending candidates can enter the queue")
        try:
            with self._sessions.begin() as session:
                existing = session.scalar(
                    select(CandidateGraphChangeRow).where(
                        CandidateGraphChangeRow.idempotency_key
                        == candidate.idempotency_key
                    )
                )
                if existing is not None:
                    current = _to_candidate(session, existing)
                    if (
                        current.payload_sha256 == candidate.payload_sha256
                        and current.change.target_graph is candidate.change.target_graph
                        and current.change.operation is candidate.change.operation
                    ):
                        return current
                    raise CandidateConflictError(
                        "candidate idempotency key already exists with a different payload"
                    )
                if session.get(CandidateGraphChangeRow, candidate.change.change_id) is not None:
                    raise CandidateConflictError("candidate change_id already exists")
                if (
                    candidate.ingestion_run_id is not None
                    and session.get(IngestionRunRow, candidate.ingestion_run_id) is None
                ):
                    raise CandidateConflictError("candidate ingestion run does not exist")
                self._validate_evidence(session, candidate)
                session.add(_candidate_row(candidate))
                session.flush()
                session.add_all(_candidate_evidence_rows(candidate))
                session.add(_event_row(_submitted_event(candidate)))
                session.flush()
                return candidate
        except CandidateConflictError:
            raise
        except IntegrityError as exc:
            raise CandidateConflictError("candidate conflicts with an existing persistent record") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist candidate graph change") from exc

    def get(self, change_id: str) -> CandidateRecord:
        try:
            with self._sessions() as session:
                return _to_candidate(session, self._get_row(session, change_id))
        except CandidateNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read candidate graph change") from exc

    def list_pending(
        self,
        *,
        target_graph: GraphNamespace | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> tuple[CandidateRecord, ...]:
        if not 1 <= int(limit) <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = select(CandidateGraphChangeRow).where(
            CandidateGraphChangeRow.review_status == ReviewStatus.PENDING.value
        )
        if target_graph is not None:
            statement = statement.where(
                CandidateGraphChangeRow.target_graph == target_graph.value
            )
        if source_id is not None:
            statement = (
                statement.join(
                    CandidateEvidenceRefRow,
                    CandidateEvidenceRefRow.change_id
                    == CandidateGraphChangeRow.change_id,
                )
                .where(CandidateEvidenceRefRow.source_id == source_id)
                .distinct()
            )
        statement = statement.order_by(
            CandidateGraphChangeRow.created_at,
            CandidateGraphChangeRow.change_id,
        ).limit(int(limit))
        try:
            with self._sessions() as session:
                return tuple(
                    _to_candidate(session, row)
                    for row in session.scalars(statement).all()
                )
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list pending candidates") from exc

    def list_events(self, change_id: str) -> tuple[ReviewEvent, ...]:
        try:
            with self._sessions() as session:
                self._get_row(session, change_id)
                rows = session.scalars(
                    select(CandidateReviewEventRow)
                    .where(CandidateReviewEventRow.change_id == change_id)
                    .order_by(
                        CandidateReviewEventRow.created_at,
                        CandidateReviewEventRow.event_id,
                    )
                ).all()
                return tuple(_to_event(row) for row in rows)
        except CandidateNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list candidate review events") from exc

    @staticmethod
    def _get_row(session: Session, change_id: str) -> CandidateGraphChangeRow:
        row = session.get(CandidateGraphChangeRow, change_id)
        if row is None:
            raise CandidateNotFoundError(f"candidate not found: {change_id}")
        return row

    @staticmethod
    def _validate_evidence(session: Session, candidate: CandidateRecord) -> None:
        for ref in candidate.change.evidence_refs:
            if session.get(SourceRecordRow, ref.source_id) is None:
                raise CandidateConflictError("candidate evidence source does not exist")
            if (
                ref.content_fragment_id is not None
                and session.get(EvidenceFragmentRow, ref.content_fragment_id) is None
            ):
                raise CandidateConflictError("candidate evidence fragment does not exist")
