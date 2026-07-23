from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from .contracts import GraphEdge, GraphNode
from .errors import ContractValidationError
from .store import GraphStore


def _full_evidence(defaults: Mapping[str, object], anchor: str) -> list[dict[str, object]]:
    source = defaults.get("source")
    if not isinstance(source, Mapping):
        raise ContractValidationError("compact graph fixture defaults.source must be an object")
    return [
        {
            "source_id": source.get("source_id"),
            "document_id": source.get("document_id"),
            "version_id": source.get("version_id"),
            "content_fragment_id": f"fragment:{anchor}",
            "source_anchor": {
                "type": source.get("anchor_type", "conversation_message"),
                "value": {"message_id": anchor},
            },
        }
    ]


def _expand_node(record: Mapping[str, object], defaults: Mapping[str, object]) -> dict[str, object]:
    graph = record.get("graph")
    sensitivity_key = "brain_sensitivity" if graph == "me_brain" else "who_sensitivity"
    return {
        "schema_version": "graph-node/0.1",
        "id": record.get("id"),
        "graph": graph,
        "type": record.get("type"),
        "label": record.get("label"),
        "properties": record.get("properties", {}),
        "authority": record.get("authority", defaults.get("authority", "canonical")),
        "confirmation_status": record.get(
            "confirmation_status", defaults.get("confirmation_status", "human_confirmed")
        ),
        "status": record.get("status", "current"),
        "valid_from": record.get("valid_from", defaults.get("valid_from")),
        "valid_to": record.get("valid_to"),
        "sensitivity": record.get("sensitivity", defaults.get(sensitivity_key)),
        "source_refs": _full_evidence(defaults, str(record.get("anchor") or record.get("id"))),
    }


def _expand_edge(record: Mapping[str, object], defaults: Mapping[str, object]) -> dict[str, object]:
    graph = record.get("graph")
    if graph == "bridge":
        sensitivity = "restricted"
    elif graph == "me_who":
        sensitivity = defaults.get("who_sensitivity")
    else:
        sensitivity = defaults.get("brain_sensitivity")
    return {
        "schema_version": "graph-edge/0.1",
        "id": record.get("id"),
        "graph": graph,
        "type": record.get("type"),
        "from_id": record.get("from_id"),
        "to_id": record.get("to_id"),
        "properties": record.get("properties", {}),
        "authority": record.get("authority", defaults.get("authority", "canonical")),
        "confirmation_status": record.get(
            "confirmation_status", defaults.get("confirmation_status", "human_confirmed")
        ),
        "confidence": record.get("confidence", 1.0),
        "valid_from": record.get("valid_from", defaults.get("valid_from")),
        "valid_to": record.get("valid_to"),
        "sensitivity": record.get("sensitivity", sensitivity),
        "source_refs": _full_evidence(defaults, str(record.get("anchor") or record.get("id"))),
    }


def load_graph_fixture(path: Path, store: GraphStore) -> None:
    fixture_path = Path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"unable to read graph fixture {fixture_path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ContractValidationError("graph fixture root must be an object")
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
        raise ContractValidationError("graph fixture nodes must be an array")
    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        raise ContractValidationError("graph fixture edges must be an array")
    compact = payload.get("schema_version") == "graph-fixture-compact/0.1"
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), Mapping) else {}
    for value in nodes:
        if not isinstance(value, Mapping):
            raise ContractValidationError("every fixture node must be an object")
        data = _expand_node(value, defaults) if compact else dict(value)
        store.add_node(GraphNode.from_dict(data))
    for value in edges:
        if not isinstance(value, Mapping):
            raise ContractValidationError("every fixture edge must be an object")
        data = _expand_edge(value, defaults) if compact else dict(value)
        store.add_edge(GraphEdge.from_dict(data))
