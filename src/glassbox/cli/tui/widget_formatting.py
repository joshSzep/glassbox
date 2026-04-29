"""Shared formatting helpers for TUI widget renderers."""

from pathlib import PurePath
from textwrap import wrap

from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import ToolActivity
from glassbox.cli.tui.conversation import ToolActivityStatus


def dashboard_hint(
    dashboard_url: str | None,
    fallback: str,
    width: int,
) -> str:
    if dashboard_url is None:
        return fallback
    if width >= 104:
        return "dashboard ready (Ctrl+D open, Alt+D copy)"
    return "dashboard ready"


def wrapped_label_lines(label: str, value: str, width: int) -> list[str]:
    prefix = f"{label}: "
    available_width = max(width - len(prefix), 12)
    wrapped = wrap(
        value,
        width=available_width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    ) or [""]
    return [
        (prefix if index == 0 else " " * len(prefix)) + line
        for index, line in enumerate(wrapped)
    ]


def fit_line(value: str, width: int) -> str:
    if width <= 0 or len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def truncate_middle(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    left = (max_length - 3) // 2
    right = max_length - 3 - left
    return f"{value[:left]}...{value[-right:]}"


def truncate_path(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    path = PurePath(value)
    name = path.name
    if name and len(name) + 4 < max_length:
        prefix = truncate_middle(str(path.parent), max_length - len(name) - 4)
        return f"{prefix}/.../{name}"
    return truncate_middle(value, max_length)


def tool_status_label(
    tool: ToolActivity,
    state: TerminalConversationState,
) -> str:
    if (
        state.pending_approval is not None
        and state.pending_approval.tool_call_id == tool.tool_call_id
        and state.pending_approval.decision is None
    ):
        return "awaiting approval"
    if tool.status == ToolActivityStatus.REQUESTED:
        return "requested"
    if tool.status == ToolActivityStatus.RUNNING:
        return "running"
    if tool.status == ToolActivityStatus.SUCCEEDED:
        return "completed"
    return "failed"


def policy_decision_label(
    outcome: object,
    source_kind: object | None = None,
) -> str:
    outcome_value = enum_or_string_value(outcome)
    source_value = (
        enum_or_string_value(source_kind) if source_kind is not None else None
    )
    if outcome_value == "approve":
        return "policy approval required"
    if outcome_value == "deny":
        return "denied by policy"
    if outcome_value == "blocked" and source_value == "invariant":
        return "invariant block"
    if outcome_value == "blocked":
        return "blocked by policy"
    if outcome_value == "allow":
        return "advisory risk accepted"
    return f"outcome {outcome_value}"


def policy_source_label(source_kind: object | None, source_label: str | None) -> str:
    if source_kind is not None and source_label:
        return f"{enum_or_string_value(source_kind)}:{source_label}"
    if source_label:
        return source_label
    if source_kind is not None:
        return enum_or_string_value(source_kind)
    return ""


def enum_or_string_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)
