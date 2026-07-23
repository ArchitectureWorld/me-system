from __future__ import annotations

from typing import Iterable, Literal, Protocol, runtime_checkable

from .contracts import GraphEdge, GraphNamespace, GraphNode
from .errors import (
    DuplicateGraphObjectError,
    GraphNamespaceError,
    GraphObjectNotFoundError,
)


Direction = Literal["in", "out", "both"]


@runtime_checkable
class GraphStore(Protocol):
    def add_node(self, node: GraphNode) -> None: ...

    def add_edge(self, edge: GraphEdge) -> None: ...

    def get_node(self, node_id: str) -> GraphNode: ...

    def get_edge(self, edge_id: str) -> GraphEdge: ...

    def get_object(self, object_id: str) -> GraphNode | GraphEdge: ...

    def list_nodes(self, graph: GraphNamespace | None = None) -> tuple[GraphNode, ...]: ...

    def list_edges(self, graph: GraphNamespace | None = None) -> tuple[GraphEdge, ...]: ...

    def neighbors(
        self,
        node_id: str,
        edge_types: set[str] | None = None,
        direction: Direction = "both",
    ) -> tuple[GraphEdge, ...]: ...


class InMemoryGraphStore:
    """Small deterministic store used for contracts, fixtures, and adapter tests."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

    def add_node(self, node: GraphNode) -> None:
        if node.id in self._nodes or node.id in self._edges:
            raise DuplicateGraphObjectError(f"graph object already exists: {node.id}")
        self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.id in self._edges or edge.id in self._nodes:
            raise DuplicateGraphObjectError(f"graph object already exists: {edge.id}")
        from_node = self.get_node(edge.from_id)
        to_node = self.get_node(edge.to_id)
        self._validate_edge_namespace(edge, from_node, to_node)
        self._edges[edge.id] = edge

    @staticmethod
    def _validate_edge_namespace(edge: GraphEdge, from_node: GraphNode, to_node: GraphNode) -> None:
        if edge.graph is GraphNamespace.BRIDGE:
            if from_node.graph is to_node.graph:
                raise GraphNamespaceError("bridge edges must connect different canonical graphs")
            return
        if from_node.graph is not edge.graph or to_node.graph is not edge.graph:
            raise GraphNamespaceError(
                "cross-graph relations must use the explicit bridge namespace"
            )

    def get_node(self, node_id: str) -> GraphNode:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise GraphObjectNotFoundError(f"node not found: {node_id}") from exc

    def get_edge(self, edge_id: str) -> GraphEdge:
        try:
            return self._edges[edge_id]
        except KeyError as exc:
            raise GraphObjectNotFoundError(f"edge not found: {edge_id}") from exc

    def get_object(self, object_id: str) -> GraphNode | GraphEdge:
        if object_id in self._nodes:
            return self._nodes[object_id]
        if object_id in self._edges:
            return self._edges[object_id]
        raise GraphObjectNotFoundError(f"graph object not found: {object_id}")

    def list_nodes(self, graph: GraphNamespace | None = None) -> tuple[GraphNode, ...]:
        values: Iterable[GraphNode] = self._nodes.values()
        if graph is not None:
            values = (node for node in values if node.graph is graph)
        return tuple(sorted(values, key=lambda node: node.id))

    def list_edges(self, graph: GraphNamespace | None = None) -> tuple[GraphEdge, ...]:
        values: Iterable[GraphEdge] = self._edges.values()
        if graph is not None:
            values = (edge for edge in values if edge.graph is graph)
        return tuple(sorted(values, key=lambda edge: edge.id))

    def neighbors(
        self,
        node_id: str,
        edge_types: set[str] | None = None,
        direction: Direction = "both",
    ) -> tuple[GraphEdge, ...]:
        self.get_node(node_id)
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be one of: in, out, both")
        matches: list[GraphEdge] = []
        for edge in self._edges.values():
            if edge_types is not None and edge.type not in edge_types:
                continue
            if direction in {"out", "both"} and edge.from_id == node_id:
                matches.append(edge)
                continue
            if direction in {"in", "both"} and edge.to_id == node_id:
                matches.append(edge)
        return tuple(sorted(matches, key=lambda edge: edge.id))
