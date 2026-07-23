from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from me_system.contracts import Sensitivity
from me_system.errors import EvidenceConflictError, SourceConflictError, SourceNotFoundError
from me_system.evidence.contracts import EvidenceFragment, FragmentType, SourceRecord
from me_system.persistence.models import create_schema
from me_system.persistence.source_repository import SqlAlchemySourceRepository
from me_system.persistence.testing import create_sqlite_test_engine


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def source(*, source_id: str = "source:conversation:001", content_hash: str = "a" * 64) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type="agent_conversation",
        external_system="hermes",
        external_id="conversation-001",
        idempotency_key="hermes:conversation-001:export-1",
        content_ref="file:///data/conversation-001.json",
        content_sha256=content_hash,
        media_type="application/json",
        occurred_at=NOW,
        ingested_at=NOW,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
        metadata={"title": "照明平台讨论"},
    )


def fragment(
    fragment_id: str,
    ordinal: int,
    *,
    text: str,
    content_hash: str,
) -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id=fragment_id,
        source_id="source:conversation:001",
        ordinal=ordinal,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content=text,
        source_anchor={
            "type": "conversation_message",
            "value": {"message_id": fragment_id},
        },
        content_sha256=content_hash,
        occurred_at=NOW,
        actor_id="who:user:master",
        metadata={"role": "user"},
    )


@pytest.fixture
def repository() -> SqlAlchemySourceRepository:
    engine = create_sqlite_test_engine()
    create_schema(engine)
    return SqlAlchemySourceRepository(engine)


def test_register_and_get_source(repository: SqlAlchemySourceRepository) -> None:
    value = source()
    assert repository.register(value) == value
    assert repository.get(value.source_id) == value


def test_identical_source_retry_returns_existing_record(repository: SqlAlchemySourceRepository) -> None:
    first = source()
    retry = SourceRecord.from_dict(
        {
            **first.to_dict(),
            "source_id": "source:conversation:retry",
            "ingested_at": "2026-07-24T12:00:00Z",
        }
    )
    assert repository.register(first) == first
    assert repository.register(retry) == first


def test_source_retry_with_changed_content_is_rejected(repository: SqlAlchemySourceRepository) -> None:
    repository.register(source())
    with pytest.raises(SourceConflictError) as exc:
        repository.register(source(source_id="source:retry", content_hash="b" * 64))
    assert "conversation-001.json" not in str(exc.value)


def test_missing_source_is_explicit(repository: SqlAlchemySourceRepository) -> None:
    with pytest.raises(SourceNotFoundError):
        repository.get("source:missing")


def test_fragments_are_idempotent_and_listed_in_ordinal_order(repository: SqlAlchemySourceRepository) -> None:
    repository.register(source())
    second = fragment("fragment:2", 2, text="第二条", content_hash="2" * 64)
    first = fragment("fragment:1", 1, text="第一条", content_hash="1" * 64)
    assert repository.add_fragments(source().source_id, (second, first)) == (first, second)
    assert repository.add_fragments(source().source_id, (first, second)) == (first, second)
    assert repository.list_fragments(source().source_id) == (first, second)


def test_fragment_id_conflict_is_rejected_atomically(repository: SqlAlchemySourceRepository) -> None:
    repository.register(source())
    first = fragment("fragment:1", 1, text="第一条", content_hash="1" * 64)
    repository.add_fragments(source().source_id, (first,))
    conflicting = fragment("fragment:1", 1, text="已改变", content_hash="9" * 64)
    new_value = fragment("fragment:2", 2, text="第二条", content_hash="2" * 64)
    with pytest.raises(EvidenceConflictError):
        repository.add_fragments(source().source_id, (conflicting, new_value))
    assert repository.list_fragments(source().source_id) == (first,)


def test_ordinal_conflict_is_rejected(repository: SqlAlchemySourceRepository) -> None:
    repository.register(source())
    first = fragment("fragment:1", 1, text="第一条", content_hash="1" * 64)
    repository.add_fragments(source().source_id, (first,))
    with pytest.raises(EvidenceConflictError):
        repository.add_fragments(
            source().source_id,
            (fragment("fragment:other", 1, text="其他", content_hash="8" * 64),),
        )


def test_file_database_survives_repository_recreation(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'me-system.db'}"
    engine1 = create_sqlite_test_engine(url)
    create_schema(engine1)
    first_repository = SqlAlchemySourceRepository(engine1)
    first_repository.register(source())
    first_repository.add_fragments(
        source().source_id,
        (fragment("fragment:1", 1, text="第一条", content_hash="1" * 64),),
    )
    engine1.dispose()

    engine2 = create_sqlite_test_engine(url)
    second_repository = SqlAlchemySourceRepository(engine2)
    assert second_repository.get(source().source_id) == source()
    assert second_repository.list_fragments(source().source_id)[0].fragment_id == "fragment:1"
