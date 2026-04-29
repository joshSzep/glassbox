"""Details pane widget and render helpers for the terminal UI."""

from typing import ClassVar

from textual.widgets import Static

from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import ToolActivity
from glassbox.cli.tui.widget_formatting import enum_or_string_value
from glassbox.cli.tui.widget_formatting import fit_line
from glassbox.cli.tui.widget_formatting import policy_decision_label
from glassbox.cli.tui.widget_formatting import policy_source_label
from glassbox.cli.tui.widget_formatting import tool_status_label
from glassbox.cli.tui.widget_formatting import truncate_middle
from glassbox.cli.tui.widget_formatting import truncate_path
from glassbox.cli.tui.widget_formatting import wrapped_label_lines

DETAILS_OUTPUT_PREVIEW_CHARS = 1200


class DetailsPane(Static):
    can_focus: ClassVar[bool] = True

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        super().__init__(render_details_pane(state), id="details-pane")
        self.display = False

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self.update(render_details_pane(state, width=self._render_width()))

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self) -> None:
        self.update_state(self._state)

    def toggle(self) -> None:
        self.display = not self.display
        if self.display:
            self.focus()

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 24)


def render_details_pane(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    tool = _selected_tool_for_details(state)
    tool_count = sum(len(turn.tools) for turn in state.turns)
    lines = [
        "Details",
        f"session: {state.header.session_id}",
        f"mode: {state.header.mode.value}",
        f"stream: {state.header.stream_status.value}",
        f"sequence: {state.header.last_sequence}",
        (
            f"recent: {len(state.messages)} messages | "
            f"{len(state.turns)} turns | {tool_count} tools"
        ),
    ]
    if state.header.dashboard_url is not None:
        lines.extend(
            wrapped_label_lines("dashboard", state.header.dashboard_url, width)
        )
    if state.failure is not None:
        lines.append(f"failure: {fit_line(state.failure.message, width - 9)}")
    if tool is None:
        lines.append("selected tool: none")
        return "\n".join(fit_line(line, width) for line in lines)
    lines.extend(_tool_details_lines(tool, state, width))
    return "\n".join(fit_line(line, width) for line in lines)


def _selected_tool_for_details(
    state: TerminalConversationState,
) -> ToolActivity | None:
    tools = [tool for turn in state.turns for tool in turn.tools]
    if not tools:
        return None
    for tool in reversed(tools):
        if tool.tool_call_id in state.expanded_tool_ids:
            return tool
    return tools[-1]


def _tool_details_lines(
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> list[str]:
    status = tool_status_label(tool, state)
    lines = [
        f"selected tool: {truncate_middle(tool.tool_name, 40)} [{status}]",
        f"tool id: {tool.tool_call_id}",
    ]
    if tool.arguments_json:
        lines.append(f"args: {fit_line(tool.arguments_json, width - 6)}")
    policy_parts: list[str] = []
    if tool.policy_outcome is not None:
        policy_parts.append(
            policy_decision_label(tool.policy_outcome, tool.policy_source_kind)
        )
    if tool.policy_risk_level is not None:
        policy_parts.append(f"risk {enum_or_string_value(tool.policy_risk_level)}")
    source = policy_source_label(tool.policy_source_kind, tool.policy_source_label)
    if source:
        policy_parts.append(f"source {source}")
    if policy_parts:
        lines.append("policy: " + " | ".join(policy_parts))
    if tool.policy_reason:
        lines.append(f"policy reason: {fit_line(tool.policy_reason, width - 15)}")
    if tool.summary:
        lines.append(f"summary: {fit_line(tool.summary, width - 9)}")
    if tool.exit_code is not None:
        lines.append(f"exit: {tool.exit_code}")
    if tool.output_text:
        output = tool.output_text.replace("\n", "\\n")
        truncated = len(output) > DETAILS_OUTPUT_PREVIEW_CHARS
        preview = output[:DETAILS_OUTPUT_PREVIEW_CHARS]
        lines.append(f"output: {fit_line(preview, width - 8)}")
        if truncated:
            lines.append("output policy: truncated; dashboard has full output")
    else:
        lines.append("output: none yet")
    for path in tool.artifact_paths:
        lines.append(f"artifact: {truncate_path(path, width - 10)}")
    return lines
