"""Terminal rendering for CLI-visible runtime events."""

import asyncio
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from typing import TextIO

from glassbox.cli.policy_formatters import format_policy_suffix
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionResumed
from glassbox.core.events import SessionStarted
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import TurnFailed
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import MessageId
from glassbox.core.ids import ToolCallId
from glassbox.runtime.transport import RuntimeEventSubscription


@dataclass(slots=True)
class CliRenderState:
    """State required to render event streams coherently."""

    assistant_chunks: dict[MessageId, list[str]] = field(default_factory=dict)
    tool_names: dict[ToolCallId, str] = field(default_factory=dict)


@dataclass(slots=True)
class InteractivePromptState:
    """Current interactive prompt state while the CLI awaits operator input."""

    prompt_label: str | None = None
    context_lines: tuple[str, ...] = ()

    def activate(self, prompt_label: str, context_lines: Iterable[str]) -> None:
        self.prompt_label = prompt_label
        self.context_lines = tuple(context_lines)

    def clear(self) -> None:
        self.prompt_label = None
        self.context_lines = ()


def format_event_for_terminal(
    event: EventEnvelope,
    state: CliRenderState,
) -> str | None:
    """Convert one event into a stable terminal line when it is user-visible."""

    payload = event.payload

    if isinstance(payload, SessionStarted):
        return f"Started session {event.session_id} in {payload.cwd}"

    if isinstance(payload, SessionResumed):
        return (
            f"Resumed session {event.session_id} from sequence {payload.from_sequence}"
        )

    if isinstance(payload, SessionCompleted):
        return f"Session completed: {payload.reason}"

    if isinstance(payload, SessionFailed):
        return f"Session failed: {payload.error_message}"

    if isinstance(payload, TurnFailed):
        return f"Turn failed: {payload.error_message}"

    if isinstance(payload, UserMessageReceived):
        return f"Queued user message: {payload.text}"

    if isinstance(payload, UserQuestionAsked):
        return f"Question asked ({payload.question_id}): {payload.question}"

    if isinstance(payload, UserAnswerProvided):
        return f"Answer submitted for question {payload.question_id}: {payload.answer}"

    if isinstance(payload, AssistantMessageStarted):
        state.assistant_chunks[payload.message_id] = []
        return None

    if isinstance(payload, AssistantMessageDelta):
        state.assistant_chunks.setdefault(payload.message_id, []).append(payload.delta)
        return None

    if isinstance(payload, AssistantMessageCompleted):
        buffered_parts = state.assistant_chunks.pop(payload.message_id, [])
        text_parts = [part.text for part in payload.parts if part.kind == "text"]
        assistant_text = "".join(text_parts) if text_parts else "".join(buffered_parts)
        if not assistant_text:
            return "Assistant response completed"
        return f"Assistant: {assistant_text}"

    if isinstance(payload, ModelToolCallRequested):
        state.tool_names[payload.tool_call_id] = payload.tool_name
        policy_suffix = format_policy_suffix(
            outcome=payload.policy_outcome,
            risk_level=payload.policy_risk_level,
            source_kind=payload.policy_source_kind,
            source_label=payload.policy_source_label,
        )
        return f"Tool requested: {payload.tool_name}{policy_suffix}"

    if isinstance(payload, ToolExecutionStarted):
        state.tool_names[payload.tool_call_id] = payload.tool_name
        policy_suffix = format_policy_suffix(
            outcome=payload.policy_outcome,
            risk_level=payload.policy_risk_level,
            source_kind=payload.policy_source_kind,
            source_label=payload.policy_source_label,
        )
        return f"Tool started: {payload.tool_name}{policy_suffix}"

    if isinstance(payload, ToolArtifactRecorded):
        artifact_location = f" at {payload.path}" if payload.path else ""
        return f"Artifact recorded: {payload.artifact_kind}{artifact_location}"

    if isinstance(payload, ToolExecutionCompleted):
        tool_name = state.tool_names.get(
            payload.tool_call_id,
            str(payload.tool_call_id),
        )
        status = "succeeded" if payload.success else "failed"
        exit_suffix = (
            f" (exit code {payload.exit_code})" if payload.exit_code is not None else ""
        )
        return f"Tool completed: {tool_name} {status}: {payload.summary}{exit_suffix}"

    if isinstance(payload, ApprovalRequested):
        policy_suffix = format_policy_suffix(
            outcome=payload.policy_outcome,
            risk_level=payload.policy_risk_level,
            source_kind=payload.policy_source_kind,
            source_label=payload.policy_source_label,
        )
        return (
            f"Approval requested: {payload.subject} ({payload.reason}){policy_suffix}"
        )

    if isinstance(payload, ApprovalResolved):
        return f"Approval resolved: {payload.decision} by {payload.decided_by}"

    return None


class CliEventRenderer:
    """Render event envelopes into a text stream for the CLI."""

    def __init__(
        self,
        stream: TextIO,
        prompt_state: InteractivePromptState | None = None,
    ) -> None:
        self._stream = stream
        self._state = CliRenderState()
        self._prompt_state = prompt_state

    def render_event(self, event: EventEnvelope) -> None:
        line = format_event_for_terminal(event, self._state)
        if line is None:
            return
        prompt_state = self._prompt_state
        if prompt_state is not None and prompt_state.prompt_label is not None:
            self._stream.write("\n")
            self._stream.write(f"{line}\n")
            for context_line in prompt_state.context_lines:
                self._stream.write(f"{context_line}\n")
            self._stream.write(prompt_state.prompt_label)
        else:
            self._stream.write(f"{line}\n")
        self._stream.flush()

    def render_events(self, events: Iterable[EventEnvelope]) -> None:
        for event in events:
            self.render_event(event)

    async def render_subscription(
        self,
        subscription: RuntimeEventSubscription[EventEnvelope],
    ) -> None:
        with suppress(asyncio.CancelledError):
            async for event in subscription:
                self.render_event(event)
