"""Tests for the pure terminal conversation state reducer."""

from datetime import UTC
from datetime import datetime

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import ToolActivityStatus
from glassbox.cli.tui.conversation import apply_event
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import reduce_events
from glassbox.cli.tui.conversation import terminal_action_from_state
from glassbox.cli.tui.conversation import with_composer_draft
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.conversation import with_tool_expanded
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
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
from glassbox.core.types import ApprovalDecision
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


def test_reducer_groups_trigger_message_and_assistant_stream_in_turn() -> None:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    turn_id = new_turn_id()

    state = reduce_events(
        _state(session_id),
        [
            _event(
                session_id,
                1,
                UserMessageReceived(message_id=user_message_id, text="Inspect this"),
            ),
            _event(
                session_id,
                2,
                TurnStarted(turn_id=turn_id, trigger_message_id=user_message_id),
            ),
            _event(
                session_id,
                3,
                AssistantMessageStarted(message_id=assistant_message_id),
            ),
            _event(
                session_id,
                4,
                AssistantMessageDelta(message_id=assistant_message_id, delta="On it"),
            ),
            _event(
                session_id,
                5,
                ModelCallCompleted(
                    turn_id=turn_id,
                    input_tokens=12,
                    output_tokens=8,
                    duration_ms=450,
                ),
            ),
        ],
    )

    turn = state.turns[0]
    assert [message.text for message in turn.messages] == ["Inspect this", "On it"]
    assert turn.messages[0].turn_id == turn_id
    assert turn.model_duration_ms == 450
    assert turn.model_input_tokens == 12
    assert turn.model_output_tokens == 8


def test_reducer_keeps_tool_metadata_preview_and_expansion_state() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    long_output = "x" * 200

    state = reduce_events(
        _state(session_id),
        [
            _event(
                session_id,
                1,
                ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="run_shell",
                    arguments_json='{"cmd":"pytest"}',
                    policy_outcome="approve",
                    policy_risk_level="command",
                    policy_source_kind="default",
                    policy_source_label="command",
                    policy_reason="shell command needs approval",
                ),
            ),
            _event(
                session_id,
                2,
                ToolOutputChunk(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    stream="stdout",
                    chunk=long_output,
                ),
            ),
            _event(
                session_id,
                3,
                ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    success=False,
                    exit_code=1,
                    summary="tests failed",
                ),
            ),
        ],
    )

    tool = state.turns[0].tools[0]
    assert tool.arguments_json == '{"cmd":"pytest"}'
    assert tool.policy_risk_level == "command"
    assert tool.policy_source_label == "command"
    assert tool.exit_code == 1
    assert tool.summary == "tests failed"
    assert tool.output_truncated is True
    assert tool.output_preview.endswith("...")

    state = with_tool_expanded(state, tool_call_id, expanded=True)
    assert tool_call_id in state.expanded_tool_ids
    state = with_tool_expanded(state, tool_call_id, expanded=False)
    assert tool_call_id not in state.expanded_tool_ids


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


def test_action_prioritizes_pending_approval_with_policy_and_tool_context() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    approval_id = new_approval_id()

    state = reduce_events(
        _state(session_id),
        [
            _event(
                session_id,
                1,
                ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="apply_patch",
                    policy_outcome="approve",
                    policy_risk_level="workspace_write",
                    policy_source_kind="default",
                    policy_source_label="workspace_write",
                ),
            ),
            _event(
                session_id,
                2,
                ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    subject="apply_patch",
                    reason="approval required",
                    policy_outcome="approve",
                    policy_risk_level="workspace_write",
                    policy_source_kind="default",
                    policy_source_label="workspace_write",
                ),
            ),
        ],
    )
    state = with_composer_draft(state, "/approve")

    action = terminal_action_from_state(state)

    assert action.kind == TerminalActionKind.PENDING_APPROVAL
    assert action.approval_id == approval_id
    assert action.related_tool_name == "apply_patch"
    assert action.policy_risk_level == "workspace_write"
    assert action.policy_source_label == "workspace_write"
    assert action.allowed_decisions
    assert action.answer_draft is None


def test_action_prioritizes_pending_question_with_matching_answer_draft() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    question_id = new_question_id()
    tool_call_id = new_tool_call_id()
    state = apply_event(
        _state(session_id),
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
    )
    state = with_composer_draft(state, "blue", question_id=question_id)

    action = terminal_action_from_state(state)

    assert action.kind == TerminalActionKind.PENDING_QUESTION
    assert action.question_id == question_id
    assert action.answer_draft == "blue"
    assert action.description == "Which color?"


def test_action_ignores_stale_resolved_approval_and_question() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    question_id = new_question_id()
    tool_call_id = new_tool_call_id()
    state = reduce_events(
        _state(session_id),
        [
            _event(
                session_id,
                1,
                ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run shell",
                    reason="approval required",
                ),
            ),
            _event(
                session_id,
                2,
                ApprovalResolved(
                    approval_id=approval_id,
                    decision=ApprovalDecision.APPROVED,
                    decided_by="user",
                ),
            ),
            _event(
                session_id,
                3,
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
                4,
                UserAnswerProvided(question_id=question_id, answer="blue"),
            ),
            _event(
                session_id,
                5,
                TurnCompleted(turn_id=turn_id, outcome="completed"),
            ),
        ],
    )

    action = terminal_action_from_state(state)

    assert action.kind == TerminalActionKind.PROMPT


def test_action_models_failed_historical_unavailable_and_active_wait_states() -> None:
    session_id = new_session_id()
    failed_state = apply_event(
        _state(session_id),
        _event(session_id, 1, SessionFailed(error_message="boom", retryable=False)),
    )
    historical_state = conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=session_id,
                status=SessionStatus.COMPLETED,
                last_sequence=10,
            )
        )
    )
    unavailable_state = with_stream_status(
        _state(session_id),
        TerminalStreamStatus.UNAVAILABLE,
        detail="daemon disconnected",
    )
    active_state = apply_event(
        _state(session_id),
        _event(
            session_id,
            1,
            TurnStarted(turn_id=new_turn_id(), trigger_message_id=new_message_id()),
        ),
    )

    assert terminal_action_from_state(failed_state).kind == TerminalActionKind.FAILED
    assert (
        terminal_action_from_state(historical_state).kind
        == TerminalActionKind.HISTORICAL_ONLY
    )
    assert (
        terminal_action_from_state(unavailable_state).kind
        == TerminalActionKind.UNAVAILABLE_PROMPT
    )
    assert (
        terminal_action_from_state(active_state).kind
        == TerminalActionKind.ACTIVE_TURN_WAIT
    )


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
    assert state.turns[0].turn_id == source_turn_id
    assert state.turns[0].messages[0].imported is True


def test_reducer_records_turn_failure_inside_group() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    state = apply_event(
        _state(session_id),
        _event(session_id, 1, TurnFailed(turn_id=turn_id, error_message="tool boom")),
    )

    assert state.turns[0].turn_id == turn_id
    assert state.turns[0].failure_message == "tool boom"
    assert state.failure is not None
    assert state.failure.message == "tool boom"


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
