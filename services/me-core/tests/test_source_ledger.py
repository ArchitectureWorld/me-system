from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from me_core.contracts import Sensitivity
from me_core.errors import EvidenceConflictError, SourceConflictError, SourceNotFoundError
from me_core.ingestion.contracts import EvidenceFragment, FragmentType, SourceRecord
from me_core.ingestion.source import SourceLedgerService
from me_core.persistence.ingestion_repository import SqlAlchemyIngestionRepository
from me_core.persistence.models import create_schema
from me_core.persistence.testing import create_sqlite_test_engine


UTC = timezone.utc


def source(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "source_id": "source:conversation:001",
        "source_type": "agent_conversation",
        "external_system": "hermes",
        "external_id": "conversation-001",
        "idempotency_key": "hermes:conversation-001:v1",
        "content_ref": "file:///data/conversation-001.json",
        "content_sha256": "a" * 64,
        "media_type": "application/json",
        "occurred_at": datetime(2026, 7, 22, 4, 0, tzinfo=UTC),
        "ingested_at": datetime(2026, 7, 23, 4, 0, tzinfo=UTC),
        "sensitivity": Sensitivity.PROJECT_PRIVATE,
        "metadata": {
            "project_id": "brain:project:lighting-platform",
            "nested": {"roles": ["user", "assistant"]},
        },
    }
    values.update(overrides)
    return SourceRecord(**values)


def fragment(
    ordinal: int,
    *,
    fragment_id: str | None = None,
    text: str | None = None,
    source_id: str = "source:conversation:001",
) -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id=fragment_id or f"fragment:conversation:001:{ordinal}",
        source_id=source_id,
        ordinal=ordinal,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content=text or f"message {ordinal}",
        source_anchor={
            "type": "conversation_message",
            "value": {"conversation_id": "conversation-001", "message_id": f"msg-{ordinal}"},
        },
        content_sha256=f"{ordinal % 10}" * 64,
        occurred_at=datetime(2026, 7, 22, 4, ordinal % 60, tzinfo=UTC),
        actor_id="who:user:master",
        sensitivity=Sensitivity.PROJECT_PRIVATE,
        metadata={"language": "zh-CN", "ordinal": ordinal},
    )


def service(url: str = "sqlite+pysqlite:///:memory:") -> SourceLedgerService:
    engine = create_sqlite_test_engine(url)
    create_schema(engine)
    return SourceLedgerService(SqlAlchemyIngestionRepository(engine))


def test_first_registration_and_lookup_round_trip() -> None:
    ledger = service()
    value = source()
    assert ledger.register_source(value) == value
    assert ledger.get_source(value.source_id) == value
    assert ledger.get_source(value.source_id).metadata["nested"] == {"roles": ["user", "assistant"]}


def test_same_source_identity_is_idempotent_even_if_storage_location_changes() -> None:
    ledger = service()
    first = ledger.register_source(source())
    replay = replace(
        source(),
        source_id="source:conversation:replay",
        content_ref="file:///moved/conversation-001.json",
        ingested_at=datetime(2026, 7, 24, 4, 0, tzinfo=UTC),
    )
    assert ledger.register_source(replay) == first


def test_same_idempotency_key_with_changed_content_is_rejected() -> None:
    ledger = service()
    ledger.register_source(source())
    with pytest.raises(SourceConflictError, match="idempotency"):
        ledger.register_source(source(source_id="source:changed", content_sha256="c" * 64))


def test_duplicate_source_id_with_another_idempotency_key_is_rejected() -> None:
    ledger = service()
    ledger.register_source(source())
    with pytest.raises(SourceConflictError, match="source_id"):
        ledger.register_source(source(idempotency_key="another-key", external_id="conversation-002"))


def test_missing_source_raises_domain_error() -> None:
    with pytest.raises(SourceNotFoundError, match="missing"):
        service().get_source("source:missing")


def test_source_survives_repository_recreation(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'ingestion.db'}"
    first = service(url)
    value = first.register_source(source())
    second = service(url)
    assert second.get_source(value.source_id) == value


def test_fragment_batch_is_persisted_and_listed_by_ordinal() -> None:
    ledger = service()
    ledger.register_source(source())
    stored = ledger.add_fragments(source().source_id, (fragment(2), fragment(0), fragment(1)))
    assert [item.ordinal for item in stored] == [0, 1, 2]
    assert ledger.list_fragments(source().source_id) == stored
    assert stored[1].metadata == {"language": "zh-CN", "ordinal": 1}
    assert stored[1].sensitivity is Sensitivity.PROJECT_PRIVATE


def test_exact_fragment_replay_is_idempotent() -> None:
    ledger = service()
    ledger.register_source(source())
    first = ledger.add_fragments(source().source_id, (fragment(0), fragment(1)))
    replay = ledger.add_fragments(source().source_id, (fragment(1), fragment(0)))
    assert replay == first
    assert ledger.list_fragments(source().source_id) == first


def test_changed_fragment_with_same_id_is_rejected() -> None:
    ledger = service()
    ledger.register_source(source())
    ledger.add_fragments(source().source_id, (fragment(0),))
    with pytest.raises(EvidenceConflictError, match="fragment_id"):
        ledger.add_fragments(source().source_id, (fragment(0, text="changed"),))


def test_new_fragment_with_existing_ordinal_is_rejected() -> None:
    ledger = service()
    ledger.register_source(source())
    ledger.add_fragments(source().source_id, (fragment(0),))
    with pytest.raises(EvidenceConflictError, match="ordinal"):
        ledger.add_fragments(
            source().source_id,
            (fragment(0, fragment_id="fragment:other:0"),),
        )


def test_conflicting_batch_rolls_back_new_fragments() -> None:
    ledger = service()
    ledger.register_source(source())
    ledger.add_fragments(source().source_id, (fragment(0),))
    with pytest.raises(EvidenceConflictError):
        ledger.add_fragments(
            source().source_id,
            (
                fragment(1),
                fragment(0, fragment_id="fragment:conflict:0"),
            ),
        )
    assert ledger.list_fragments(source().source_id) == (fragment(0),)


def test_fragments_require_existing_source_and_matching_source_id() -> None:
    ledger = service()
    with pytest.raises(SourceNotFoundError):
        ledger.add_fragments("source:missing", (fragment(0, source_id="source:missing"),))

    ledger.register_source(source())
    with pytest.raises(EvidenceConflictError, match="source_id"):
        ledger.add_fragments(source().source_id, (fragment(0, source_id="source:other"),))
