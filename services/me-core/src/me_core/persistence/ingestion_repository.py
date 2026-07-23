from __future__ import annotations

from datetime import datetime, timezone
import json

from sqlalchemy import Engine, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..errors import (
    EvidenceConflictError,
    GraphStoreUnavailableError,
    SourceConflictError,
    SourceNotFoundError,
)
from ..ingestion.contracts import EvidenceFragment, SourceRecord
from .models import EvidenceFragmentRow, SourceRecordRow


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _source_row(source: SourceRecord) -> SourceRecordRow:
    return SourceRecordRow(
        source_id=source.source_id,
        source_type=source.source_type,
        external_system=source.external_system,
        external_id=source.external_id,
        idempotency_key=source.idempotency_key,
        content_ref=source.content_ref,
        content_sha256=source.content_sha256,
        media_type=source.media_type,
        occurred_at=source.occurred_at,
        ingested_at=source.ingested_at,
        sensitivity=source.sensitivity.value,
        metadata_json=dict(source.metadata),
    )


def _to_source(row: SourceRecordRow) -> SourceRecord:
    return SourceRecord.from_dict(
        {
            "source_id": row.source_id,
            "source_type": row.source_type,
            "external_system": row.external_system,
            "external_id": row.external_id,
            "idempotency_key": row.idempotency_key,
            "content_ref": row.content_ref,
            "content_sha256": row.content_sha256,
            "media_type": row.media_type,
            "occurred_at": _aware(row.occurred_at),
            "ingested_at": _aware(row.ingested_at),
            "sensitivity": row.sensitivity,
            "metadata": dict(row.metadata_json),
        }
    )


def _fragment_row(fragment: EvidenceFragment) -> EvidenceFragmentRow:
    return EvidenceFragmentRow(
        fragment_id=fragment.fragment_id,
        source_id=fragment.source_id,
        ordinal=fragment.ordinal,
        fragment_type=fragment.fragment_type.value,
        text_content=fragment.text_content,
        source_anchor={
            "type": fragment.source_anchor["type"],
            "value": dict(fragment.source_anchor["value"]),
        },
        content_sha256=fragment.content_sha256,
        occurred_at=fragment.occurred_at,
        actor_id=fragment.actor_id,
        sensitivity=fragment.sensitivity.value,
        metadata_json=dict(fragment.metadata),
    )


def _to_fragment(row: EvidenceFragmentRow) -> EvidenceFragment:
    return EvidenceFragment.from_dict(
        {
            "fragment_id": row.fragment_id,
            "source_id": row.source_id,
            "ordinal": row.ordinal,
            "fragment_type": row.fragment_type,
            "text_content": row.text_content,
            "source_anchor": dict(row.source_anchor),
            "content_sha256": row.content_sha256,
            "occurred_at": _aware(row.occurred_at),
            "actor_id": row.actor_id,
            "sensitivity": row.sensitivity,
            "metadata": dict(row.metadata_json),
        }
    )


