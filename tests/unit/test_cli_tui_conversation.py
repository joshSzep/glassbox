"""Tests for the pure terminal conversation state reducer."""

from datetime import UTC
from datetime import datetime

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import ToolActivityStatus
from glassbox.cli.tui.conversation import apply_event
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import reduce_events
from glassbox.cli.tui.conversation import with_composer_draft
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionFailed
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_artifact_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import MessagePart
from glassbox.core.models import SessionState
from glassbox.core.types import SessionStatus


def test_reducer_builds_normal_conversation_from_events() -> None:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    turn_id = new_turn_id()
    state = _state(session_id)

    state = reduce_events(
        state,
        [
            _event(
                session_id,
                3,
                AssistantMessageCompleted(
                    message_id=assistant_message_id,
                    parts=[MessagePart(kind="text", text="Hello back")],
                ),
            ),
            _event(
                session_id,
                1,
                UserMessageReceived(message_id=user_message_id, text="Hello"),
            ),
            _event(
                session_id,
                2,
                TurnStarted(turn_id=turn_id, trigger_message_id=user_message_id),
            ),
            _event(
                session_id,
                4,
                TurnCompleted(turn_id=turn_id, outcome="completed"),
            ),
        ],
    )

    assert [message.text for message in state.messages] == ["Hello", "Hello back"]
    assert state.messages[-1].status == AssistantMessageStatus.COMPLETED
    assert state.turns[0].completed_outcome == "completed"
    assert state.header.mode == TerminalMode.READY
    assert state.header.last_sequence == 4


def test_reducer_tracks_live_assistant_streaming_text() -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    state = _state(session_id)

    state = reduce_events(
        state,
        [
            _event(session_id, 1, AssistantMessageStarted(message_id=message_id)),
            _event(
                session_id, 2, AssistantMessageDelta(message_id=message_id, delta="Hel")
            ),
            _event(
                session_id, 3, AssistantMessageDelta(message_id=message_id, delta="lo")
            ),
        ],
    )

    assert state.messages[0].text == "Hello"
    assert state.messages[0].status == AssistantMessageStatus.STREAMING


def test_reducer_tracks_tool_heavy_turn_state() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    state = _state(session_id)

    state = reduce_events(
        state,
        [
            _event(
                session_id,
                1,
                ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                    arguments_json='{"path":"README.md"}',
                ),
            ),
            _event(
                session_id,
                2,
                ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                ),
            ),
            _event(
                session_id,
                3,
                ToolOutputChunk(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    stream="stdout",
                    chunk="line 1",
                ),
            ),
            _event(
                session_id,
                4,
                ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind="text",
                    path="artifacts/readme.txt",
                ),
            ),
            _event(
                session_id,
                5,
                ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    success=True,
                    summary="read README",
                ),
            ),
        ],
    )

    tool = state.turns[0].tools[0]
    assert tool.tool_name == "read_file"
    assert tool.status == ToolActivityStatus.SUCCEEDED
    assert tool.output == ("line 1",)
    assert tool.artifact_paths == ("artifacts/readme.txt",)
    assert state.header.mode == TerminalMode.RUNNING_TOOL


def test_reducer_tracks_pending_approval_and_resolution() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    state = _state(session_id)

    state = apply_event(
        state,
        _event(
            session_id,
            1,
            ApprovalRequested(
                approval_id=approval_id,
                turn_id=turn_id,
                subject="apply_patch",
                reason="approval required",
            ),
        ),
    )

    assert state.pending_approval is not None
    assert state.pending_approval.subject == "apply_patch"
    assert state.header.mode == TerminalMode.AWAITING_APPROVAL


def test_reducer_tracks_pending_question_and_answer() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    question_id = new_question_id()
    tool_call_id = new_tool_call_id()
    state = _state(session_id)

    state = reduce_events(
        state,
        [
            _event(
                session_id,
                1,
                UserQuestionAsked(
                    question_id=question_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    provider_tool_call_id="provider-ask-1",
                    question="Which color?",
                ),
            ),
            _event(
                session_id,
                2,
                UserAnswerProvided(question_id=question_id, answer="blue"),
            ),
        ],
    )

    assert state.pending_question is not None
    assert state.pending_question.answer == "blue"
    assert state.header.mode == TerminalMode.THINKING


def test_reducer_tracks_failure_states() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    state = reduce_events(
        _state(session_id),
        [
            _event(session_id, 1, TurnFailed(turn_id=turn_id, error_message="boom")),
            _event(
                session_id,
                2,
                SessionFailed(error_message="session boom", retryable=True),
            ),
        ],
    )

    assert state.failure is not None
    assert state.failure.message == "session boom"
    assert state.failure.retryable is True
    assert state.header.mode == TerminalMode.FAILED


def test_reducer_preserves_partial_imported_history() -> None:
    session_id = new_session_id()
    source_session_id = new_session_id()
    source_message_id = new_message_id()
    source_turn_id = new_turn_id()
    message_id = new_message_id()
    state = apply_event(
        _state(session_id),
        _event(
            session_id,
            1,
            TranscriptMessageImported(
                message_id=message_id,
                source_session_id=source_session_id,
                source_message_id=source_message_id,
                source_turn_id=source_turn_id,
                role="assistant",
                parts=[MessagePart(kind="text", text="Inherited answer")],
                source_created_at=_ZERO_TIME,
            ),
        ),
    )

    assert state.messages[0].imported is True
    assert state.messages[0].text == "Inherited answer"
    assert state.messages[0].turn_id == source_turn_id


def test_reducer_keeps_composer_draft_separate_from_events() -> None:
    session_id = new_session_id()
    state = with_composer_draft(_state(session_id), "draft text")
    state = apply_event(
        state,
        _event(
            session_id, 1, UserMessageReceived(message_id=new_message_id(), text="sent")
        ),
    )

    assert state.composer.text == "draft text"
    assert state.messages[0].text == "sent"


def test_reducer_models_reconnect_and_historical_only_stream_status() -> None:
    session_id = new_session_id()
    state = with_stream_status(
        _state(session_id),
        TerminalStreamStatus.RECONNECTING,
        detail="retrying",
    )

    assert state.header.stream_status == TerminalStreamStatus.RECONNECTING
    assert state.header.stream_detail == "retrying"

    historical_state = conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=session_id,
                status=SessionStatus.COMPLETED,
                last_sequence=10,
            )
        )
    )

    assert historical_state.header.mode == TerminalMode.HISTORICAL_ONLY
    assert historical_state.header.stream_status == TerminalStreamStatus.HISTORICAL_ONLY


def _state(session_id):
    return conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=session_id,
                status=SessionStatus.RUNNING,
            ),
            cwd="/workspace",
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            dashboard_url="http://127.0.0.1:8765/",
        )
    )


def _event(session_id, sequence, payload) -> EventEnvelope:
    return EventEnvelope(
        session_id=session_id,
        sequence=sequence,
        payload=payload,
    )


_ZERO_TIME = datetime.fromtimestamp(0, tz=UTC)
