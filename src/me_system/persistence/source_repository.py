from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import Engine, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..errors import (
    ContractValidationError,
    EvidenceConflictError,
    GraphStoreUnavailableError,
    IngestionStateError,
    SourceConflictError,
    SourceNotFoundError,
)
from ..evidence.contracts import EvidenceFragment, SourceRecord
from ..ingestion.contracts import IngestionResult, IngestionRun, IngestionStatus
from .models import EvidenceFragmentRow, IngestionRunRow, SourceRecordRow


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _source_row(value: SourceRecord) -> SourceRecordRow:
    return SourceRecordRow(
        source_id=value.source_id,
        source_type=value.source_type,
        external_system=value.external_system,
        external_id=value.external_id,
        idempotency_key=value.idempotency_key,
        content_ref=value.content_ref,
        content_sha256=value.content_sha256,
        media_type=value.media_type,
        occurred_at=value.occurred_at,
        ingested_at=value.ingested_at,
        sensitivity=value.sensitivity.value,
        metadata_json=dict(value.metadata),
    )


def _to_source(row: SourceRecordRow) -> SourceRecord:
    return SourceRecord(
        source_id=row.source_id,
        source_type=row.source_type,
        external_system=row.external_system,
        external_id=row.external_id,
        idempotency_key=row.idempotency_key,
        content_ref=row.content_ref,
        content_sha256=row.content_sha256,
        media_type=row.media_type,
        occurred_at=_aware(row.occurred_at),
        ingested_at=_aware(row.ingested_at),
        sensitivity=row.sensitivity,
        metadata=dict(row.metadata_json),
    )


def _fragment_row(value: EvidenceFragment) -> EvidenceFragmentRow:
    return EvidenceFragmentRow(
        fragment_id=value.fragment_id,
        source_id=value.source_id,
        ordinal=value.ordinal,
        fragment_type=value.fragment_type.value,
        text_content=value.text_content,
        source_anchor={
            "type": value.source_anchor["type"],
            "value": dict(value.source_anchor["value"]),
        },
        content_sha256=value.content_sha256,
        occurred_at=value.occurred_at,
        actor_id=value.actor_id,
        metadata_json=dict(value.metadata),
    )


def _to_fragment(row: EvidenceFragmentRow) -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id=row.fragment_id,
        source_id=row.source_id,
        ordinal=row.ordinal,
        fragment_type=row.fragment_type,
        text_content=row.text_content,
        source_anchor=dict(row.source_anchor),
        content_sha256=row.content_sha256,
        occurred_at=_aware(row.occurred_at),
        actor_id=row.actor_id,
        metadata=dict(row.metadata_json),
    )


def _run_row(value: IngestionRun) -> IngestionRunRow:
    return IngestionRunRow(
        run_id=value.run_id,
        source_id=value.source_id,
        adapter_name=value.adapter_name,
        adapter_version=value.adapter_version,
        status=value.status.value,
        started_at=value.started_at,
        completed_at=value.completed_at,
        input_item_count=value.input_item_count,
        processed_item_count=value.processed_item_count,
        skipped_item_count=value.skipped_item_count,
        failed_item_count=value.failed_item_count,
        fragment_count=value.fragment_count,
        candidate_count=value.candidate_count,
        coverage_ratio=value.coverage_ratio,
        quality_report=dict(value.quality_report),
        log_ref=value.log_ref,
        error_summary=value.error_summary,
    )


def _to_run(row: IngestionRunRow) -> IngestionRun:
    return IngestionRun(
        run_id=row.run_id,
        source_id=row.source_id,
        adapter_name=row.adapter_name,
        adapter_version=row.adapter_version,
        status=row.status,
        started_at=_aware(row.started_at),
        completed_at=_aware(row.completed_at),
        input_item_count=row.input_item_count,
        processed_item_count=row.processed_item_count,
        skipped_item_count=row.skipped_item_count,
        failed_item_count=row.failed_item_count,
        fragment_count=row.fragment_count,
        candidate_count=row.candidate_count,
        coverage_ratio=row.coverage_ratio,
        quality_report=dict(row.quality_report),
        log_ref=row.log_ref,
        error_summary=row.error_summary,
    )


def _update_run_row(row: IngestionRunRow, value: IngestionRun) -> None:
    row.status = value.status.value
    row.completed_at = value.completed_at
    row.processed_item_count = value.processed_item_count
    row.skipped_item_count = value.skipped_item_count
    row.failed_item_count = value.failed_item_count
    row.fragment_count = value.fragment_count
    row.candidate_count = value.candidate_count
    row.coverage_ratio = value.coverage_ratio
    row.quality_report = dict(value.quality_report)
    row.log_ref = value.log_ref
    row.error_summary = value.error_summary