def _serialized_fragment(fragment: EvidenceFragment) -> str:
    return json.dumps(
        fragment.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class SqlAlchemyIngestionRepository:
    """Persistent Source, Evidence, and Ingestion state inside ME-Core."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    def register_source(self, source: SourceRecord) -> SourceRecord:
        try:
            with self._sessions.begin() as session:
                by_key = session.scalar(
                    select(SourceRecordRow).where(
                        SourceRecordRow.idempotency_key == source.idempotency_key
                    )
                )
                if by_key is not None:
                    existing = _to_source(by_key)
                    if existing.identity_digest() == source.identity_digest():
                        return existing
                    raise SourceConflictError(
                        "source idempotency key conflicts with an existing immutable source"
                    )

                by_id = session.get(SourceRecordRow, source.source_id)
                if by_id is not None:
                    raise SourceConflictError(
                        f"source_id already exists with another idempotency identity: {source.source_id}"
                    )

                session.add(_source_row(source))
                session.flush()
                return source
        except SourceConflictError:
            raise
        except IntegrityError as exc:
            raise SourceConflictError(
                "source registration conflicts with an existing immutable source"
            ) from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist source record") from exc

    def get_source(self, source_id: str) -> SourceRecord:
        try:
            with self._sessions() as session:
                row = session.get(SourceRecordRow, source_id)
                if row is None:
                    raise SourceNotFoundError(f"source not found: {source_id}")
                return _to_source(row)
        except SourceNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to read source record") from exc

    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]:
        normalized = self._normalize_fragment_batch(source_id, fragments)
        try:
            with self._sessions.begin() as session:
                self._require_source_row(session, source_id)
                if not normalized:
                    return ()

                ids = [fragment.fragment_id for fragment in normalized]
                ordinals = [fragment.ordinal for fragment in normalized]
                rows = session.scalars(
                    select(EvidenceFragmentRow).where(
                        or_(
                            EvidenceFragmentRow.fragment_id.in_(ids),
                            (
                                (EvidenceFragmentRow.source_id == source_id)
                                & EvidenceFragmentRow.ordinal.in_(ordinals)
                            ),
                        )
                    )
                ).all()
                existing_by_id = {row.fragment_id: row for row in rows}
                existing_by_ordinal = {
                    row.ordinal: row for row in rows if row.source_id == source_id
                }

                for fragment in normalized:
                    by_id = existing_by_id.get(fragment.fragment_id)
                    if by_id is not None:
                        existing = _to_fragment(by_id)
                        if _serialized_fragment(existing) == _serialized_fragment(fragment):
                            continue
                        raise EvidenceConflictError(
                            f"fragment_id conflicts with existing evidence: {fragment.fragment_id}"
                        )

                    by_ordinal = existing_by_ordinal.get(fragment.ordinal)
                    if by_ordinal is not None:
                        raise EvidenceConflictError(
                            f"ordinal already belongs to another fragment in source {source_id}: {fragment.ordinal}"
                        )

                    session.add(_fragment_row(fragment))

                session.flush()
                return normalized
        except (SourceNotFoundError, EvidenceConflictError):
            raise
        except IntegrityError as exc:
            raise EvidenceConflictError(
                "evidence fragment batch conflicts with existing source evidence"
            ) from exc
        except SQLAlchemyError as exc:
            raise GraphStoreUnavailableError("unable to persist evidence fragments") from exc

    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]:
        try:
            with self._sessions() as session:
                self._require_source_row(session, source_id)
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

    @staticmethod
    def _require_source_row(session: Session, source_id: str) -> SourceRecordRow:
        row = session.get(SourceRecordRow, source_id)
        if row is None:
            raise SourceNotFoundError(f"source not found: {source_id}")
        return row

    @staticmethod
    def _normalize_fragment_batch(
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]:
        by_id: dict[str, EvidenceFragment] = {}
        by_ordinal: dict[int, EvidenceFragment] = {}
        for fragment in fragments:
            if fragment.source_id != source_id:
                raise EvidenceConflictError(
                    "fragment source_id must match the target source_id"
                )
            previous_id = by_id.get(fragment.fragment_id)
            if previous_id is not None:
                if _serialized_fragment(previous_id) != _serialized_fragment(fragment):
                    raise EvidenceConflictError(
                        f"fragment_id appears with conflicting payloads: {fragment.fragment_id}"
                    )
                continue
            previous_ordinal = by_ordinal.get(fragment.ordinal)
            if previous_ordinal is not None:
                raise EvidenceConflictError(
                    f"ordinal appears more than once in the fragment batch: {fragment.ordinal}"
                )
            by_id[fragment.fragment_id] = fragment
            by_ordinal[fragment.ordinal] = fragment
        return tuple(sorted(by_id.values(), key=lambda item: (item.ordinal, item.fragment_id)))
