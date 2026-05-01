"""Small shared utilities for session export helper modules."""

from collections.abc import Iterable
from collections.abc import Sequence

from glassbox.core.models import MessagePart


def message_text(parts: Sequence[MessagePart]) -> str:
    return " ".join(part.text for part in parts if part.text).strip()


def enum_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def stringify_optional(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)
