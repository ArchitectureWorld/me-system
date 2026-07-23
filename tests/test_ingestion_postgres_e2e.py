from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

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
from me_system.fixtures import load_graph_fixture
from me_system.ingestion.contracts import (
    CandidateRecord,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    candidate_payload_sha256,
)
from me_system.ingestion.review import PersistentReviewService
from me_system.persistence.candidate_repository import SqlAlchemyCandidateRepository
from me_system.persistence.database import create_database_engine
from me_system.persistence.migrations import upgrade_database
from me_system.persistence.source_repository import SqlAlchemySourceRepository
from me_system.persistence.store import create_postgres_graph_store
from me_system.query import GraphQueryService


POSTGRES_URL = os.getenv("ME_GRAPH_TEST_POSTGRES_URL")
FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "graph" / "lighting-platform.json"
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
PROJECT_ID = "brain:project:lighting-platform"
USER_ID = "who:user:master"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="ME_GRAPH_TEST_POSTGRES_URL is not configured",
)


def source() -> SourceRecord:
    return SourceRecord(
        source_id="source:conversation:postgres-ingestion-001",
        source_type="agent_conversation",
        external_system="hermes",
        external_id="postgres-ingestion-001",
        idempotency_key="hermes:postgres-ingestion-001:export-1",
        content_ref="file:///data/postgres-ingestion-001.json",
        content_sha256="a" * 64,
        media_type="application/json",
        occurred_at=NOW,
        ingested_at=NOW,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
        metadata={"project_id": PROJECT_ID},
    )


def fragment() -> EvidenceFragment:
    return EvidenceFragment(
        fragment_id="fragment:conversation:postgres-ingestion-001:42",
        source_id=source().source_id,
        ordinal=42,
        fragment_type=FragmentType.CONVERSATION_MESSAGE,
        text_content="第一阶段只考虑人工照明；明确实现任务直接执行。",
        source_anchor={
            "type": "conversation_message",
            "value": {
                "conversation_id": "postgres-ingestion-001",
                "message_id": "msg-42",
            },
        },
        content_sha256="b" * 64,
        occurred_at=NOW,
        actor_id=USER_ID,
        metadata={"role": "user"},
    )


