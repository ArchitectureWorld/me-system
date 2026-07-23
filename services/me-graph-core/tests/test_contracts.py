from __future__ import annotations

from datetime import datetime, timezone

import pytest

from me_graph_core.contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    EvidenceRef,
    GraphEdge,
    GraphNamespace,
    GraphNode,
    GraphSlice,
    ReviewStatus,
    Sensitivity,
    TemporalStatus,
)
from me_graph_core.errors import ContractValidationError


def evidence(source_id: str = "src_1") -> EvidenceRef:
    return EvidenceRef(
        source_id=source_id,
        document_id="doc_1",
        version_id="docv_1",
        content_fragment_id="fragment_1",
        source_anchor={"type": "conversation_message", "value": {"message_id": "42"}},
    )


def brain_node(**overrides: object) -> GraphNode:
    values: dict[str, object] = {
        "id": "brain:decision:radiance-primary",
        "graph": GraphNamespace.ME_BRAIN,
        "type": "Decision",
        "label": "Radiance 作为主计算核心",
        "properties": {"rationale": "稳定主路线"},
        "authority": AuthorityLevel.CANONICAL,
        "confirmation_status": ConfirmationStatus.HUMAN_CONFIRMED,
        "status": TemporalStatus.CURRENT,
        "valid_from": datetime(2026, 7, 14, tzinfo=timezone.utc),
        "valid_to": None,
        "sensitivity": Sensitivity.PROJECT_PRIVATE,
        "source_refs": (evidence(),),
    }
    values.update(overrides)
    return GraphNode(**values)


def test_graph_node_round_trips_to_dict_and_from_dict() -> None:
    node = brain_node()
    restored = GraphNode.from_dict(node.to_dict())
    assert restored == node
    assert restored.to_dict()["schema_version"] == "graph-node/0.1"


def test_me_brain_node_requires_brain_identifier_prefix() -> None:
    with pytest.raises(ContractValidationError, match="brain:"):
        brain_node(id="who:decision:radiance-primary")


def test_node_rejects_valid_to_before_valid_from() -> None:
    with pytest.raises(ContractValidationError, match="valid_to"):
        brain_node(
            valid_from=datetime(2026, 7, 14, tzinfo=timezone.utc),
            valid_to=datetime(2026, 7, 13, tzinfo=timezone.utc),
        )


def test_canonical_node_requires_evidence() -> None:
    with pytest.raises(ContractValidationError, match="source_refs"):
        brain_node(source_refs=())


def test_graph_edge_rejects_self_loop() -> None:
    with pytest.raises(ContractValidationError, match="self-loop"):
        GraphEdge(
            id="edge_1",
            graph=GraphNamespace.ME_BRAIN,
            type="SUPERSEDES",
            from_id="brain:decision:a",
            to_id="brain:decision:a",
            properties={},
            authority=AuthorityLevel.CANONICAL,
            confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
            confidence=1.0,
            valid_from=None,
            valid_to=None,
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            source_refs=(evidence(),),
        )


def test_candidate_change_materializes_candidate_node() -> None:
    payload = brain_node(
        authority=AuthorityLevel.CANDIDATE,
        confirmation_status=ConfirmationStatus.PENDING,
    ).to_dict()
    change = CandidateGraphChange(
        change_id="change_1",
        target_graph=GraphNamespace.ME_BRAIN,
        operation=ChangeOperation.ADD_NODE,
        submitted_by="hermes-primary",
        reason="用户明确确认新的技术路线",
        evidence_refs=(evidence(),),
        payload=payload,
        review_status=ReviewStatus.PENDING,
    )
    materialized = change.materialize()
    assert isinstance(materialized, GraphNode)
    assert materialized.authority is AuthorityLevel.CANDIDATE


def test_candidate_change_rejects_payload_for_other_graph() -> None:
    payload = brain_node(
        id="who:preference:direct-execution",
        graph=GraphNamespace.ME_WHO,
        type="Preference",
        authority=AuthorityLevel.CANDIDATE,
        confirmation_status=ConfirmationStatus.PENDING,
        sensitivity=Sensitivity.PERSONAL_PRIVATE,
    ).to_dict()
    with pytest.raises(ContractValidationError, match="target_graph"):
        CandidateGraphChange(
            change_id="change_2",
            target_graph=GraphNamespace.ME_BRAIN,
            operation=ChangeOperation.ADD_NODE,
            submitted_by="hermes-primary",
            reason="wrong graph",
            evidence_refs=(evidence(),),
            payload=payload,
            review_status=ReviewStatus.PENDING,
        )


def test_graph_slice_serializes_contract_objects() -> None:
    node = brain_node()
    graph_slice = GraphSlice(
        slice_id="slice_1",
        graph=GraphNamespace.ME_BRAIN,
        as_of_time=datetime(2026, 7, 23, tzinfo=timezone.utc),
        root_ids=(node.id,),
        summary="项目当前状态",
        nodes=(node,),
        edges=(),
        evidence_handles=(evidence(),),
        excluded={"superseded": (), "unauthorized": ()},
        truncated=False,
    )
    payload = graph_slice.to_dict()
    assert payload["nodes"][0]["id"] == node.id
    assert payload["excluded"] == {"superseded": [], "unauthorized": []}
