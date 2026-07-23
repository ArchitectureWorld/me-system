from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Mapping, TypeVar

from .errors import ContractValidationError

EnumT = TypeVar("EnumT", bound=Enum)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def required_text(value: object, name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ContractValidationError(f"{name} must not be empty")
    return normalized


def optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    return required_text(value, name)


def enum_value(value: object, enum_type: type[EnumT], name: str) -> EnumT:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise ContractValidationError(f"{name} must be one of: {allowed}") from exc


def aware_datetime(value: object, name: str, *, required: bool = False) -> datetime | None:
    if value is None or value == "":
        if required:
            raise ContractValidationError(f"{name} must not be empty")
        return None
    if isinstance(value, datetime):
        result = value
    else:
        text = required_text(value, name)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ContractValidationError(f"{name} must be an ISO-8601 datetime") from exc
    if result.tzinfo is None:
        raise ContractValidationError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: object, name: str) -> str:
    normalized = required_text(value, name).lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ContractValidationError(f"{name} must be a lowercase SHA-256 hex digest")
    return normalized


def nonnegative_int(value: object, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractValidationError(f"{name} must be an integer") from exc
    if result < 0:
        raise ContractValidationError(f"{name} must be zero or greater")
    return result


def mapping_copy(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{name} must be an object")
    return deepcopy(dict(value))


def source_anchor(value: object) -> dict[str, object]:
    anchor = mapping_copy(value, "source_anchor")
    anchor_type = required_text(anchor.get("type"), "source_anchor.type")
    anchor_value = anchor.get("value")
    if not isinstance(anchor_value, Mapping):
        raise ContractValidationError("source_anchor.value must be an object")
    return {"type": anchor_type, "value": deepcopy(dict(anchor_value))}


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
