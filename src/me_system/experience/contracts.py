from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Sequence


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value


def _required_text(value: object, name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _aware_datetime(value: object, name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = _required_text(value, name)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def _datetime_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return dict(value)


@dataclass(frozen=True, slots=True)
class AcceptanceCheck:
    check_id: str
    title: str
    status: CheckStatus
    summary: str
    evidence: Mapping[str, object]
    duration_ms: int
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_id", _required_text(self.check_id, "check_id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        if isinstance(self.status, CheckStatus):
            status = self.status
        else:
            try:
                status = CheckStatus(str(self.status))
            except ValueError as exc:
                raise ValueError("status must be pass, fail, or skipped") from exc
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "evidence", _mapping(self.evidence, "evidence"))
        duration = int(self.duration_ms)
        if duration < 0:
            raise ValueError("duration_ms must be zero or greater")
        object.__setattr__(self, "duration_ms", duration)
        object.__setattr__(self, "error_type", _optional_text(self.error_type))
        object.__setattr__(self, "error_message", _optional_text(self.error_message))
        if status is CheckStatus.FAIL and not self.error_message:
            raise ValueError("failed checks require error_message")
        if status is not CheckStatus.FAIL and (self.error_type or self.error_message):
            raise ValueError("passing or skipped checks must not include error details")

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AcceptanceCheck":
        return cls(
            check_id=data.get("check_id", ""),
            title=data.get("title", ""),
            status=data.get("status", ""),
            summary=data.get("summary", ""),
            evidence=data.get("evidence") if isinstance(data.get("evidence"), Mapping) else {},
            duration_ms=data.get("duration_ms", 0),
            error_type=data.get("error_type") if data.get("error_type") is not None else None,
            error_message=(
                data.get("error_message") if data.get("error_message") is not None else None
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "status": self.status.value,
            "summary": self.summary,
            "evidence": dict(self.evidence),
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    run_id: str
    started_at: datetime
    completed_at: datetime
    checks: tuple[AcceptanceCheck, ...]
    highlights: Mapping[str, object]
    technical: Mapping[str, object]
    version: str

    SCHEMA_VERSION = "one-click-acceptance/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        started = _aware_datetime(self.started_at, "started_at")
        completed = _aware_datetime(self.completed_at, "completed_at")
        if completed < started:
            raise ValueError("completed_at must not be earlier than started_at")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "completed_at", completed)
        normalized: list[AcceptanceCheck] = []
        for value in self.checks:
            if not isinstance(value, AcceptanceCheck):
                raise ValueError("checks must contain AcceptanceCheck values")
            normalized.append(value)
        if not normalized:
            raise ValueError("checks must not be empty")
        ids = [value.check_id for value in normalized]
        if len(ids) != len(set(ids)):
            raise ValueError("check_id values must be unique")
        object.__setattr__(self, "checks", tuple(normalized))
        object.__setattr__(self, "highlights", _mapping(self.highlights, "highlights"))
        object.__setattr__(self, "technical", _mapping(self.technical, "technical"))
        object.__setattr__(self, "version", _required_text(self.version, "version"))

    @property
    def status(self) -> str:
        if any(value.status is CheckStatus.FAIL for value in self.checks):
            return "fail"
        if all(value.status is CheckStatus.PASS for value in self.checks):
            return "pass"
        return "partial"

    @property
    def passed_count(self) -> int:
        return sum(value.status is CheckStatus.PASS for value in self.checks)

    @property
    def failed_count(self) -> int:
        return sum(value.status is CheckStatus.FAIL for value in self.checks)

    @property
    def skipped_count(self) -> int:
        return sum(value.status is CheckStatus.SKIPPED for value in self.checks)

    @property
    def duration_ms(self) -> int:
        return int(round((self.completed_at - self.started_at).total_seconds() * 1000))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AcceptanceReport":
        values = data.get("checks")
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise ValueError("checks must be an array")
        return cls(
            run_id=data.get("run_id", ""),
            started_at=_aware_datetime(data.get("started_at"), "started_at"),
            completed_at=_aware_datetime(data.get("completed_at"), "completed_at"),
            checks=tuple(
                AcceptanceCheck.from_dict(value)
                for value in values
                if isinstance(value, Mapping)
            ),
            highlights=(
                data.get("highlights") if isinstance(data.get("highlights"), Mapping) else {}
            ),
            technical=(
                data.get("technical") if isinstance(data.get("technical"), Mapping) else {}
            ),
            version=data.get("version", ""),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": self.run_id,
            "status": self.status,
            "started_at": _datetime_text(self.started_at),
            "completed_at": _datetime_text(self.completed_at),
            "duration_ms": self.duration_ms,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "checks": [value.to_dict() for value in self.checks],
            "highlights": dict(self.highlights),
            "technical": dict(self.technical),
            "version": self.version,
        }
