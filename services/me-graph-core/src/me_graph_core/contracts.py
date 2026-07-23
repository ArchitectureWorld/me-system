from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Sequence

from .errors import ContractValidationError


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class GraphNamespace(StrEnum):
    ME_BRAIN = "me_brain"
    ME_WHO = "me_who"
    BRIDGE = "bridge"


class AuthorityLevel(StrEnum):
    CANONICAL = "canonical"
    HUMAN_CONFIRMED = "human_confirmed"
    RULE_CONFIRMED = "rule_confirmed"
    CANDIDATE = "candidate"
    INFERENCE = "inference"
    RAW_EVIDENCE = "raw_evidence"


class ConfirmationStatus(StrEnum):
    HUMAN_CONFIRMED = "human_confirmed"
    RULE_CONFIRMED = "rule_confirmed"
    PENDING = "pending"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    OBSERVED = "observed"
    INFERRED = "inferred"


class TemporalStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"
    FUTURE_PLANNED = "future_planned"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    PROJECT_PRIVATE = "project_private"
    PERSONAL_PRIVATE = "personal_private"
    RESTRICTED = "restricted"


class ChangeOperation(StrEnum):
    ADD_NODE = "add_node"
    ADD_EDGE = "add_edge"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def _required_text(value: object, name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ContractValidationError(f"{name} must not be empty")
    return normalized


def _enum(value: object, enum_type: type[StrEnum], name: str) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ContractValidationError(f"{name} must be one of: {allowed}") from exc


def _datetime(value: object, name: str) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        result = value
    else:
        text = _required_text(value, name)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ContractValidationError(f"{name} must be an ISO-8601 datetime") from exc
    if result.tzinfo is None:
        raise ContractValidationError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def _datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_temporal(valid_from: datetime | None, valid_to: datetime | None) -> None:
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise ContractValidationError("valid_to must not be earlier than valid_from")


def _validate_authority(authority: AuthorityLevel, confirmation: ConfirmationStatus) -> None:
    if authority is AuthorityLevel.CANDIDATE and confirmation is not ConfirmationStatus.PENDING:
        raise ContractValidationError("candidate authority requires pending confirmation_status")
    if authority is AuthorityLevel.CANONICAL and confirmation not in {
        ConfirmationStatus.HUMAN_CONFIRMED,
        ConfirmationStatus.RULE_CONFIRMED,
    }:
        raise ContractValidationError("canonical authority requires confirmed confirmation_status")
    if authority is AuthorityLevel.HUMAN_CONFIRMED and confirmation is not ConfirmationStatus.HUMAN_CONFIRMED:
        raise ContractValidationError("human_confirmed authority requires human_confirmed confirmation_status")
    if authority is AuthorityLevel.RULE_CONFIRMED and confirmation is not ConfirmationStatus.RULE_CONFIRMED:
        raise ContractValidationError("rule_confirmed authority requires rule_confirmed confirmation_status")


def _graph_prefix(graph: GraphNamespace) -> str:
    if graph is GraphNamespace.ME_BRAIN:
        return "brain:"
    if graph is GraphNamespace.ME_WHO:
        return "who:"
    raise ContractValidationError("bridge is not a valid node graph")


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    source_id: str
    source_anchor: Mapping[str, object]
    document_id: str | None = None
    version_id: str | None = None
    content_fragment_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        anchor = dict(self.source_anchor)
        anchor_type = _required_text(anchor.get("type"), "source_anchor.type")
        anchor_value = anchor.get("value")
        if not isinstance(anchor_value, Mapping):
            raise ContractValidationError("source_anchor.value must be an object")
        object.__setattr__(self, "source_anchor", {"type": anchor_type, "value": dict(anchor_value)})
        for name in ("document_id", "version_id", "content_fragment_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required_text(value, name))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvidenceRef":
        return cls(
            source_id=data.get("source_id", ""),
            document_id=data.get("document_id") if data.get("document_id") is not None else None,
            version_id=data.get("version_id") if data.get("version_id") is not None else None,
            content_fragment_id=(
                data.get("content_fragment_id") if data.get("content_fragment_id") is not None else None
            ),
            source_anchor=data.get("source_anchor") if isinstance(data.get("source_anchor"), Mapping) else {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "content_fragment_id": self.content_fragment_id,
            "source_anchor": {
                "type": self.source_anchor["type"],
                "value": dict(self.source_anchor["value"]),
            },
        }


def _evidence_refs(values: Sequence[EvidenceRef | Mapping[str, object]]) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    for value in values:
        refs.append(value if isinstance(value, EvidenceRef) else EvidenceRef.from_dict(value))
    return tuple(refs)


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    graph: GraphNamespace
    type: str
    label: str
    properties: Mapping[str, object]
    authority: AuthorityLevel
    confirmation_status: ConfirmationStatus
    status: TemporalStatus
    valid_from: datetime | None
    valid_to: datetime | None
    sensitivity: Sensitivity
    source_refs: tuple[EvidenceRef, ...]

    SCHEMA_VERSION = "graph-node/0.1"

    def __post_init__(self) -> None:
        graph = _enum(self.graph, GraphNamespace, "graph")
        if graph is GraphNamespace.BRIDGE:
            raise ContractValidationError("bridge is not a valid node graph")
        object.__setattr__(self, "graph", graph)
        node_id = _required_text(self.id, "id")
        expected_prefix = _graph_prefix(graph)
        if not node_id.startswith(expected_prefix):
            raise ContractValidationError(f"{graph.value} node id must start with {expected_prefix}")
        object.__setattr__(self, "id", node_id)
        object.__setattr__(self, "type", _required_text(self.type, "type"))
        object.__setattr__(self, "label", _required_text(self.label, "label"))
        object.__setattr__(self, "properties", dict(self.properties))
        authority = _enum(self.authority, AuthorityLevel, "authority")
        confirmation = _enum(self.confirmation_status, ConfirmationStatus, "confirmation_status")
        _validate_authority(authority, confirmation)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "confirmation_status", confirmation)
        object.__setattr__(self, "status", _enum(self.status, TemporalStatus, "status"))
        valid_from = _datetime(self.valid_from, "valid_from")
        valid_to = _datetime(self.valid_to, "valid_to")
        _validate_temporal(valid_from, valid_to)
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_to", valid_to)
        object.__setattr__(self, "sensitivity", _enum(self.sensitivity, Sensitivity, "sensitivity"))
        refs = _evidence_refs(self.source_refs)
        if not refs:
            raise ContractValidationError("source_refs must contain at least one evidence reference")
        object.__setattr__(self, "source_refs", refs)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "GraphNode":
        refs = data.get("source_refs")
        return cls(
            id=data.get("id", ""),
            graph=data.get("graph", ""),
            type=data.get("type", ""),
            label=data.get("label", ""),
            properties=data.get("properties") if isinstance(data.get("properties"), Mapping) else {},
            authority=data.get("authority", ""),
            confirmation_status=data.get("confirmation_status", ""),
            status=data.get("status", ""),
            valid_from=data.get("valid_from"),
            valid_to=data.get("valid_to"),
            sensitivity=data.get("sensitivity", ""),
            source_refs=_evidence_refs(refs if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) else ()),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "id": self.id,
            "graph": self.graph.value,
            "type": self.type,
            "label": self.label,
            "properties": dict(self.properties),
            "authority": self.authority.value,
            "confirmation_status": self.confirmation_status.value,
            "status": self.status.value,
            "valid_from": _datetime_text(self.valid_from),
            "valid_to": _datetime_text(self.valid_to),
            "sensitivity": self.sensitivity.value,
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }

    def as_confirmed(self, *, reviewer_kind: str = "human") -> "GraphNode":
        if reviewer_kind == "rule":
            return replace(
                self,
                authority=AuthorityLevel.RULE_CONFIRMED,
                confirmation_status=ConfirmationStatus.RULE_CONFIRMED,
            )
        return replace(
            self,
            authority=AuthorityLevel.HUMAN_CONFIRMED,
            confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        )


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: str
    graph: GraphNamespace
    type: str
    from_id: str
    to_id: str
    properties: Mapping[str, object]
    authority: AuthorityLevel
    confirmation_status: ConfirmationStatus
    confidence: float
    valid_from: datetime | None
    valid_to: datetime | None
    sensitivity: Sensitivity
    source_refs: tuple[EvidenceRef, ...]

    SCHEMA_VERSION = "graph-edge/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        graph = _enum(self.graph, GraphNamespace, "graph")
        object.__setattr__(self, "graph", graph)
        object.__setattr__(self, "type", _required_text(self.type, "type"))
        from_id = _required_text(self.from_id, "from_id")
        to_id = _required_text(self.to_id, "to_id")
        if from_id == to_id:
            raise ContractValidationError("graph edges must not be self-loop relations")
        object.__setattr__(self, "from_id", from_id)
        object.__setattr__(self, "to_id", to_id)
        object.__setattr__(self, "properties", dict(self.properties))
        authority = _enum(self.authority, AuthorityLevel, "authority")
        confirmation = _enum(self.confirmation_status, ConfirmationStatus, "confirmation_status")
        _validate_authority(authority, confirmation)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "confirmation_status", confirmation)
        confidence = float(self.confidence)
        if not 0 <= confidence <= 1:
            raise ContractValidationError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        valid_from = _datetime(self.valid_from, "valid_from")
        valid_to = _datetime(self.valid_to, "valid_to")
        _validate_temporal(valid_from, valid_to)
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_to", valid_to)
        object.__setattr__(self, "sensitivity", _enum(self.sensitivity, Sensitivity, "sensitivity"))
        refs = _evidence_refs(self.source_refs)
        if not refs:
            raise ContractValidationError("source_refs must contain at least one evidence reference")
        object.__setattr__(self, "source_refs", refs)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "GraphEdge":
        refs = data.get("source_refs")
        return cls(
            id=data.get("id", ""),
            graph=data.get("graph", ""),
            type=data.get("type", ""),
            from_id=data.get("from_id", ""),
            to_id=data.get("to_id", ""),
            properties=data.get("properties") if isinstance(data.get("properties"), Mapping) else {},
            authority=data.get("authority", ""),
            confirmation_status=data.get("confirmation_status", ""),
            confidence=data.get("confidence", 0),
            valid_from=data.get("valid_from"),
            valid_to=data.get("valid_to"),
            sensitivity=data.get("sensitivity", ""),
            source_refs=_evidence_refs(refs if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) else ()),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "id": self.id,
            "graph": self.graph.value,
            "type": self.type,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "properties": dict(self.properties),
            "authority": self.authority.value,
            "confirmation_status": self.confirmation_status.value,
            "confidence": self.confidence,
            "valid_from": _datetime_text(self.valid_from),
            "valid_to": _datetime_text(self.valid_to),
            "sensitivity": self.sensitivity.value,
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }

    def as_confirmed(self, *, reviewer_kind: str = "human") -> "GraphEdge":
        if reviewer_kind == "rule":
            return replace(
                self,
                authority=AuthorityLevel.RULE_CONFIRMED,
                confirmation_status=ConfirmationStatus.RULE_CONFIRMED,
            )
        return replace(
            self,
            authority=AuthorityLevel.HUMAN_CONFIRMED,
            confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        )


