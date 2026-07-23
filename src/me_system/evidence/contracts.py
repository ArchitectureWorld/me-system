from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

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
    source_anchor,
)
from ..contracts import Sensitivity


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
        object.__setattr__(self, "source_id", required_text(self.source_id, "source_id"))
        object.__setattr__(self, "source_type", required_text(self.source_type, "source_type"))
        object.__setattr__(
            self,
            "external_system",
            optional_text(self.external_system, "external_system"),
        )
        object.__setattr__(self, "external_id", optional_text(self.external_id, "external_id"))
        object.__setattr__(
            self,
            "idempotency_key",
            required_text(self.idempotency_key, "idempotency_key"),
        )
        object.__setattr__(self, "content_ref", required_text(self.content_ref, "content_ref"))
        object.__setattr__(
            self,
            "content_sha256",
            sha256_text(self.content_sha256, "content_sha256"),
        )
        object.__setattr__(self, "media_type", optional_text(self.media_type, "media_type"))
        object.__setattr__(
            self,
            "occurred_at",
            aware_datetime(self.occurred_at, "occurred_at"),
        )
        ingested_at = aware_datetime(self.ingested_at, "ingested_at", required=True)
        assert ingested_at is not None
        object.__setattr__(self, "ingested_at", ingested_at)
        object.__setattr__(
            self,
            "sensitivity",
            enum_value(self.sensitivity, Sensitivity, "sensitivity"),
        )
        object.__setattr__(self, "metadata", mapping_copy(self.metadata, "metadata"))

    def fingerprint(self) -> str:
        """Hash the immutable source snapshot, excluding local record identity."""

        return canonical_sha256(
            {
                "source_type": self.source_type,
                "external_system": self.external_system,
                "external_id": self.external_id,
                "content_ref": self.content_ref,
                "content_sha256": self.content_sha256,
                "media_type": self.media_type,
                "occurred_at": datetime_text(self.occurred_at),
                "sensitivity": self.sensitivity.value,
                "metadata": dict(self.metadata),
            }
        )

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
            "occurred_at": datetime_text(self.occurred_at),
            "ingested_at": datetime_text(self.ingested_at),
            "sensitivity": self.sensitivity.value,
            "metadata": mapping_copy(self.metadata, "metadata"),
        }


@dataclass(frozen=True, slots=True)
class EvidenceFragment:
    fragment_id: str
    source_id: str
    ordinal: int
    fragment_type: str
    text_content: str | None
    source_anchor: Mapping[str, object]
    content_sha256: str
    occurred_at: datetime | None
    actor_id: str | None
    metadata: Mapping[str, object]

    SCHEMA_VERSION = "evidence-fragment/0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fragment_id", required_text(self.fragment_id, "fragment_id"))
        object.__setattr__(self, "source_id", required_text(self.source_id, "source_id"))
        object.__setattr__(self, "ordinal", nonnegative_int(self.ordinal, "ordinal"))
        object.__setattr__(
            self,
            "fragment_type",
            required_text(self.fragment_type, "fragment_type"),
        )
        if self.text_content is not None:
            object.__setattr__(self, "text_content", str(self.text_content))
        object.__setattr__(self, "source_anchor", source_anchor(self.source_anchor))
        object.__setattr__(
            self,
            "content_sha256",
            sha256_text(self.content_sha256, "content_sha256"),
        )
        object.__setattr__(
            self,
            "occurred_at",
            aware_datetime(self.occurred_at, "occurred_at"),
        )
        object.__setattr__(self, "actor_id", optional_text(self.actor_id, "actor_id"))
        object.__setattr__(self, "metadata", mapping_copy(self.metadata, "metadata"))

    def fingerprint(self) -> str:
        return canonical_sha256(
            {
                "source_id": self.source_id,
                "ordinal": self.ordinal,
                "fragment_type": self.fragment_type,
                "text_content": self.text_content,
                "source_anchor": mapping_copy(self.source_anchor, "source_anchor"),
                "content_sha256": self.content_sha256,
                "occurred_at": datetime_text(self.occurred_at),
                "actor_id": self.actor_id,
                "metadata": mapping_copy(self.metadata, "metadata"),
            }
        )

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
            actor_id=data.get("actor_id"),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "fragment_id": self.fragment_id,
            "source_id": self.source_id,
            "ordinal": self.ordinal,
            "fragment_type": self.fragment_type,
            "text_content": self.text_content,
            "source_anchor": mapping_copy(self.source_anchor, "source_anchor"),
            "content_sha256": self.content_sha256,
            "occurred_at": datetime_text(self.occurred_at),
            "actor_id": self.actor_id,
            "metadata": mapping_copy(self.metadata, "metadata"),
        }
