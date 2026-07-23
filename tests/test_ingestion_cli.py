from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from me_system.cli import main
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
from me_system.evidence.contracts import EvidenceFragment, FragmentType, SourceRecord
from me_system.ingestion.contracts import CandidateRecord, candidate_payload_sha256


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def source() -> SourceRecord:
    return SourceRecord(
        source_id="source:conversation:cli-001",
        source_type="agent_conversation",
        external_system="hermes",
        external_id="cli-conversation-001",
        idempotency_key="hermes:cli-conversation-001:export-1",
        content_ref="file:///data/cli-conversation-001.json",
        content_sha256="a" * 64,
        media_type="application/json",
        occurred_at=NOW,
        ingested_at=NOW,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
        metadata={"title": "CLI ingestion test"},
    )


def fragment() -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id="fragment:conversation:cli-001:42",
        source_id=source().source_id,
        ordinal=42,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content="第一阶段只考虑人工照明。",
        source_anchor={
            "type": "conversation_message",
            "value": {"conversation_id": "cli-001", "message_id": "msg-42"},
        },
        content_sha256="b" * 64,
        occurred_at=NOW,
        actor_id="who:user:master",
        metadata={"role": "user"},
    )


def candidate(
    *,
    change_id: str = "candidate:cli:constraint",
    object_id: str = "brain:constraint:cli-artificial-light-only",
) -> CandidateRecord:
    ref: EvidenceRef = fragment().to_evidence_ref()
    payload = {
        "schema_version": "graph-node/0.1",
        "id": object_id,
        "graph": GraphNamespace.ME_BRAIN.value,
        "type": "Constraint",
        "label": "第一阶段只考虑人工照明",
        "properties": {"scope": "lighting_calculation"},
        "authority": AuthorityLevel.CANDIDATE.value,
        "confirmation_status": ConfirmationStatus.PENDING.value,
        "status": TemporalStatus.CURRENT.value,
        "valid_from": "2026-07-23T12:00:00Z",
        "valid_to": None,
        "sensitivity": Sensitivity.PROJECT_PRIVATE.value,
        "source_refs": [ref.to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=GraphNamespace.ME_BRAIN,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:cli-test:0.1.0",
        reason="explicit constraint",
        evidence_refs=(ref,),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=f"cli-test:{change_id}",
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=None,
    )


def run_cli(*args: str) -> tuple[int, dict[str, object], dict[str, object]]:
    from io import StringIO
    import contextlib

    stdout = StringIO()
    stderr = StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(list(args))
    out = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
    err = json.loads(stderr.getvalue()) if stderr.getvalue().strip() else {}
    return code, out, err


def setup_database(tmp_path: Path) -> tuple[str, tuple[str, ...]]:
    url = f"sqlite+pysqlite:///{tmp_path / 'me-system.db'}"
    database_args = ("--database-url", url, "--allow-test-database")
    code, output, error = run_cli("db-upgrade", *database_args)
    assert code == 0, error
    assert output == {"status": "upgraded"}
    return url, database_args


def test_source_register_and_show_include_fragments(tmp_path: Path) -> None:
    _, database_args = setup_database(tmp_path)
    payload_path = write_json(
        tmp_path / "source.json",
        {"source": source().to_dict(), "fragments": [fragment().to_dict()]},
    )
    code, output, error = run_cli(
        "source-register",
        *database_args,
        "--json",
        str(payload_path),
    )
    assert code == 0, error
    assert output["source"]["source_id"] == source().source_id
    assert output["fragment_count"] == 1

    code, shown, error = run_cli(
        "source-show",
        *database_args,
        "--source-id",
        source().source_id,
    )
    assert code == 0, error
    assert shown["source"]["source_id"] == source().source_id
    assert shown["fragments"][0]["fragment_id"] == fragment().fragment_id


def test_candidate_submit_list_and_approve(tmp_path: Path) -> None:
    _, database_args = setup_database(tmp_path)
    source_path = write_json(
        tmp_path / "source.json",
        {"source": source().to_dict(), "fragments": [fragment().to_dict()]},
    )
    assert run_cli("source-register", *database_args, "--json", str(source_path))[0] == 0

    candidate_path = write_json(tmp_path / "candidate.json", candidate().to_dict())
    code, submitted, error = run_cli(
        "candidate-submit",
        *database_args,
        "--json",
        str(candidate_path),
    )
    assert code == 0, error
    assert submitted["change"]["review_status"] == "pending"

    code, listed, error = run_cli(
        "candidate-list",
        *database_args,
        "--target-graph",
        "me_brain",
        "--source-id",
        source().source_id,
    )
    assert code == 0, error
    assert listed["count"] == 1
    assert listed["candidates"][0]["change"]["change_id"] == candidate().change.change_id

    code, approved, error = run_cli(
        "candidate-approve",
        *database_args,
        "--change-id",
        candidate().change.change_id,
        "--reviewer-id",
        "who:user:master",
        "--reason",
        "confirmed project constraint",
    )
    assert code == 0, error
    assert approved["object"]["id"] == candidate().change.materialize().id
    assert approved["candidate"]["change"]["review_status"] == "approved"
    assert [event["event_type"] for event in approved["events"]] == [
        "submitted",
        "approved",
    ]


def test_candidate_reject_and_safe_missing_source_error(tmp_path: Path) -> None:
    _, database_args = setup_database(tmp_path)
    source_path = write_json(
        tmp_path / "source.json",
        {"source": source().to_dict(), "fragments": [fragment().to_dict()]},
    )
    assert run_cli("source-register", *database_args, "--json", str(source_path))[0] == 0
    value = candidate(
        change_id="candidate:cli:reject",
        object_id="brain:constraint:cli-rejected",
    )
    candidate_path = write_json(tmp_path / "reject.json", value.to_dict())
    assert run_cli("candidate-submit", *database_args, "--json", str(candidate_path))[0] == 0

    code, rejected, error = run_cli(
        "candidate-reject",
        *database_args,
        "--change-id",
        value.change.change_id,
        "--reviewer-id",
        "who:user:master",
        "--reason",
        "not stable enough",
    )
    assert code == 0, error
    assert rejected["candidate"]["change"]["review_status"] == "rejected"
    assert [event["event_type"] for event in rejected["events"]] == [
        "submitted",
        "rejected",
    ]

    code, _, error = run_cli(
        "source-show",
        *database_args,
        "--source-id",
        "source:missing",
    )
    assert code == 2
    assert error["error_type"] == "SourceNotFoundError"
    assert "sqlite" not in error["error"].lower()
