from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Mapping

from ..contracts import EvidenceRef, Sensitivity
from ..errors import ContractValidationError


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FragmentType(str, Enum):
    CONVERSATION_MESSAGE = "conversation_message"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    GIT_COMMIT = "git_commit"
    UNKNOWN = "unknown"

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


def _sha256(value: object, name: str) -> str:
    text = _required_text(value, name).lower()
    if not _SHA256_RE.fullmatch(text):
        raise ContractValidationError(f"{name} must be a 64-character lowercase SHA-256 hex digest")
    return text


def _sensitivity(value: object) -> Sensitivity:
    if isinstance(value, Sensitivity):
        return value
    try:
        return Sensitivity(str(value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Sensitivity)
        raise ContractValidationError(f"sensitivity must be one of: {allowed}") from exc


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{name} must be an object")
    return dict(value)


def _source_anchor(value: object) -> dict[str, object]:
    anchor = _mapping(value, "source_anchor")
    anchor_type = _required_text(anchor.get("type"), "source_anchor.type")
    anchor_value = anchor.get("value")
    if not isinstance(anchor_value, Mapping):
        raise ContractValidationError("source_anchor.value must be an object")
    return {"type": anchor_type, "value": dict(anchor_value)}


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
    metadata: Mapping[str, object]

    SCHEMA_VERSION = "source-record/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "source_type", _required_text(self.source_type, "source_type"))
        object.__setattr__(self, "external_system", _optional_text(self.external_system, "external_system"))
        object.__setattr__(self, "external_id", _optional_text(self.external_id, "external_id"))
        object.__setattr__(self, "idempotency_key", _required_text(self.idempotency_key, "idempotency_key"))
        object.__setattr__(self, "content_ref", _required_text(self.content_ref, "content_ref"))
        object.__setattr__(self, "content_sha256", _sha256(self.content_sha256, "content_sha256"))
        object.__setattr__(self, "media_type", _optional_text(self.media_type, "media_type"))
        object.__setattr__(
            self,
            "occurred_at",
            _aware_datetime(self.occurred_at, "occurred_at", required=False),
        )
        ingested_at = _aware_datetime(self.ingested_at, "ingested_at", required=True)
        assert ingested_at is not None
        object.__setattr__(self, "ingested_at", ingested_at)
        object.__setattr__(self, "sensitivity", _sensitivity(self.sensitivity))
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SourceRecord":
        return cls(
            source_id=data.get("source_id", ""),
            source_type=data.get("source_type", ""),
            external_system=data.get("external_system"),
            external_id=data.get("external_id"),
            idempotency_key=data.get("idempotency_key", ""),
            content_ref=data.get("content_ref", ""),
            content_sha256=data.get("content_sha256", ""),
            media_type=data.get("media_type"),
            occurred_at=data.get("occurred_at"),
            ingested_at=data.get("ingested_at"),
            sensitivity=data.get("sensitivity", ""),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def identity_payload(self) -> dict[str, object]:
        """Return immutable content identity fields used for idempotent retries."""

        return {
            "source_type": self.source_type,
            "external_system": self.external_system,
            "external_id": self.external_id,
            "idempotency_key": self.idempotency_key,
            "content_ref": self.content_ref,
            "content_sha256": self.content_sha256,
            "media_type": self.media_type,
            "occurred_at": _datetime_text(self.occurred_at),
            "sensitivity": self.sensitivity.value,
            "metadata": dict(self.metadata),
        }

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
    metadata: Mapping[str, object]

    SCHEMA_VERSION = "evidence-fragment/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fragment_id", _required_text(self.fragment_id, "fragment_id"))
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        ordinal = int(self.ordinal)
        if ordinal < 0:
            raise ContractValidationError("ordinal must be zero or greater")
        object.__setattr__(self, "ordinal", ordinal)
        if isinstance(self.fragment_type, FragmentType):
            fragment_type = self.fragment_type
        else:
            try:
                fragment_type = FragmentType(str(self.fragment_type))
            except ValueError as exc:
                allowed = ", ".join(item.value for item in FragmentType)
                raise ContractValidationError(f"fragment_type must be one of: {allowed}") from exc
        object.__setattr__(self, "fragment_type", fragment_type)
        object.__setattr__(self, "text_content", None if self.text_content is None else str(self.text_content))
        object.__setattr__(self, "source_anchor", _source_anchor(self.source_anchor))
        object.__setattr__(self, "content_sha256", _sha256(self.content_sha256, "content_sha256"))
        object.__setattr__(
            self,
            "occurred_at",
            _aware_datetime(self.occurred_at, "occurred_at", required=False),
        )
        object.__setattr__(self, "actor_id", _optional_text(self.actor_id, "actor_id"))
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
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def to_evidence_ref(
        self,
        *,
        document_id: str | None = None,
        version_id: str | None = None,
    ) -> EvidenceRef:
        return EvidenceRef(
            source_id=self.source_id,
            document_id=document_id,
            version_id=version_id,
            content_fragment_id=self.fragment_id,
            source_anchor={
                "type": self.source_anchor["type"],
                "value": dict(self.source_anchor["value"]),
            },
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
            "metadata": dict(self.metadata),
        }
