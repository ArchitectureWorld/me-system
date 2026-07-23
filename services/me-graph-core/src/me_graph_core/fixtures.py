from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from .contracts import GraphEdge, GraphNode
from .errors import ContractValidationError
from .store import GraphStore


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
    for value in nodes:
        if not isinstance(value, Mapping):
            raise ContractValidationError("every fixture node must be an object")
        store.add_node(GraphNode.from_dict(value))
    for value in edges:
        if not isinstance(value, Mapping):
            raise ContractValidationError("every fixture edge must be an object")
        store.add_edge(GraphEdge.from_dict(value))
