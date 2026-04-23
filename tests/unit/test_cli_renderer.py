"""Unit tests for CLI event rendering decisions."""

from io import StringIO

from glassbox.cli.renderer import (
    CliEventRenderer,
    CliRenderState,
    format_event_for_terminal,
)
from glassbox.core import EventEnvelope, MessagePart
from glassbox.core.events import (
    ApprovalRequested,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    UserAnswerProvided,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    new_approval_id,
    new_message_id,
    new_session_id,
    new_tool_call_id,
    new_turn_id,
)


def test_renderer_buffers_assistant_deltas_until_completion() -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    state = CliRenderState()

    assert (
        format_event_for_terminal(
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=AssistantMessageStarted(message_id=message_id),
            ),
            state,
        )
        is None
    )
    assert (
        format_event_for_terminal(
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=AssistantMessageDelta(message_id=message_id, delta="Hello, "),
            ),
            state,
        )
        is None
    )

    rendered = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=3,
            payload=AssistantMessageCompleted(
                message_id=message_id,
                parts=[MessagePart(kind="text", text="world")],
            ),
        ),
        state,
    )

    assert rendered == "Assistant: world"


def test_renderer_uses_known_tool_name_for_completion_lines() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    state = CliRenderState()

    started_line = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=1,
            payload=ToolExecutionStarted(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                tool_name="search",
            ),
        ),
        state,
    )
    completed_line = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=2,
            payload=ToolExecutionCompleted(
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                success=True,
                exit_code=0,
                summary="found 3 results",
            ),
        ),
        state,
    )

    assert started_line == "Tool started: search"
    assert completed_line == (
        "Tool completed: search succeeded: found 3 results (exit code 0)"
    )


def test_renderer_outputs_approval_prompt_line() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    state = CliRenderState()

    rendered = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=1,
            payload=ApprovalRequested(
                approval_id=approval_id,
                turn_id=turn_id,
                reason="needs confirmation",
                subject="run shell command",
            ),
        ),
        state,
    )

    assert rendered == "Approval requested: run shell command (needs confirmation)"


def test_renderer_outputs_question_and_answer_lines() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    question_id = new_session_id()
    state = CliRenderState()

    question_line = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=1,
            payload=UserQuestionAsked(
                question_id=question_id,
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                provider_tool_call_id="provider-ask-1",
                question="What colour should I use?",
            ),
        ),
        state,
    )
    answer_line = format_event_for_terminal(
        EventEnvelope(
            session_id=session_id,
            sequence=2,
            payload=UserAnswerProvided(
                question_id=question_id,
                answer="blue",
            ),
        ),
        state,
    )

    assert question_line == (
        f"Question asked ({question_id}): What colour should I use?"
    )
    assert answer_line == f"Answer submitted for question {question_id}: blue"


def test_renderer_writes_only_visible_lines() -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    stream = StringIO()
    renderer = CliEventRenderer(stream)

    renderer.render_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=1,
                payload=AssistantMessageStarted(message_id=message_id),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=2,
                payload=AssistantMessageDelta(message_id=message_id, delta="Hello"),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=AssistantMessageCompleted(
                    message_id=message_id,
                    parts=[MessagePart(kind="text", text="Hello")],
                ),
            ),
        ]
    )

    assert stream.getvalue() == "Assistant: Hello\n"
