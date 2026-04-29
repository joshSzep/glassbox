"""Transcript widget and render helpers for the terminal UI."""

from contextlib import suppress
from dataclasses import dataclass
from textwrap import wrap
from typing import ClassVar

from rich.markdown import Markdown
from rich.text import Text
from textual.events import Resize
from textual.widgets import RichLog

from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import ConversationMessageKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import ToolActivity
from glassbox.cli.tui.conversation import ToolActivityStatus
from glassbox.cli.tui.widget_formatting import enum_or_string_value
from glassbox.cli.tui.widget_formatting import fit_line
from glassbox.cli.tui.widget_formatting import tool_status_label
from glassbox.cli.tui.widget_formatting import truncate_middle
from glassbox.cli.tui.widget_formatting import truncate_path

TRANSCRIPT_MIN_WIDTH = 36
TRANSCRIPT_USER_STYLE = "#8fc7ff"
TRANSCRIPT_ASSISTANT_STYLE = "#7bd88f"
TRANSCRIPT_RUNTIME_STYLE = "#aab2b7"
TRANSCRIPT_SYSTEM_STYLE = "#f5d36b"
TRANSCRIPT_FAILURE_STYLE = "#ff6b6b"


@dataclass(frozen=True, slots=True)
class TranscriptRenderLine:
    text: str
    style: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptRenderBlock:
    text: str
    style: str | None = None
    markdown: bool = False


class ConversationPane(RichLog):
    can_focus: ClassVar[bool] = True

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        self._follow_latest = True
        self._content_text = ""
        self._render_markdown = False
        self._scroll_callback_token = 0
        self._suppress_scroll_callback_invalidation = False
        self._rebuilding_content = False
        super().__init__(
            id="conversation-pane",
            auto_scroll=True,
            min_width=1,
            wrap=False,
            markup=False,
        )

    @property
    def content_text(self) -> str:
        return self._content_text

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self, event: Resize) -> None:
        super().on_resize(event)
        self.update_state(self._state)

    @property
    def markdown_enabled(self) -> bool:
        return self._render_markdown

    def update_state(
        self,
        state: TerminalConversationState,
        *,
        render_markdown: bool | None = None,
    ) -> None:
        self._state = state
        if render_markdown is not None:
            self._render_markdown = render_markdown
        self._replace_content(
            render_transcript_lines(state, width=self._render_width()),
            render_transcript_blocks(state) if self._render_markdown else None,
        )

    def jump_to_latest(self) -> None:
        self._follow_latest = True
        self._schedule_jump_to_latest()

    def _schedule_jump_to_latest(self) -> None:
        token = self._next_scroll_callback_token()
        with suppress(Exception):
            self.call_after_refresh(lambda: self._jump_to_latest_immediate(token))

    def _jump_to_latest_immediate(self, token: int) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(self.max_scroll_y)
            self.call_after_refresh(lambda: self._jump_to_latest_final(token))

    def _jump_to_latest_final(self, token: int) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(self.max_scroll_y)

    def page_up(self) -> None:
        self._invalidate_scroll_callbacks()
        with suppress(Exception):
            self.scroll_y = max(
                self.scroll_y - max(self.size.height - 1, 1),
                0,
            )
            self._follow_latest = False

    def page_down(self) -> None:
        self._invalidate_scroll_callbacks()
        with suppress(Exception):
            self.scroll_y = min(
                self.scroll_y + max(self.size.height - 1, 1),
                self.max_scroll_y,
            )
            self._follow_latest = self._is_at_latest()

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if (
            self.is_mounted
            and not self._rebuilding_content
            and not self._suppress_scroll_callback_invalidation
        ):
            self._follow_latest = new_value >= self.max_scroll_y
            if not self._follow_latest:
                self._invalidate_scroll_callbacks()

    def on_mouse_scroll_up(self) -> None:
        self._invalidate_scroll_callbacks()
        self._follow_latest = False

    def on_mouse_scroll_down(self) -> None:
        self._invalidate_scroll_callbacks()
        self._follow_latest = False

    def show_local_message(self, message: str) -> None:
        self._replace_content(_plain_transcript_lines(message))

    def _replace_content(
        self,
        lines: list[TranscriptRenderLine],
        blocks: list[TranscriptRenderBlock] | None = None,
    ) -> None:
        previous_scroll_y = self.scroll_y if self.is_mounted else 0
        should_follow_latest = self._follow_latest
        self._rebuilding_content = True
        try:
            self.clear()
            self._content_text = "\n".join(line.text for line in lines)
            width = self._render_width()
            if blocks is not None:
                self._write_markdown_blocks(blocks, width)
                self._restore_scroll_position(previous_scroll_y, should_follow_latest)
                return
            for line in lines:
                self.write(
                    Text(line.text, style=line.style or ""),
                    width=width,
                    scroll_end=False,
                )
        finally:
            self._rebuilding_content = False
        self._restore_scroll_position(previous_scroll_y, should_follow_latest)

    def _restore_scroll_position(
        self,
        previous_scroll_y: float,
        should_follow_latest: bool,
    ) -> None:
        if should_follow_latest:
            self._follow_latest = True
            self._schedule_jump_to_latest()
            return
        self._follow_latest = False
        token = self._next_scroll_callback_token()
        self.call_after_refresh(
            lambda: self._restore_manual_scroll_position(token, previous_scroll_y)
        )

    def _restore_manual_scroll_position(
        self,
        token: int,
        previous_scroll_y: float,
    ) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(
                min(previous_scroll_y, self.max_scroll_y)
            )

    def _next_scroll_callback_token(self) -> int:
        self._scroll_callback_token += 1
        return self._scroll_callback_token

    def _invalidate_scroll_callbacks(self) -> None:
        self._scroll_callback_token += 1

    def _set_scroll_y_without_invalidating_callbacks(self, value: float) -> None:
        self._suppress_scroll_callback_invalidation = True
        try:
            self.scroll_y = value
        finally:
            self._suppress_scroll_callback_invalidation = False

    def _write_markdown_blocks(
        self,
        blocks: list[TranscriptRenderBlock],
        width: int,
    ) -> None:
        for block in blocks:
            if block.markdown:
                self.write(
                    Markdown(
                        block.text,
                        style=block.style or "none",
                        hyperlinks=False,
                    ),
                    width=width,
                    scroll_end=False,
                )
            else:
                self.write(
                    Text(block.text, style=block.style or ""),
                    width=width,
                    scroll_end=False,
                )

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        content_width = self.scrollable_content_region.width
        if content_width > 0:
            return content_width
        return max(self.size.width - 2, 1)

    def _is_at_latest(self) -> bool:
        if not self.is_mounted:
            return True
        return self.scroll_y >= max(self.max_scroll_y - 1, 0)


