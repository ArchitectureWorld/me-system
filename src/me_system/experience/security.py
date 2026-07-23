from __future__ import annotations

import re


_DATABASE_URL_RE = re.compile(
    r"(?:postgresql(?:\+psycopg)?|sqlite(?:\+pysqlite)?):\/\/[^\s,;'\"<>]+",
    re.IGNORECASE,
)
_PASSWORD_ASSIGNMENT_RE = re.compile(
    r"\b(password\s*=\s*)[^\s,;]+",
    re.IGNORECASE,
)


def sanitize_error(
    value: Exception | object,
    *,
    database_url: str | None = None,
    max_length: int = 320,
) -> str:
    """Return a compact diagnostic without credentials, URLs, or tracebacks."""

    text = str(value).strip() or type(value).__name__
    if database_url:
        text = text.replace(database_url, "[database-url-redacted]")
    text = _DATABASE_URL_RE.sub("[database-url-redacted]", text)
    text = _PASSWORD_ASSIGNMENT_RE.sub(r"\1[redacted]", text)
    text = text.replace("Traceback", "错误详情")
    return text[: max(1, int(max_length))]