def candidate_node(
    *,
    change_id: str,
    idempotency_key: str,
    graph: GraphNamespace,
    object_id: str,
    object_type: str,
    label: str,
    properties: dict[str, object],
    sensitivity: Sensitivity,
    run_id: str,
) -> CandidateRecord:
    ref = fragment().to_evidence_ref()
    payload = {
        "schema_version": "graph-node/0.1",
        "id": object_id,
        "graph": graph.value,
        "type": object_type,
        "label": label,
        "properties": properties,
        "authority": AuthorityLevel.CANDIDATE.value,
        "confirmation_status": ConfirmationStatus.PENDING.value,
        "status": TemporalStatus.CURRENT.value,
        "valid_from": "2026-07-23T12:00:00Z",
        "valid_to": None,
        "sensitivity": sensitivity.value,
        "source_refs": [ref.to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=graph,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="adapter:agent-conversation:0.1.0",
        reason="explicit statement in conversation",
        evidence_refs=(ref,),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=idempotency_key,
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=run_id,
    )


def candidate_edge(
    *,
    change_id: str,
    idempotency_key: str,
    graph: GraphNamespace,
    edge_id: str,
    edge_type: str,
    from_id: str,
    to_id: str,
    sensitivity: Sensitivity,
    run_id: str,
) -> CandidateRecord:
    ref: EvidenceRef = fragment().to_evidence_ref()
    payload = {
        "schema_version": "graph-edge/0.1",
        "id": edge_id,
        "graph": graph.value,
        "type": edge_type,
        "from_id": from_id,
        "to_id": to_id,
        "properties": {},
        "authority": AuthorityLevel.CANDIDATE.value,
        "confirmation_status": ConfirmationStatus.PENDING.value,
        "confidence": 1.0,
        "valid_from": "2026-07-23T12:00:00Z",
        "valid_to": None,
        "sensitivity": sensitivity.value,
        "source_refs": [ref.to_dict()],
    }
    change = CandidateGraphChange(
        change_id=change_id,
        target_graph=graph,
        operation=ChangeOperation.ADD_EDGE,
        submitted_by="adapter:agent-conversation:0.1.0",
        reason="explicit relation in conversation",
        evidence_refs=(ref,),
        payload=payload,
    )
    return CandidateRecord(
        change=change,
        idempotency_key=idempotency_key,
        payload_sha256=candidate_payload_sha256(payload),
        created_at=NOW,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=run_id,
    )


def test_postgres_source_candidate_review_and_query_round_trip() -> None:
    assert POSTGRES_URL is not None
    schema = f"me_system_ingestion_{uuid4().hex}"
    base_engine = create_database_engine(POSTGRES_URL)
    parsed = make_url(POSTGRES_URL)
    isolated = parsed.update_query_dict({"options": f"-csearch_path={schema}"})
    isolated_url = isolated.render_as_string(hide_password=False)

    with base_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        upgrade_database(isolated_url)
        graph_store = create_postgres_graph_store(isolated_url)
        load_graph_fixture(FIXTURE, graph_store)
        engine = graph_store.engine
        sources = SqlAlchemySourceRepository(engine)
        candidates = SqlAlchemyCandidateRepository(engine)
        review = PersistentReviewService(engine)

        sources.register(source())
        sources.add_fragments(source().source_id, (fragment(),))
        run = IngestionRun.new(
            run_id="run:postgres-ingestion-001:0.1.0",
            source_id=source().source_id,
            adapter_name="agent-conversation",
            adapter_version="0.1.0",
            started_at=NOW,
            input_item_count=1,
        )
        sources.create_run(run)
        sources.start_run(run.run_id)
        sources.complete_run(
            run.run_id,
            IngestionResult(
                status=IngestionStatus.COMPLETED,
                completed_at=NOW,
                processed_item_count=1,
                skipped_item_count=0,
                failed_item_count=0,
                fragment_count=1,
                candidate_count=4,
                coverage_ratio=1.0,
                quality_report={"ambiguous_relations": 0},
            ),
        )

        brain_node_id = "brain:constraint:conversation-artificial-light-only"
        brain_node = candidate_node(
            change_id="candidate:postgres:brain-node",
            idempotency_key="postgres:brain-node",
            graph=GraphNamespace.ME_BRAIN,
            object_id=brain_node_id,
            object_type="Constraint",
            label="对话确认：第一阶段只考虑人工照明",
            properties={"scope": "lighting_calculation"},
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            run_id=run.run_id,
        )
        brain_edge = candidate_edge(
            change_id="candidate:postgres:brain-edge",
            idempotency_key="postgres:brain-edge",
            graph=GraphNamespace.ME_BRAIN,
            edge_id="edge:project-has-conversation-constraint",
            edge_type="HAS_CONSTRAINT",
            from_id=PROJECT_ID,
            to_id=brain_node_id,
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            run_id=run.run_id,
        )
        who_node_id = "who:collaboration-rule:conversation-direct-execution"
        who_node = candidate_node(
            change_id="candidate:postgres:who-node",
            idempotency_key="postgres:who-node",
            graph=GraphNamespace.ME_WHO,
            object_id=who_node_id,
            object_type="CollaborationRule",
            label="对话确认：明确实现任务直接执行",
            properties={
                "task_types": ["implementation"],
                "project_ids": [PROJECT_ID],
            },
            sensitivity=Sensitivity.PERSONAL_PRIVATE,
            run_id=run.run_id,
        )
        who_edge = candidate_edge(
            change_id="candidate:postgres:who-edge",
            idempotency_key="postgres:who-edge",
            graph=GraphNamespace.ME_WHO,
            edge_id="edge:user-has-conversation-direct-execution",
            edge_type="HAS_COLLABORATION_RULE",
            from_id=USER_ID,
            to_id=who_node_id,
            sensitivity=Sensitivity.PERSONAL_PRIVATE,
            run_id=run.run_id,
        )

        for value in (brain_node, brain_edge, who_node, who_edge):
            candidates.submit(value)
        review.approve(brain_node.change.change_id, USER_ID)
        review.approve(brain_edge.change.change_id, USER_ID)
        review.approve(who_node.change.change_id, USER_ID)
        review.approve(who_edge.change.change_id, USER_ID)

        # Recreate repositories and query services to prove persistence.
        reopened_store = create_postgres_graph_store(isolated_url)
        reopened_candidates = SqlAlchemyCandidateRepository(reopened_store.engine)
        query = GraphQueryService(reopened_store)
        snapshot = query.get_project_snapshot(PROJECT_ID)
        profile = query.get_task_profile(USER_ID, PROJECT_ID, "implementation")

        assert brain_node_id in {node.id for node in snapshot.nodes}
        assert who_node_id in {node.id for node in profile.nodes}
        assert query.get_evidence(brain_node_id)[0].content_fragment_id == fragment().fragment_id
        assert reopened_candidates.get(brain_node.change.change_id).approved_object_id == brain_node_id
        assert [
            event.event_type.value
            for event in reopened_candidates.list_events(brain_node.change.change_id)
        ] == ["submitted", "approved"]
    finally:
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        base_engine.dispose()
