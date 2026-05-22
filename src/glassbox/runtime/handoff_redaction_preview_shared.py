"""Shared helpers for handoff redaction previews."""

from collections.abc import Mapping
from typing import Any

from glassbox.core import HandoffSafeCommand
from glassbox.runtime.session_export_redaction import REDACTION_PLACEHOLDER
from glassbox.runtime.session_export_redaction import WORKSPACE_PLACEHOLDER


def included_sections(payload: Mapping[str, Any]) -> list[str]:
    """Return non-empty top-level payload sections in stable order."""

    return [
        key
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    ][:100]


def redaction_marker_summary(value: Any) -> tuple[int, list[str]]:
    """Count redaction placeholders and return stable marker categories."""

    categories: list[str] = []
    count = 0
    for item in _walk_values(value):
        if not isinstance(item, str):
            continue
        redacted = REDACTION_PLACEHOLDER in item
        workspace = WORKSPACE_PLACEHOLDER in item
        if redacted or workspace:
            count += 1
        if redacted:
            categories.append("secret-like-token")
        if workspace:
            categories.append("workspace-path")
    return count, list(dict.fromkeys(categories))


def positive_counts(counts: Mapping[str, int]) -> dict[str, int]:
    """Drop zero-count local-only categories."""

    return {key: value for key, value in counts.items() if value > 0}


def safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    """Build a read-only safe command from display text."""

    return HandoffSafeCommand(
        command=display.split(),
        display=display,
        purpose=purpose,
    )


def _walk_values(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


__all__ = [
    "included_sections",
    "positive_counts",
    "redaction_marker_summary",
    "safe_command",
]