def render_transcript(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    return "\n".join(line.text for line in render_transcript_lines(state, width=width))


def render_transcript_lines(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> list[TranscriptRenderLine]:
    width = max(width, TRANSCRIPT_MIN_WIDTH)
    lines: list[TranscriptRenderLine] = []
    if not _has_visible_transcript_content(state):
        return [
            TranscriptRenderLine(
                _empty_transcript_text(state),
                TRANSCRIPT_RUNTIME_STYLE,
            )
        ]

    for message in state.messages:
        _append_message(lines, message.kind, message.text, width, message.status)

    for turn in state.turns:
        if turn.failure_message:
            _append_block(
                lines,
                "Turn failed",
                turn.failure_message,
                width,
                title_style=TRANSCRIPT_FAILURE_STYLE,
                body_style=TRANSCRIPT_FAILURE_STYLE,
            )

    if state.failure is not None:
        _append_block(
            lines,
            "Failure",
            state.failure.message,
            width,
            title_style=TRANSCRIPT_FAILURE_STYLE,
            body_style=TRANSCRIPT_FAILURE_STYLE,
        )

    return lines


def render_transcript_blocks(
    state: TerminalConversationState,
) -> list[TranscriptRenderBlock]:
    blocks: list[TranscriptRenderBlock] = []
    if not _has_visible_transcript_content(state):
        return [
            TranscriptRenderBlock(
                _empty_transcript_text(state),
                TRANSCRIPT_RUNTIME_STYLE,
            )
        ]

    for message in state.messages:
        if blocks:
            blocks.append(TranscriptRenderBlock(""))
        style = _message_style(message.kind)
        blocks.append(
            TranscriptRenderBlock(message.text or "...", style, markdown=True)
        )
        if marker := _message_status_marker(message.status):
            blocks.append(
                TranscriptRenderBlock(
                    marker,
                    _message_status_style(message.status),
                )
            )

    for turn in state.turns:
        if turn.failure_message:
            if blocks:
                blocks.append(TranscriptRenderBlock(""))
            blocks.append(
                TranscriptRenderBlock("Turn failed", TRANSCRIPT_FAILURE_STYLE)
            )
            blocks.append(
                TranscriptRenderBlock(turn.failure_message, TRANSCRIPT_FAILURE_STYLE)
            )

    if state.failure is not None:
        if blocks:
            blocks.append(TranscriptRenderBlock(""))
        blocks.append(TranscriptRenderBlock("Failure", TRANSCRIPT_FAILURE_STYLE))
        blocks.append(
            TranscriptRenderBlock(state.failure.message, TRANSCRIPT_FAILURE_STYLE)
        )

    return blocks


def _has_visible_transcript_content(state: TerminalConversationState) -> bool:
    if state.messages or state.failure is not None:
        return True
    return any(turn.failure_message for turn in state.turns)


def _message_style(kind: ConversationMessageKind) -> str:
    if kind == ConversationMessageKind.USER:
        return TRANSCRIPT_USER_STYLE
    if kind == ConversationMessageKind.ASSISTANT:
        return TRANSCRIPT_ASSISTANT_STYLE
    if kind == ConversationMessageKind.RUNTIME:
        return TRANSCRIPT_RUNTIME_STYLE
    return TRANSCRIPT_SYSTEM_STYLE


def _message_status_marker(status: AssistantMessageStatus | None) -> str | None:
    if status == AssistantMessageStatus.INTERRUPTED:
        return "[interrupted]"
    if status == AssistantMessageStatus.FAILED:
        return "[failed]"
    return None


def _message_status_style(status: AssistantMessageStatus | None) -> str:
    if status == AssistantMessageStatus.FAILED:
        return TRANSCRIPT_FAILURE_STYLE
    return TRANSCRIPT_SYSTEM_STYLE


def _empty_transcript_text(state: TerminalConversationState) -> str:
    if state.header.mode == TerminalMode.STARTING:
        return "Starting session..."
    if state.header.mode == TerminalMode.HISTORICAL_ONLY:
        return "No transcript messages yet."
    return "Starting conversation..."


def _append_message(
    lines: list[TranscriptRenderLine],
    kind: ConversationMessageKind,
    text: str,
    width: int,
    status: AssistantMessageStatus | None,
) -> None:
    if lines:
        lines.append(TranscriptRenderLine(""))
    style = _message_style(kind)
    for raw_line in (text or "...").splitlines() or [""]:
        _append_wrapped_line(lines, raw_line, width, style)
    if marker := _message_status_marker(status):
        _append_wrapped_line(lines, marker, width, _message_status_style(status))


def _append_tool(
    lines: list[TranscriptRenderLine],
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> None:
    status = tool_status_label(tool, state)
    title = f"Tool: {truncate_middle(tool.tool_name, 32)} [{status}]"
    details = _compact_tool_details(tool, state, width)
    if tool.tool_call_id in state.expanded_tool_ids:
        details.extend(_expanded_tool_details(tool, width))
    _append_block(lines, title, "\n".join(details), width)


def _compact_tool_details(
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> list[str]:
    details: list[str] = []
    if tool.policy_outcome is not None:
        details.append(f"policy {enum_or_string_value(tool.policy_outcome)}")
    if tool.policy_risk_level is not None:
        details.append(f"risk {enum_or_string_value(tool.policy_risk_level)}")
    if tool.policy_source_label:
        details.append(f"source {truncate_middle(tool.policy_source_label, 28)}")
    elif tool.policy_source_kind is not None:
        details.append(f"source {enum_or_string_value(tool.policy_source_kind)}")
    if tool.summary:
        details.append(fit_line(tool.summary, max(width - 2, 12)))
    if tool.exit_code is not None:
        details.append(f"exit {tool.exit_code}")
    if (
        state.pending_approval is not None
        and state.pending_approval.tool_call_id == tool.tool_call_id
        and state.pending_approval.decision is None
    ):
        details.append("approval pending")
    if tool.output_preview:
        preview = fit_line(tool.output_preview.replace("\n", " "), max(width - 10, 12))
        suffix = " (truncated)" if tool.output_truncated else ""
        details.append(f"output: {preview}{suffix}")
    if tool.artifact_paths:
        paths = ", ".join(truncate_path(path, 30) for path in tool.artifact_paths)
        details.append(f"artifacts: {paths}")
    if not details:
        details.append("waiting for tool output")
    return details


def _expanded_tool_details(tool: ToolActivity, width: int) -> list[str]:
    details = ["details expanded"]
    if tool.arguments_json:
        details.append(f"args: {fit_line(tool.arguments_json, max(width - 8, 12))}")
    if tool.output_text:
        output = tool.output_text.replace("\n", "\\n")
        details.append(f"output full: {fit_line(output, max(width - 15, 12))}")
    if tool.artifact_paths:
        for path in tool.artifact_paths:
            details.append(f"artifact: {truncate_path(path, max(width - 12, 20))}")
    if tool.status == ToolActivityStatus.FAILED and tool.summary:
        details.append(f"failure: {fit_line(tool.summary, max(width - 11, 12))}")
    return details


def _append_block(
    lines: list[TranscriptRenderLine],
    title: str,
    text: str,
    width: int,
    *,
    title_style: str | None = TRANSCRIPT_SYSTEM_STYLE,
    body_style: str | None = None,
) -> None:
    if lines:
        lines.append(TranscriptRenderLine(""))
    lines.append(TranscriptRenderLine(fit_line(title, width), title_style))
    for raw_line in text.splitlines() or [""]:
        _append_wrapped_line(lines, raw_line, width, body_style)


def _append_wrapped_line(
    lines: list[TranscriptRenderLine],
    value: str,
    width: int,
    style: str | None,
) -> None:
    line_width = max(width, 12)
    if value.startswith("```"):
        lines.append(TranscriptRenderLine(fit_line(value, line_width), style))
        return
    wrapped = wrap(
        value,
        width=line_width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    if not wrapped:
        lines.append(TranscriptRenderLine("", style))
        return
    for line in wrapped:
        lines.append(TranscriptRenderLine(line, style))


def _plain_transcript_lines(text: str) -> list[TranscriptRenderLine]:
    return [TranscriptRenderLine(line) for line in text.splitlines() or [""]]
