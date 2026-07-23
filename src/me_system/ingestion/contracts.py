from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Mapping, Sequence

from .._validation import (
    aware_datetime,
    canonical_sha256,
    datetime_text,
    enum_value,
    mapping_copy,
    nonnegative_int,
    optional_text,
    required_text,
    sha256_text,
)
from ..contracts import CandidateGraphChange, EvidenceRef, ReviewStatus
from ..errors import ContractValidationError, IngestionStateError


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ReviewEventType(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActorKind(StrEnum):
    ADAPTER = "adapter"
    AGENT = "agent"
    HUMAN = "human"
    RULE = "rule"


_TERMINAL_INGESTION = {
    IngestionStatus.COMPLETED,
    IngestionStatus.PARTIAL,
    IngestionStatus.FAILED,
}


def _evidence_refs(values: object) -> tuple[EvidenceRef, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ContractValidationError("evidence_refs must be an array")
    return tuple(
        value if isinstance(value, EvidenceRef) else EvidenceRef.from_dict(value)
        for value in values
        if isinstance(value, (EvidenceRef, Mapping))
    )


@dataclass(frozen=True, slots=True)
class IngestionRun:
    run_id: str
    source_id: str
    adapter_name: str
    adapter_version: str
    status: IngestionStatus
    started_at: datetime
    completed_at: datetime | None
    input_item_count: int
    processed_item_count: int
    skipped_item_count: int
    failed_item_count: int
    fragment_count: int
    candidate_count: int
    coverage_ratio: float
    quality_report: Mapping[str, object]
    log_ref: str | None
    error_summary: str | None

    SCHEMA_VERSION = "ingestion-run/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", required_text(self.run_id, "run_id"))
        object.__setattr__(self, "source_id", required_text(self.source_id, "source_id"))
        object.__setattr__(self, "adapter_name", required_text(self.adapter_name, "adapter_name"))
        object.__setattr__(
            self,
            "adapter_version",
            required_text(self.adapter_version, "adapter_version"),
        )
        status = enum_value(self.status, IngestionStatus, "status")
        object.__setattr__(self, "status", status)
        started_at = aware_datetime(self.started_at, "started_at", required=True)
        assert started_at is not None
        completed_at = aware_datetime(self.completed_at, "completed_at")
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "completed_at", completed_at)

        count_names = (
            "input_item_count",
            "processed_item_count",
            "skipped_item_count",
            "failed_item_count",
            "fragment_count",
            "candidate_count",
        )
        for name in count_names:
            object.__setattr__(self, name, nonnegative_int(getattr(self, name), name))
        handled = self.processed_item_count + self.skipped_item_count + self.failed_item_count
        if handled > self.input_item_count:
            raise ContractValidationError(
                "ingestion counts must not exceed input_item_count"
            )
        try:
            coverage = float(self.coverage_ratio)
        except (TypeError, ValueError) as exc:
            raise ContractValidationError("coverage_ratio must be numeric") from exc
        if not 0 <= coverage <= 1:
            raise ContractValidationError("coverage_ratio must be between 0 and 1")
        object.__setattr__(self, "coverage_ratio", coverage)
        object.__setattr__(
            self,
            "quality_report",
            mapping_copy(self.quality_report, "quality_report"),
        )
        object.__setattr__(self, "log_ref", optional_text(self.log_ref, "log_ref"))
        object.__setattr__(
            self,
            "error_summary",
            optional_text(self.error_summary, "error_summary"),
        )
        if status in _TERMINAL_INGESTION and completed_at is None:
            raise ContractValidationError(
                "completed_at is required for terminal ingestion status"
            )
        if status not in _TERMINAL_INGESTION and completed_at is not None:
            raise ContractValidationError(
                "completed_at is only allowed for terminal ingestion status"
            )
        if completed_at is not None and completed_at < started_at:
            raise ContractValidationError("completed_at must not precede started_at")

    def start(self) -> "IngestionRun":
        if self.status is not IngestionStatus.PENDING:
            raise IngestionStateError("only pending ingestion runs can start")
        return replace(self, status=IngestionStatus.RUNNING)

    def finish(
        self,
        *,
        status: IngestionStatus,
        completed_at: datetime,
        input_item_count: int,
        processed_item_count: int,
        skipped_item_count: int,
        failed_item_count: int,
        fragment_count: int,
        candidate_count: int,
        coverage_ratio: float,
        quality_report: Mapping[str, object],
        log_ref: str | None = None,
        error_summary: str | None = None,
    ) -> "IngestionRun":
        if self.status is not IngestionStatus.RUNNING:
            raise IngestionStateError("only running ingestion runs can finish")
        terminal = enum_value(status, IngestionStatus, "status")
        if terminal not in _TERMINAL_INGESTION:
            raise IngestionStateError("finished ingestion status must be terminal")
        return replace(
            self,
            status=terminal,
            completed_at=completed_at,
            input_item_count=input_item_count,
            processed_item_count=processed_item_count,
            skipped_item_count=skipped_item_count,
            failed_item_count=failed_item_count,
            fragment_count=fragment_count,
            candidate_count=candidate_count,
            coverage_ratio=coverage_ratio,
            quality_report=quality_report,
            log_ref=log_ref,
            error_summary=error_summary,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IngestionRun":
        return cls(
            run_id=data.get("run_id", ""),
            source_id=data.get("source_id", ""),
            adapter_name=data.get("adapter_name", ""),
            adapter_version=data.get("adapter_version", ""),
            status=data.get("status", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            input_item_count=data.get("input_item_count", 0),
            processed_item_count=data.get("processed_item_count", 0),
            skipped_item_count=data.get("skipped_item_count", 0),
            failed_item_count=data.get("failed_item_count", 0),
            fragment_count=data.get("fragment_count", 0),
            candidate_count=data.get("candidate_count", 0),
            coverage_ratio=data.get("coverage_ratio", 0),
            quality_report=(
                data.get("quality_report")
                if isinstance(data.get("quality_report"), Mapping)
                else {}
            ),
            log_ref=data.get("log_ref"),
            error_summary=data.get("error_summary"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": self.run_id,
            "source_id": self.source_id,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "status": self.status.value,
            "started_at": datetime_text(self.started_at),
            "completed_at": datetime_text(self.completed_at),
            "input_item_count": self.input_item_count,
            "processed_item_count": self.processed_item_count,
            "skipped_item_count": self.skipped_item_count,
            "failed_item_count": self.failed_item_count,
            "fragment_count": self.fragment_count,
            "candidate_count": self.candidate_count,
            "coverage_ratio": self.coverage_ratio,
            "quality_report": mapping_copy(self.quality_report, "quality_report"),
            "log_ref": self.log_ref,
            "error_summary": self.error_summary,
        }


@dataclass(frozen=True, slots=True)
class CandidateGraphChangeRecord:
    change: CandidateGraphChange
    idempotency_key: str
    payload_sha256: str
    created_at: datetime
    reviewed_at: datetime | None = None
    approved_object_id: str | None = None
    ingestion_run_id: str | None = None

    SCHEMA_VERSION = "candidate-graph-change-record/0.1"

    def __post_init__(self) -> None:
        if not isinstance(self.change, CandidateGraphChange):
            raise ContractValidationError("change must be a CandidateGraphChange")
        object.__setattr__(
            self,
            "idempotency_key",
            required_text(self.idempotency_key, "idempotency_key"),
        )
        expected_hash = canonical_sha256(dict(self.change.payload))
        provided_hash = sha256_text(self.payload_sha256, "payload_sha256")
        if provided_hash != expected_hash:
            raise ContractValidationError(
                "payload_sha256 does not match the canonical candidate payload"
            )
        object.__setattr__(self, "payload_sha256", provided_hash)
        created_at = aware_datetime(self.created_at, "created_at", required=True)
        assert created_at is not None
        reviewed_at = aware_datetime(self.reviewed_at, "reviewed_at")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "reviewed_at", reviewed_at)
        object.__setattr__(
            self,
            "approved_object_id",
            optional_text(self.approved_object_id, "approved_object_id"),
        )
        object.__setattr__(
            self,
            "ingestion_run_id",
            optional_text(self.ingestion_run_id, "ingestion_run_id"),
        )
        status = self.change.review_status
        if status is ReviewStatus.PENDING:
            if reviewed_at is not None or self.approved_object_id is not None:
                raise ContractValidationError(
                    "pending candidate records must not include review metadata"
                )
        elif status is ReviewStatus.APPROVED:
            if reviewed_at is None or not self.change.reviewed_by or not self.approved_object_id:
                raise ContractValidationError(
                    "approved candidate records require reviewer, reviewed_at, and approved_object_id"
                )
        elif status is ReviewStatus.REJECTED:
            if reviewed_at is None or not self.change.reviewed_by or not self.change.review_reason:
                raise ContractValidationError(
                    "rejected candidate records require reviewer, reason, and reviewed_at"
                )
            if self.approved_object_id is not None:
                raise ContractValidationError(
                    "rejected candidate records must not include approved_object_id"
                )

    @classmethod
    def from_change(
        cls,
        change: CandidateGraphChange,
        *,
        idempotency_key: str,
        created_at: datetime,
        reviewed_at: datetime | None = None,
        approved_object_id: str | None = None,
        ingestion_run_id: str | None = None,
    ) -> "CandidateGraphChangeRecord":
        return cls(
            change=change,
            idempotency_key=idempotency_key,
            payload_sha256=canonical_sha256(dict(change.payload)),
            created_at=created_at,
            reviewed_at=reviewed_at,
            approved_object_id=approved_object_id,
            ingestion_run_id=ingestion_run_id,
        )

    def submission_fingerprint(self) -> str:
        return canonical_sha256(
            {
                "target_graph": self.change.target_graph.value,
                "operation": self.change.operation.value,
                "submitted_by": self.change.submitted_by,
                "reason": self.change.reason,
                "evidence_refs": [ref.to_dict() for ref in self.change.evidence_refs],
                "payload": dict(self.change.payload),
                "ingestion_run_id": self.ingestion_run_id,
            }
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CandidateGraphChangeRecord":
        change_data = data.get("change")
        if not isinstance(change_data, Mapping):
            change_data = {
                key: data.get(key)
                for key in (
                    "change_id",
                    "target_graph",
                    "operation",
                    "submitted_by",
                    "reason",
                    "evidence_refs",
                    "payload",
                    "review_status",
                    "reviewed_by",
                    "review_reason",
                )
            }
        return cls(
            change=CandidateGraphChange.from_dict(change_data),
            idempotency_key=data.get("idempotency_key", ""),
            payload_sha256=data.get("payload_sha256", ""),
            created_at=data.get("created_at"),
            reviewed_at=data.get("reviewed_at"),
            approved_object_id=data.get("approved_object_id"),
            ingestion_run_id=data.get("ingestion_run_id"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "change": self.change.to_dict(),
            "idempotency_key": self.idempotency_key,
            "payload_sha256": self.payload_sha256,
            "created_at": datetime_text(self.created_at),
            "reviewed_at": datetime_text(self.reviewed_at),
            "approved_object_id": self.approved_object_id,
            "ingestion_run_id": self.ingestion_run_id,
        }


@dataclass(frozen=True, slots=True)
class CandidateReviewEvent:
    event_id: str
    change_id: str
    event_type: ReviewEventType
    actor_id: str
    actor_kind: ActorKind
    reason: str
    created_at: datetime
    metadata: Mapping[str, object]

    SCHEMA_VERSION = "candidate-review-event/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", required_text(self.event_id, "event_id"))
        object.__setattr__(self, "change_id", required_text(self.change_id, "change_id"))
        object.__setattr__(
            self,
            "event_type",
            enum_value(self.event_type, ReviewEventType, "event_type"),
        )
        object.__setattr__(self, "actor_id", required_text(self.actor_id, "actor_id"))
        object.__setattr__(
            self,
            "actor_kind",
            enum_value(self.actor_kind, ActorKind, "actor_kind"),
        )
        object.__setattr__(self, "reason", required_text(self.reason, "reason"))
        created_at = aware_datetime(self.created_at, "created_at", required=True)
        assert created_at is not None
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "metadata", mapping_copy(self.metadata, "metadata"))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CandidateReviewEvent":
        return cls(
            event_id=data.get("event_id", ""),
            change_id=data.get("change_id", ""),
            event_type=data.get("event_type", ""),
            actor_id=data.get("actor_id", ""),
            actor_kind=data.get("actor_kind", ""),
            reason=data.get("reason", ""),
            created_at=data.get("created_at"),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": self.event_id,
            "change_id": self.change_id,
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "actor_kind": self.actor_kind.value,
            "reason": self.reason,
            "created_at": datetime_text(self.created_at),
            "metadata": mapping_copy(self.metadata, "metadata"),
        }
