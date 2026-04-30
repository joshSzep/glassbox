"""Command text extraction and command-risk heuristics for tool policy."""

import re
from collections.abc import Mapping

from glassbox.tools.registry import ToolSpec

_DESTRUCTIVE_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)rm\s+-[A-Za-z-]*[rf][A-Za-z-]*\b"),
    re.compile(r"(^|\s)git\s+clean\b[^\n]*\s-f\b"),
    re.compile(r"(^|\s)git\s+reset\s+--hard\b"),
    re.compile(r"(^|\s)(mkfs|shutdown|reboot|poweroff)\b"),
)


def command_text(tool_spec: ToolSpec, arguments: Mapping[str, object]) -> str | None:
    """Return normalized command text for command tools."""

    if tool_spec.command_argument_name is None:
        return None
    value = arguments.get(tool_spec.command_argument_name)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def is_destructive_command(command_text: str) -> bool:
    """Return whether command text matches blocked destructive patterns."""

    normalized_command = command_text.strip().lower()
    return any(
        pattern.search(normalized_command) is not None
        for pattern in _DESTRUCTIVE_COMMAND_PATTERNS
    )