class SqlAlchemySourceRepository:
    """Persistent source, evidence, and ingestion status repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def register(self, source: SourceRecord) -> SourceRecord:
        try:
            with self._sessions.begin() as session:
                existing = session.scalar(
                    select(SourceRecordRow).where(
                        SourceRecordRow.idempotency_key == source.idempotency_key
                    )
                )
                if existing is not None:
                    current = _to_source(existing)
                    if current.identity_payload() == source.identity_payload():
                        return current
                    raise SourceConflictError(
                        "source idempotency key already exists with different immutable content"
                    )
                if session.get(SourceRecordRow, source.source_id) is not None:
                    raise SourceConflictError("source_id already exists with different identity")
                session.add(_source_row(source))
                session.flush()
                return source
        except (SourceConflictError, ContractValidationError):
            raise
        except IntegrityError as exc:
            raise SourceConflictError("source identity conflicts with an existing record") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist source record") from exc

    def get(self, source_id: str) -> SourceRecord:
        try:
            with self._sessions() as session:
                return _to_source(self._get_source_row(session, source_id))
        except SourceNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read source record") from exc

    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]:
        ordered = tuple(sorted(fragments, key=lambda item: (item.ordinal, item.fragment_id)))
        try:
            with self._sessions.begin() as session:
                self._get_source_row(session, source_id)
                accepted: list[EvidenceFragment] = []
                for fragment in ordered:
                    if fragment.source_id != source_id:
                        raise EvidenceConflictError(
                            "fragment source_id does not match the requested source"
                        )
                    rows = session.scalars(
                        select(EvidenceFragmentRow).where(
                            or_(
                                EvidenceFragmentRow.fragment_id == fragment.fragment_id,
                                (
                                    (EvidenceFragmentRow.source_id == source_id)
                                    & (EvidenceFragmentRow.ordinal == fragment.ordinal)
                                ),
                            )
                        )
                    ).all()
                    if rows:
                        if len(rows) != 1 or _to_fragment(rows[0]) != fragment:
                            raise EvidenceConflictError(
                                "evidence fragment identity or ordinal conflicts with existing content"
                            )
                        accepted.append(_to_fragment(rows[0]))
                        continue
                    session.add(_fragment_row(fragment))
                    session.flush()
                    accepted.append(fragment)
                return tuple(sorted(accepted, key=lambda item: (item.ordinal, item.fragment_id)))
        except (SourceNotFoundError, EvidenceConflictError, ContractValidationError):
            raise
        except IntegrityError as exc:
            raise EvidenceConflictError("evidence fragment conflicts with existing content") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist evidence fragments") from exc

    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]:
        try:
            with self._sessions() as session:
                self._get_source_row(session, source_id)
                rows = session.scalars(
                    select(EvidenceFragmentRow)
                    .where(EvidenceFragmentRow.source_id == source_id)
                    .order_by(EvidenceFragmentRow.ordinal, EvidenceFragmentRow.fragment_id)
                ).all()
                return tuple(_to_fragment(row) for row in rows)
        except SourceNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to list evidence fragments") from exc

    def create_run(self, run: IngestionRun) -> IngestionRun:
        if run.status is not IngestionStatus.PENDING:
            raise IngestionStateError("new ingestion runs must start in pending state")
        try:
            with self._sessions.begin() as session:
                self._get_source_row(session, run.source_id)
                if session.get(IngestionRunRow, run.run_id) is not None:
                    raise IngestionStateError("ingestion run_id already exists")
                session.add(_run_row(run))
                session.flush()
                return run
        except (SourceNotFoundError, IngestionStateError):
            raise
        except IntegrityError as exc:
            raise IngestionStateError("ingestion run conflicts with an existing record") from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist ingestion run") from exc

    def get_run(self, run_id: str) -> IngestionRun:
        try:
            with self._sessions() as session:
                row = session.get(IngestionRunRow, run_id)
                if row is None:
                    raise IngestionStateError("ingestion run does not exist")
                return _to_run(row)
        except IngestionStateError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read ingestion run") from exc

    def start_run(self, run_id: str) -> IngestionRun:
        try:
            with self._sessions.begin() as session:
                row = self._get_run_row(session, run_id)
                current = _to_run(row)
                if current.status is not IngestionStatus.PENDING:
                    raise IngestionStateError("only a pending ingestion run can start")
                updated = current.as_running()
                _update_run_row(row, updated)
                session.flush()
                return updated
        except (IngestionStateError, ContractValidationError):
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to start ingestion run") from exc

    def complete_run(self, run_id: str, result: IngestionResult) -> IngestionRun:
        try:
            with self._sessions.begin() as session:
                row = self._get_run_row(session, run_id)
                current = _to_run(row)
                if current.status not in {IngestionStatus.PENDING, IngestionStatus.RUNNING}:
                    raise IngestionStateError("only an active ingestion run can complete")
                try:
                    updated = current.complete(result)
                except ContractValidationError as exc:
                    raise IngestionStateError(str(exc)) from exc
                _update_run_row(row, updated)
                session.flush()
                return updated
        except IngestionStateError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to complete ingestion run") from exc

    @staticmethod
    def _get_source_row(session: Session, source_id: str) -> SourceRecordRow:
        row = session.get(SourceRecordRow, source_id)
        if row is None:
            raise SourceNotFoundError(f"source not found: {source_id}")
        return row

    @staticmethod
    def _get_run_row(session: Session, run_id: str) -> IngestionRunRow:
        row = session.get(IngestionRunRow, run_id)
        if row is None:
            raise IngestionStateError("ingestion run does not exist")
        return row
