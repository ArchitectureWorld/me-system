from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Mapping

from ..contracts import CandidateGraphChange, GraphNamespace, ReviewStatus
from ..errors import ContractValidationError


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FINAL_STATUSES = {"completed", "partial", "failed"}
_ACTIVE_STATUSES = {"pending", "running"}


class IngestionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class ReviewEventType(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return self.value


class ActorKind(str, Enum):
    ADAPTER = "adapter"
    AGENT = "agent"
    HUMAN = "human"
    RULE = "rule"

    def __str__(self) -> str:
        return self.value


def _required_text(value: object, name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ContractValidationError(f"{name} must not be empty")
    return text


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _aware_datetime(value: object, name: str, *, required: bool) -> datetime | None:
    if value is None or value == "":
        if required:
            raise ContractValidationError(f"{name} must not be empty")
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


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{name} must be an object")
    return dict(value)


def _enum(value: object, enum_type: type[Enum], name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(str(item.value) for item in enum_type)
        raise ContractValidationError(f"{name} must be one of: {allowed}") from exc


def _nonnegative(value: object, name: str) -> int:
    number = int(value)
    if number < 0:
        raise ContractValidationError(f"{name} must be zero or greater")
    return number


def _coverage(value: object) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise ContractValidationError("coverage_ratio must be between 0 and 1")
    return number


def _sha256(value: object, name: str) -> str:
    text = _required_text(value, name).lower()
    if not _SHA256_RE.fullmatch(text):
        raise ContractValidationError(f"{name} must be a 64-character lowercase SHA-256 hex digest")
    return text


def candidate_payload_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class IngestionResult:
    status: IngestionStatus
    completed_at: datetime
    processed_item_count: int
    skipped_item_count: int
    failed_item_count: int
    fragment_count: int
    candidate_count: int
    coverage_ratio: float
    quality_report: Mapping[str, object]
    log_ref: str | None = None
    error_summary: str | None = None

    def __post_init__(self) -> None:
        status = _enum(self.status, IngestionStatus, "status")
        if status.value not in _FINAL_STATUSES:
            raise ContractValidationError("IngestionResult status must be completed, partial, or failed")
        object.__setattr__(self, "status", status)
        completed_at = _aware_datetime(self.completed_at, "completed_at", required=True)
        assert completed_at is not None
        object.__setattr__(self, "completed_at", completed_at)
        for name in (
            "processed_item_count",
            "skipped_item_count",
            "failed_item_count",
            "fragment_count",
            "candidate_count",
        ):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name))
        object.__setattr__(self, "coverage_ratio", _coverage(self.coverage_ratio))
        object.__setattr__(self, "quality_report", _mapping(self.quality_report, "quality_report"))
        object.__setattr__(self, "log_ref", _optional_text(self.log_ref, "log_ref"))
        object.__setattr__(self, "error_summary", _optional_text(self.error_summary, "error_summary"))


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
    log_ref: str | None = None
    error_summary: str | None = None

    SCHEMA_VERSION = "ingestion-run/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "adapter_name", _required_text(self.adapter_name, "adapter_name"))
        object.__setattr__(self, "adapter_version", _required_text(self.adapter_version, "adapter_version"))
        status = _enum(self.status, IngestionStatus, "status")
        object.__setattr__(self, "status", status)
        started_at = _aware_datetime(self.started_at, "started_at", required=True)
        assert started_at is not None
        object.__setattr__(self, "started_at", started_at)
        completed_at = _aware_datetime(self.completed_at, "completed_at", required=False)
        object.__setattr__(self, "completed_at", completed_at)
        if status.value in _FINAL_STATUSES and completed_at is None:
            raise ContractValidationError("completed_at is required for a final ingestion status")
        if status.value in _ACTIVE_STATUSES and completed_at is not None:
            raise ContractValidationError("completed_at must be empty for pending or running ingestion")
        if completed_at is not None and completed_at < started_at:
            raise ContractValidationError("completed_at must not be earlier than started_at")
        for name in (
            "input_item_count",
            "processed_item_count",
            "skipped_item_count",
            "failed_item_count",
            "fragment_count",
            "candidate_count",
        ):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name))
        accounted = self.processed_item_count + self.skipped_item_count + self.failed_item_count
        if accounted > self.input_item_count:
            raise ContractValidationError(
                "processed_item_count + skipped_item_count + failed_item_count "
                "must not exceed input_item_count"
            )
        object.__setattr__(self, "coverage_ratio", _coverage(self.coverage_ratio))
        object.__setattr__(self, "quality_report", _mapping(self.quality_report, "quality_report"))
        object.__setattr__(self, "log_ref", _optional_text(self.log_ref, "log_ref"))
        object.__setattr__(self, "error_summary", _optional_text(self.error_summary, "error_summary"))

    @classmethod
    def new(
        cls,
        *,
        run_id: str,
        source_id: str,
        adapter_name: str,
        adapter_version: str,
        started_at: datetime,
        input_item_count: int,
    ) -> "IngestionRun":
        return cls(
            run_id=run_id,
            source_id=source_id,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            status=IngestionStatus.PENDING,
            started_at=started_at,
            completed_at=None,
            input_item_count=input_item_count,
            processed_item_count=0,
            skipped_item_count=0,
            failed_item_count=0,
            fragment_count=0,
            candidate_count=0,
            coverage_ratio=0,
            quality_report={},
            log_ref=None,
            error_summary=None,
        )

    def as_running(self) -> "IngestionRun":
        if self.status is not IngestionStatus.PENDING:
            raise ContractValidationError("only a pending ingestion run can start")
        return replace(self, status=IngestionStatus.RUNNING)

    def complete(self, result: IngestionResult) -> "IngestionRun":
        if self.status not in {IngestionStatus.PENDING, IngestionStatus.RUNNING}:
            raise ContractValidationError("only an active ingestion run can complete")
        accounted = result.processed_item_count + result.skipped_item_count + result.failed_item_count
        if accounted > self.input_item_count:
            raise ContractValidationError("ingestion result counts must not exceed input_item_count")
        return replace(
            self,
            status=result.status,
            completed_at=result.completed_at,
            processed_item_count=result.processed_item_count,
            skipped_item_count=result.skipped_item_count,
            failed_item_count=result.failed_item_count,
            fragment_count=result.fragment_count,
            candidate_count=result.candidate_count,
            coverage_ratio=result.coverage_ratio,
            quality_report=dict(result.quality_report),
            log_ref=result.log_ref,
            error_summary=result.error_summary,
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
            quality_report=data.get("quality_report") if isinstance(data.get("quality_report"), Mapping) else {},
            log_ref=data.get("log_ref") if data.get("log_ref") is not None else None,
            error_summary=data.get("error_summary") if data.get("error_summary") is not None else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": self.run_id,
            "source_id": self.source_id,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "status": self.status.value,
            "started_at": _datetime_text(self.started_at),
            "completed_at": _datetime_text(self.completed_at),
            "input_item_count": self.input_item_count,
            "processed_item_count": self.processed_item_count,
            "skipped_item_count": self.skipped_item_count,
            "failed_item_count": self.failed_item_count,
            "fragment_count": self.fragment_count,
            "candidate_count": self.candidate_count,
            "coverage_ratio": self.coverage_ratio,
            "quality_report": dict(self.quality_report),
            "log_ref": self.log_ref,
            "error_summary": self.error_summary,
        }


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    change: CandidateGraphChange
    idempotency_key: str
    payload_sha256: str
    created_at: datetime
    reviewed_at: datetime | None
    approved_object_id: str | None
    ingestion_run_id: str | None

    SCHEMA_VERSION = "candidate-record/0.1"

    def __post_init__(self) -> None:
        if not isinstance(self.change, CandidateGraphChange):
            raise ContractValidationError("change must be a CandidateGraphChange")
        object.__setattr__(self, "idempotency_key", _required_text(self.idempotency_key, "idempotency_key"))
        payload_hash = _sha256(self.payload_sha256, "payload_sha256")
        expected = candidate_payload_sha256(self.change.payload)
        if payload_hash != expected:
            raise ContractValidationError("payload_sha256 does not match the candidate payload")
        object.__setattr__(self, "payload_sha256", payload_hash)
        created_at = _aware_datetime(self.created_at, "created_at", required=True)
        assert created_at is not None
        object.__setattr__(self, "created_at", created_at)
        reviewed_at = _aware_datetime(self.reviewed_at, "reviewed_at", required=False)
        object.__setattr__(self, "reviewed_at", reviewed_at)
        object.__setattr__(self, "approved_object_id", _optional_text(self.approved_object_id, "approved_object_id"))
        object.__setattr__(self, "ingestion_run_id", _optional_text(self.ingestion_run_id, "ingestion_run_id"))
        status = self.change.review_status
        if status is ReviewStatus.PENDING:
            if reviewed_at is not None or self.approved_object_id is not None:
                raise ContractValidationError("pending candidates must not include reviewed_at or approved_object_id")
        elif status is ReviewStatus.APPROVED:
            if reviewed_at is None or self.approved_object_id is None:
                raise ContractValidationError("approved candidates require reviewed_at and approved_object_id")
        elif status is ReviewStatus.REJECTED:
            if reviewed_at is None or self.approved_object_id is not None:
                raise ContractValidationError("rejected candidates require reviewed_at and no approved_object_id")
        if reviewed_at is not None and reviewed_at < created_at:
            raise ContractValidationError("reviewed_at must not be earlier than created_at")

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CandidateRecord":
        change_data = data.get("change")
        if not isinstance(change_data, Mapping):
            raise ContractValidationError("change must be an object")
        return cls(
            change=CandidateGraphChange.from_dict(change_data),
            idempotency_key=data.get("idempotency_key", ""),
            payload_sha256=data.get("payload_sha256", ""),
            created_at=data.get("created_at"),
            reviewed_at=data.get("reviewed_at"),
            approved_object_id=data.get("approved_object_id") if data.get("approved_object_id") is not None else None,
            ingestion_run_id=data.get("ingestion_run_id") if data.get("ingestion_run_id") is not None else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "change": self.change.to_dict(),
            "idempotency_key": self.idempotency_key,
            "payload_sha256": self.payload_sha256,
            "created_at": _datetime_text(self.created_at),
            "reviewed_at": _datetime_text(self.reviewed_at),
            "approved_object_id": self.approved_object_id,
            "ingestion_run_id": self.ingestion_run_id,
        }


@dataclass(frozen=True, slots=True)
class ReviewEvent:
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
        object.__setattr__(self, "event_id", _required_text(self.event_id, "event_id"))
        object.__setattr__(self, "change_id", _required_text(self.change_id, "change_id"))
        object.__setattr__(self, "event_type", _enum(self.event_type, ReviewEventType, "event_type"))
        object.__setattr__(self, "actor_id", _required_text(self.actor_id, "actor_id"))
        object.__setattr__(self, "actor_kind", _enum(self.actor_kind, ActorKind, "actor_kind"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        created_at = _aware_datetime(self.created_at, "created_at", required=True)
        assert created_at is not None
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ReviewEvent":
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
            "created_at": _datetime_text(self.created_at),
            "metadata": dict(self.metadata),
        }
