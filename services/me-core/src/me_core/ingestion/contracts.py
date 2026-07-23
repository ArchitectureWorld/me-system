from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import TypeVar

from ..contracts import Sensitivity, StrEnum
from ..errors import ContractValidationError


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EnumT = TypeVar("EnumT", bound=StrEnum)


class FragmentType(StrEnum):
    CONVERSATION_MESSAGE = "conversation_message"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    GIT_COMMIT = "git_commit"
    UNKNOWN = "unknown"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


_TERMINAL_STATUSES = {
    IngestionStatus.COMPLETED,
    IngestionStatus.PARTIAL,
    IngestionStatus.FAILED,
}


def _required_text(value: object, name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ContractValidationError(f"{name} must not be empty")
    return normalized


def _optional_text(value: object | None, name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return _required_text(normalized, name) if normalized else None


def _enum(value: object, enum_type: type[EnumT], name: str) -> EnumT:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ContractValidationError(f"{name} must be one of: {allowed}") from exc


def _datetime(value: object | None, name: str) -> datetime | None:
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


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{name} must be an object")
    return dict(value)


def _sha256(value: object, name: str = "content_sha256") -> str:
    normalized = _required_text(value, name)
    if not _SHA256_RE.fullmatch(normalized):
        raise ContractValidationError(f"{name} must be a lowercase 64-character SHA-256 hex digest")
    return normalized


def _anchor(value: object) -> dict[str, object]:
    anchor = _mapping(value, "source_anchor")
    anchor_type = _required_text(anchor.get("type"), "source_anchor.type")
    anchor_value = _mapping(anchor.get("value"), "source_anchor.value")
    return {"type": anchor_type, "value": anchor_value}


def _non_negative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractValidationError(f"{name} must be an integer")
    if value < 0:
        raise ContractValidationError(f"{name} must be zero or greater")
    return value


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_type: str
    external_system: str | None
    external_id: str | None
    idempotency_key: str
    content_ref: str
    content_sha256: str
    media_type: str | None
    occurred_at: datetime | None
    ingested_at: datetime
    sensitivity: Sensitivity
    metadata: Mapping[str, object] = field(default_factory=dict)

    SCHEMA_VERSION = "source-record/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "source_type", _required_text(self.source_type, "source_type"))
        object.__setattr__(self, "external_system", _optional_text(self.external_system, "external_system"))
        object.__setattr__(self, "external_id", _optional_text(self.external_id, "external_id"))
        object.__setattr__(self, "idempotency_key", _required_text(self.idempotency_key, "idempotency_key"))
        object.__setattr__(self, "content_ref", _required_text(self.content_ref, "content_ref"))
        object.__setattr__(self, "content_sha256", _sha256(self.content_sha256))
        object.__setattr__(self, "media_type", _optional_text(self.media_type, "media_type"))
        object.__setattr__(self, "occurred_at", _datetime(self.occurred_at, "occurred_at"))
        ingested_at = _datetime(self.ingested_at, "ingested_at")
        if ingested_at is None:
            raise ContractValidationError("ingested_at must not be empty")
        object.__setattr__(self, "ingested_at", ingested_at)
        object.__setattr__(self, "sensitivity", _enum(self.sensitivity, Sensitivity, "sensitivity"))
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))

    def identity_digest(self) -> str:
        payload = {
            "source_type": self.source_type,
            "external_system": self.external_system,
            "external_id": self.external_id,
            "content_sha256": self.content_sha256,
            "media_type": self.media_type,
            "occurred_at": _datetime_text(self.occurred_at),
            "sensitivity": self.sensitivity.value,
            "metadata": dict(self.metadata),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SourceRecord":
        return cls(
            source_id=data.get("source_id", ""),
            source_type=data.get("source_type", ""),
            external_system=data.get("external_system") if data.get("external_system") is not None else None,
            external_id=data.get("external_id") if data.get("external_id") is not None else None,
            idempotency_key=data.get("idempotency_key", ""),
            content_ref=data.get("content_ref", ""),
            content_sha256=data.get("content_sha256", ""),
            media_type=data.get("media_type") if data.get("media_type") is not None else None,
            occurred_at=data.get("occurred_at"),
            ingested_at=data.get("ingested_at"),
            sensitivity=data.get("sensitivity", ""),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "external_system": self.external_system,
            "external_id": self.external_id,
            "idempotency_key": self.idempotency_key,
            "content_ref": self.content_ref,
            "content_sha256": self.content_sha256,
            "media_type": self.media_type,
            "occurred_at": _datetime_text(self.occurred_at),
            "ingested_at": _datetime_text(self.ingested_at),
            "sensitivity": self.sensitivity.value,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EvidenceFragment:
    fragment_id: str
    source_id: str
    ordinal: int
    fragment_type: FragmentType
    text_content: str | None
    source_anchor: Mapping[str, object]
    content_sha256: str
    occurred_at: datetime | None
    actor_id: str | None
    sensitivity: Sensitivity
    metadata: Mapping[str, object] = field(default_factory=dict)

    SCHEMA_VERSION = "evidence-fragment/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fragment_id", _required_text(self.fragment_id, "fragment_id"))
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "ordinal", _non_negative_integer(self.ordinal, "ordinal"))
        object.__setattr__(self, "fragment_type", _enum(self.fragment_type, FragmentType, "fragment_type"))
        if self.text_content is not None and not isinstance(self.text_content, str):
            raise ContractValidationError("text_content must be a string or null")
        object.__setattr__(self, "source_anchor", _anchor(self.source_anchor))
        object.__setattr__(self, "content_sha256", _sha256(self.content_sha256))
        object.__setattr__(self, "occurred_at", _datetime(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "actor_id", _optional_text(self.actor_id, "actor_id"))
        object.__setattr__(self, "sensitivity", _enum(self.sensitivity, Sensitivity, "sensitivity"))
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvidenceFragment":
        return cls(
            fragment_id=data.get("fragment_id", ""),
            source_id=data.get("source_id", ""),
            ordinal=data.get("ordinal", -1),
            fragment_type=data.get("fragment_type", ""),
            text_content=data.get("text_content") if data.get("text_content") is not None else None,
            source_anchor=data.get("source_anchor") if isinstance(data.get("source_anchor"), Mapping) else {},
            content_sha256=data.get("content_sha256", ""),
            occurred_at=data.get("occurred_at"),
            actor_id=data.get("actor_id") if data.get("actor_id") is not None else None,
            sensitivity=data.get("sensitivity", ""),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "fragment_id": self.fragment_id,
            "source_id": self.source_id,
            "ordinal": self.ordinal,
            "fragment_type": self.fragment_type.value,
            "text_content": self.text_content,
            "source_anchor": {
                "type": self.source_anchor["type"],
                "value": dict(self.source_anchor["value"]),
            },
            "content_sha256": self.content_sha256,
            "occurred_at": _datetime_text(self.occurred_at),
            "actor_id": self.actor_id,
            "sensitivity": self.sensitivity.value,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class IngestionCounts:
    input_item_count: int = 0
    processed_item_count: int = 0
    skipped_item_count: int = 0
    failed_item_count: int = 0
    fragment_count: int = 0
    candidate_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "input_item_count",
            "processed_item_count",
            "skipped_item_count",
            "failed_item_count",
            "fragment_count",
            "candidate_count",
        ):
            object.__setattr__(self, name, _non_negative_integer(getattr(self, name), name))
        handled = self.processed_item_count + self.skipped_item_count + self.failed_item_count
        if handled > self.input_item_count:
            raise ContractValidationError(
                "processed_item_count + skipped_item_count + failed_item_count must not exceed input_item_count"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IngestionCounts":
        return cls(
            input_item_count=data.get("input_item_count", 0),
            processed_item_count=data.get("processed_item_count", 0),
            skipped_item_count=data.get("skipped_item_count", 0),
            failed_item_count=data.get("failed_item_count", 0),
            fragment_count=data.get("fragment_count", 0),
            candidate_count=data.get("candidate_count", 0),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "input_item_count": self.input_item_count,
            "processed_item_count": self.processed_item_count,
            "skipped_item_count": self.skipped_item_count,
            "failed_item_count": self.failed_item_count,
            "fragment_count": self.fragment_count,
            "candidate_count": self.candidate_count,
        }


@dataclass(frozen=True, slots=True)
class IngestionRun:
    run_id: str
    source_id: str
    adapter_name: str
    adapter_version: str
    pipeline_version: str
    status: IngestionStatus
    started_at: datetime | None
    completed_at: datetime | None
    counts: IngestionCounts
    coverage_ratio: float
    quality_report: Mapping[str, object] = field(default_factory=dict)
    log_ref: str | None = None
    error_summary: str | None = None

    SCHEMA_VERSION = "ingestion-run/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "adapter_name", _required_text(self.adapter_name, "adapter_name"))
        object.__setattr__(self, "adapter_version", _required_text(self.adapter_version, "adapter_version"))
        object.__setattr__(self, "pipeline_version", _required_text(self.pipeline_version, "pipeline_version"))
        status = _enum(self.status, IngestionStatus, "status")
        object.__setattr__(self, "status", status)
        started_at = _datetime(self.started_at, "started_at")
        completed_at = _datetime(self.completed_at, "completed_at")
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "completed_at", completed_at)
        counts = self.counts if isinstance(self.counts, IngestionCounts) else IngestionCounts.from_dict(self.counts)
        object.__setattr__(self, "counts", counts)
        coverage = float(self.coverage_ratio)
        if not 0 <= coverage <= 1:
            raise ContractValidationError("coverage_ratio must be between 0 and 1")
        object.__setattr__(self, "coverage_ratio", coverage)
        object.__setattr__(self, "quality_report", _mapping(self.quality_report, "quality_report"))
        object.__setattr__(self, "log_ref", _optional_text(self.log_ref, "log_ref"))
        object.__setattr__(self, "error_summary", _optional_text(self.error_summary, "error_summary"))

        if status is IngestionStatus.PENDING:
            if started_at is not None or completed_at is not None:
                raise ContractValidationError("pending ingestion runs must not include start or completion timestamps")
        elif status is IngestionStatus.RUNNING:
            if started_at is None:
                raise ContractValidationError("running ingestion runs require started_at")
            if completed_at is not None:
                raise ContractValidationError("running ingestion runs must not include completed_at")
        else:
            if started_at is None:
                raise ContractValidationError("terminal ingestion runs require started_at")
            if completed_at is None:
                raise ContractValidationError("terminal ingestion runs require completed_at")
            if completed_at < started_at:
                raise ContractValidationError("completed_at must not be earlier than started_at")

    def start(self, started_at: datetime) -> "IngestionRun":
        if self.status is not IngestionStatus.PENDING:
            raise ContractValidationError("only pending ingestion runs can start")
        return replace(
            self,
            status=IngestionStatus.RUNNING,
            started_at=_datetime(started_at, "started_at"),
        )

    def finish(
        self,
        *,
        status: IngestionStatus,
        completed_at: datetime,
        counts: IngestionCounts,
        coverage_ratio: float,
        quality_report: Mapping[str, object],
        log_ref: str | None = None,
        error_summary: str | None = None,
    ) -> "IngestionRun":
        if self.status is not IngestionStatus.RUNNING:
            raise ContractValidationError("only running ingestion runs can finish")
        terminal = _enum(status, IngestionStatus, "status")
        if terminal not in _TERMINAL_STATUSES:
            raise ContractValidationError("finish status must be terminal")
        return replace(
            self,
            status=terminal,
            completed_at=_datetime(completed_at, "completed_at"),
            counts=counts,
            coverage_ratio=coverage_ratio,
            quality_report=quality_report,
            log_ref=log_ref,
            error_summary=error_summary,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "IngestionRun":
        counts = data.get("counts")
        return cls(
            run_id=data.get("run_id", ""),
            source_id=data.get("source_id", ""),
            adapter_name=data.get("adapter_name", ""),
            adapter_version=data.get("adapter_version", ""),
            pipeline_version=data.get("pipeline_version", ""),
            status=data.get("status", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            counts=IngestionCounts.from_dict(counts if isinstance(counts, Mapping) else {}),
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
            "pipeline_version": self.pipeline_version,
            "status": self.status.value,
            "started_at": _datetime_text(self.started_at),
            "completed_at": _datetime_text(self.completed_at),
            "counts": self.counts.to_dict(),
            "coverage_ratio": self.coverage_ratio,
            "quality_report": dict(self.quality_report),
            "log_ref": self.log_ref,
            "error_summary": self.error_summary,
        }
