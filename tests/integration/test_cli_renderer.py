"""Integration tests for rendering a fake event stream into terminal output."""

import asyncio
from contextlib import suppress
from io import StringIO

from glassbox.cli.renderer import CliEventRenderer, InteractivePromptState
from glassbox.core import EventEnvelope, MessagePart
from glassbox.core.events import (
    ApprovalRequested,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    SessionStarted,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    new_approval_id,
    new_message_id,
    new_session_id,
    new_tool_call_id,
    new_turn_id,
)
from glassbox.runtime import EventBus


def test_renderer_renders_representative_fake_event_stream() -> None:
    output = asyncio.run(_render_fake_stream())

    assert "Started session" in output
    assert "Tool started: search" in output
    assert "Tool completed: search succeeded: found 3 results (exit code 0)" in output
    assert "Approval requested: run shell command (needs confirmation)" in output
    assert "Assistant: Here is the answer." in output


def test_renderer_redraws_prompt_context_when_events_arrive_mid_prompt() -> None:
    output = asyncio.run(_render_fake_stream_with_active_prompt())

    assert "Question asked (" in output
    assert (
        "Interactive mode: type the next prompt, or use /status, /help, or /exit.\n"
        "prompt> "
    ) in output


async def _render_fake_stream() -> str:
    session_id = new_session_id()
    message_id = new_message_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    stream = StringIO()
    renderer = CliEventRenderer(stream)
    bus: EventBus[EventEnvelope] = EventBus()

    async with bus.subscribe() as subscription:
        render_task = asyncio.create_task(renderer.render_subscription(subscription))
        try:
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=1,
                    payload=SessionStarted(
                        cwd="/tmp/workspace",
                        dashboard_url="http://127.0.0.1:8765",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=2,
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="search",
                    ),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=3,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        exit_code=0,
                        summary="found 3 results",
                    ),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=4,
                    payload=ApprovalRequested(
                        approval_id=new_approval_id(),
                        turn_id=turn_id,
                        reason="needs confirmation",
                        subject="run shell command",
                    ),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=5,
                    payload=AssistantMessageStarted(message_id=message_id),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=6,
                    payload=AssistantMessageDelta(
                        message_id=message_id,
                        delta="Here is ",
                    ),
                )
            )
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=7,
                    payload=AssistantMessageCompleted(
                        message_id=message_id,
                        parts=[MessagePart(kind="text", text="Here is the answer.")],
                    ),
                )
            )
            await asyncio.sleep(0)
        finally:
            render_task.cancel()
            with suppress(asyncio.CancelledError):
                await render_task

    return stream.getvalue()


async def _render_fake_stream_with_active_prompt() -> str:
    session_id = new_session_id()
    turn_id = new_turn_id()
    stream = StringIO()
    prompt_state = InteractivePromptState()
    renderer = CliEventRenderer(stream, prompt_state=prompt_state)
    bus: EventBus[EventEnvelope] = EventBus()

    prompt_state.activate(
        "prompt> ",
        [
            "Interactive mode: type the next prompt, or use /status, /help, or /exit.",
        ],
    )
    stream.write("prompt> ")

    async with bus.subscribe() as subscription:
        render_task = asyncio.create_task(renderer.render_subscription(subscription))
        try:
            bus.publish(
                EventEnvelope(
                    session_id=session_id,
                    sequence=1,
                    payload=UserQuestionAsked(
                        question_id=new_session_id(),
                        turn_id=turn_id,
                        tool_call_id=new_tool_call_id(),
                        provider_tool_call_id="provider-ask-1",
                        question="What colour should I use?",
                    ),
                )
            )
            await asyncio.sleep(0)
        finally:
            render_task.cancel()
            await render_task

    return stream.getvalue()