@dataclass(frozen=True, slots=True)
class CandidateGraphChange:
    change_id: str
    target_graph: GraphNamespace
    operation: ChangeOperation
    submitted_by: str
    reason: str
    evidence_refs: tuple[EvidenceRef, ...]
    payload: Mapping[str, object]
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: str | None = None
    review_reason: str | None = None

    SCHEMA_VERSION = "candidate-graph-change/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "change_id", _required_text(self.change_id, "change_id"))
        target_graph = _enum(self.target_graph, GraphNamespace, "target_graph")
        object.__setattr__(self, "target_graph", target_graph)
        operation = _enum(self.operation, ChangeOperation, "operation")
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "submitted_by", _required_text(self.submitted_by, "submitted_by"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        refs = _evidence_refs(self.evidence_refs)
        if not refs:
            raise ContractValidationError("evidence_refs must contain at least one evidence reference")
        object.__setattr__(self, "evidence_refs", refs)
        payload = dict(self.payload)
        if not payload:
            raise ContractValidationError("payload must not be empty")
        object.__setattr__(self, "payload", payload)
        review_status = _enum(self.review_status, ReviewStatus, "review_status")
        object.__setattr__(self, "review_status", review_status)
        if review_status is ReviewStatus.PENDING and (self.reviewed_by or self.review_reason):
            raise ContractValidationError("pending changes must not include review metadata")
        materialized = self.materialize()
        if materialized.graph is not target_graph:
            raise ContractValidationError("payload graph must match target_graph")
        if operation is ChangeOperation.ADD_NODE and target_graph is GraphNamespace.BRIDGE:
            raise ContractValidationError("bridge graph cannot contain nodes")
        if materialized.authority is not AuthorityLevel.CANDIDATE:
            raise ContractValidationError("candidate payload authority must be candidate")
        if materialized.confirmation_status is not ConfirmationStatus.PENDING:
            raise ContractValidationError("candidate payload confirmation_status must be pending")

    def materialize(self) -> GraphNode | GraphEdge:
        if self.operation is ChangeOperation.ADD_NODE:
            return GraphNode.from_dict(self.payload)
        if self.operation is ChangeOperation.ADD_EDGE:
            return GraphEdge.from_dict(self.payload)
        raise ContractValidationError(f"unsupported operation: {self.operation}")

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CandidateGraphChange":
        refs = data.get("evidence_refs")
        return cls(
            change_id=data.get("change_id", ""),
            target_graph=data.get("target_graph", ""),
            operation=data.get("operation", ""),
            submitted_by=data.get("submitted_by", ""),
            reason=data.get("reason", ""),
            evidence_refs=_evidence_refs(refs if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) else ()),
            payload=data.get("payload") if isinstance(data.get("payload"), Mapping) else {},
            review_status=data.get("review_status", ReviewStatus.PENDING.value),
            reviewed_by=data.get("reviewed_by") if data.get("reviewed_by") is not None else None,
            review_reason=data.get("review_reason") if data.get("review_reason") is not None else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "change_id": self.change_id,
            "target_graph": self.target_graph.value,
            "operation": self.operation.value,
            "submitted_by": self.submitted_by,
            "reason": self.reason,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "payload": dict(self.payload),
            "review_status": self.review_status.value,
            "reviewed_by": self.reviewed_by,
            "review_reason": self.review_reason,
        }


