from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def load_schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def validate(name: str, instance: dict[str, object]) -> None:
    Draft202012Validator(load_schema(name)).validate(instance)


def evidence_ref() -> dict[str, object]:
    return {
        "source_id": "src_conversation_001",
        "document_id": "doc_lighting_notes",
        "version_id": "docv_lighting_notes_01",
        "content_fragment_id": "fragment_42",
        "source_anchor": {"type": "conversation_message", "value": {"message_id": "42"}},
    }


def test_graph_node_schema_accepts_canonical_node() -> None:
    validate(
        "graph-node.schema.json",
        {
            "schema_version": "graph-node/0.1",
            "id": "brain:decision:radiance-primary",
            "graph": "me_brain",
            "type": "Decision",
            "label": "Radiance 作为主计算核心",
            "properties": {"rationale": "稳定的照明计算路线"},
            "authority": "canonical",
            "confirmation_status": "human_confirmed",
            "status": "current",
            "valid_from": "2026-07-14T00:00:00Z",
            "valid_to": None,
            "sensitivity": "project_private",
            "source_refs": [evidence_ref()],
        },
    )


def test_graph_node_schema_rejects_unknown_graph_namespace() -> None:
    with pytest.raises(ValidationError):
        validate(
            "graph-node.schema.json",
            {
                "schema_version": "graph-node/0.1",
                "id": "x",
                "graph": "everything_graph",
                "type": "Decision",
                "label": "x",
                "properties": {},
                "authority": "canonical",
                "confirmation_status": "human_confirmed",
                "status": "current",
                "valid_from": None,
                "valid_to": None,
                "sensitivity": "project_private",
                "source_refs": [],
            },
        )


def test_graph_edge_schema_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        validate(
            "graph-edge.schema.json",
            {
                "schema_version": "graph-edge/0.1",
                "id": "edge_1",
                "graph": "me_brain",
                "type": "SUPERSEDES",
                "from_id": "brain:decision:a",
                "to_id": "brain:decision:b",
                "properties": {},
                "authority": "canonical",
                "confirmation_status": "human_confirmed",
                "confidence": 1.2,
                "valid_from": None,
                "valid_to": None,
                "sensitivity": "project_private",
                "source_refs": [evidence_ref()],
            },
        )


def test_candidate_change_requires_evidence_and_payload() -> None:
    with pytest.raises(ValidationError):
        validate(
            "candidate-graph-change.schema.json",
            {
                "schema_version": "candidate-graph-change/0.1",
                "change_id": "change_1",
                "target_graph": "me_brain",
                "operation": "add_node",
                "submitted_by": "hermes-primary",
                "reason": "new decision found",
                "evidence_refs": [],
                "payload": {},
                "review_status": "pending",
            },
        )


def test_graph_slice_schema_accepts_nodes_edges_and_exclusions() -> None:
    validate(
        "graph-slice.schema.json",
        {
            "schema_version": "graph-slice/0.1",
            "slice_id": "slice_1",
            "graph": "me_brain",
            "as_of_time": "2026-07-23T00:00:00Z",
            "root_ids": ["brain:project:lighting-platform"],
            "summary": "lighting-platform 当前项目子图",
            "nodes": [],
            "edges": [],
            "evidence_handles": [evidence_ref()],
            "excluded": {"superseded": ["brain:decision:cycles-primary"], "unauthorized": []},
            "truncated": False,
        },
    )


def test_all_schema_documents_are_valid_draft_2020_12() -> None:
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_evidence_ref_schema_requires_source_anchor() -> None:
    with pytest.raises(ValidationError):
        validate("evidence-ref.schema.json", {"source_id": "src_1"})
