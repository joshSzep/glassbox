"""Terminal rendering for CLI-visible runtime events."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TextIO

from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    EventEnvelope,
    ModelToolCallRequested,
    SessionCompleted,
    SessionFailed,
    SessionResumed,
    SessionStarted,
    ToolArtifactRecorded,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    TurnFailed,
    UserMessageReceived,
)
from glassbox.core.ids import MessageId, ToolCallId
from glassbox.runtime import EventBusSubscription


@dataclass(slots=True)
class CliRenderState:
    """State required to render event streams coherently."""

    assistant_chunks: dict[MessageId, list[str]] = field(default_factory=dict)
    tool_names: dict[ToolCallId, str] = field(default_factory=dict)


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
        return f"Queued initial prompt: {payload.text}"

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
        return f"Tool requested: {payload.tool_name}"

    if isinstance(payload, ToolExecutionStarted):
        state.tool_names[payload.tool_call_id] = payload.tool_name
        return f"Tool started: {payload.tool_name}"

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
        return f"Approval requested: {payload.subject} ({payload.reason})"

    if isinstance(payload, ApprovalResolved):
        return f"Approval resolved: {payload.decision} by {payload.decided_by}"

    return None


class CliEventRenderer:
    """Render event envelopes into a text stream for the CLI."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._state = CliRenderState()

    def render_event(self, event: EventEnvelope) -> None:
        line = format_event_for_terminal(event, self._state)
        if line is None:
            return
        self._stream.write(f"{line}\n")
        self._stream.flush()

    def render_events(self, events: Iterable[EventEnvelope]) -> None:
        for event in events:
            self.render_event(event)

    async def render_subscription(
        self,
        subscription: EventBusSubscription[EventEnvelope],
    ) -> None:
        with suppress(asyncio.CancelledError):
            async for event in subscription:
                self.render_event(event)
