"""Redaction helpers for workspace memory capture."""

import re

_SENSITIVE_ASSIGNMENT = re.compile(
    r"\b(api[_-]?key|password|secret|token)\b\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)
_LONG_SECRETISH_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")


def redact_sensitive_text(value: str) -> tuple[str, bool]:
    """Redact obvious secrets from operator-reviewed memory text."""

    redacted = False

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal redacted
        redacted = True
        return f"{match.group(1)}=<redacted>"

    value = _SENSITIVE_ASSIGNMENT.sub(replace_assignment, value)

    def replace_token(match: re.Match[str]) -> str:
        nonlocal redacted
        redacted = True
        return "<redacted-token>"

    value = _LONG_SECRETISH_TOKEN.sub(replace_token, value)
    return value, redacted


__all__ = ["redact_sensitive_text"]