@dataclass(frozen=True, slots=True)
class GraphSlice:
    slice_id: str
    graph: GraphNamespace
    as_of_time: datetime | None
    root_ids: tuple[str, ...]
    summary: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    evidence_handles: tuple[EvidenceRef, ...]
    excluded: Mapping[str, Sequence[str]] = field(default_factory=lambda: {"superseded": (), "unauthorized": ()})
    truncated: bool = False

    SCHEMA_VERSION = "graph-slice/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "slice_id", _required_text(self.slice_id, "slice_id"))
        object.__setattr__(self, "graph", _enum(self.graph, GraphNamespace, "graph"))
        object.__setattr__(self, "as_of_time", _datetime(self.as_of_time, "as_of_time"))
        object.__setattr__(self, "root_ids", tuple(_required_text(value, "root_id") for value in self.root_ids))
        object.__setattr__(self, "summary", str(self.summary))
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "evidence_handles", _evidence_refs(self.evidence_handles))
        normalized_excluded = {
            "superseded": tuple(self.excluded.get("superseded", ())),
            "unauthorized": tuple(self.excluded.get("unauthorized", ())),
        }
        object.__setattr__(self, "excluded", normalized_excluded)
        object.__setattr__(self, "truncated", bool(self.truncated))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "slice_id": self.slice_id,
            "graph": self.graph.value,
            "as_of_time": _datetime_text(self.as_of_time),
            "root_ids": list(self.root_ids),
            "summary": self.summary,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "evidence_handles": [ref.to_dict() for ref in self.evidence_handles],
            "excluded": {
                "superseded": list(self.excluded["superseded"]),
                "unauthorized": list(self.excluded["unauthorized"]),
            },
            "truncated": self.truncated,
        }
