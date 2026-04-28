"""Reusable deterministic TUI workflow scenarios for terminal tests."""

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import replace

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import reduce_events
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionFailed
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
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


@dataclass(frozen=True, slots=True)
class TerminalWorkflowScenario:
    name: str
    snapshot: InteractiveSessionSnapshot
    events: tuple[EventEnvelope, ...]
    expected_mode: TerminalMode
    expected_action: TerminalActionKind
    transcript_contains: tuple[str, ...] = ()
    action_contains: tuple[str, ...] = ()
    header_contains: tuple[str, ...] = ()
    details_contains: tuple[str, ...] = ()
    state_transform: Callable[
        [TerminalConversationState], TerminalConversationState
    ] = lambda state: state


def terminal_workflow_scenarios() -> tuple[TerminalWorkflowScenario, ...]:
    return (
        _startup_scenario(),
        _initial_prompt_scenario(),
        _multi_turn_scenario(),
        _streaming_scenario(),
        _tool_activity_scenario(),
        _pending_approval_scenario(),
        _pending_question_scenario(),
        _prompt_conflict_scenario(),
        _failed_turn_scenario(),
        _dashboard_handoff_scenario(),
        _reconnect_scenario(),
        _historical_only_scenario(),
    )


def state_from_scenario(
    scenario: TerminalWorkflowScenario,
) -> TerminalConversationState:
    state = reduce_events(
        conversation_state_from_snapshot(scenario.snapshot),
        scenario.events,
    )
    return scenario.state_transform(state)


def _startup_scenario() -> TerminalWorkflowScenario:
    return TerminalWorkflowScenario(
        name="startup",
        snapshot=_snapshot(),
        events=(),
        expected_mode=TerminalMode.READY,
        expected_action=TerminalActionKind.PROMPT,
        transcript_contains=("Starting conversation",),
        header_contains=("Glassbox", "ready", "dashboard"),
    )


def _initial_prompt_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    turn_id = new_turn_id()
    return TerminalWorkflowScenario(
        name="initial prompt",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                UserMessageReceived(
                    message_id=user_message_id,
                    text="Inspect the workspace structure.",
                ),
            ),
            _event(
                session_id,
                2,
                TurnStarted(turn_id=turn_id, trigger_message_id=user_message_id),
            ),
            _event(
                session_id,
                3,
                AssistantMessageCompleted(
                    message_id=assistant_message_id,
                    parts=[MessagePart(kind="text", text="I found the source tree.")],
                ),
            ),
            _event(session_id, 4, TurnCompleted(turn_id=turn_id, outcome="completed")),
        ),
        expected_mode=TerminalMode.READY,
        expected_action=TerminalActionKind.PROMPT,
        transcript_contains=("Inspect the workspace", "I found the source tree"),
    )


def _multi_turn_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    first_user_id = new_message_id()
    second_user_id = new_message_id()
    first_turn_id = new_turn_id()
    second_turn_id = new_turn_id()
    return TerminalWorkflowScenario(
        name="multi-turn chat",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                UserMessageReceived(message_id=first_user_id, text="Find the bug."),
            ),
            _event(
                session_id,
                2,
                TurnStarted(turn_id=first_turn_id, trigger_message_id=first_user_id),
            ),
            _event(
                session_id,
                3,
                AssistantMessageCompleted(
                    message_id=new_message_id(),
                    parts=[MessagePart(kind="text", text="The bug is in parsing.")],
                ),
            ),
            _event(
                session_id,
                4,
                TurnCompleted(turn_id=first_turn_id, outcome="completed"),
            ),
            _event(
                session_id,
                5,
                UserMessageReceived(message_id=second_user_id, text="Patch it."),
            ),
            _event(
                session_id,
                6,
                TurnStarted(turn_id=second_turn_id, trigger_message_id=second_user_id),
            ),
            _event(
                session_id,
                7,
                AssistantMessageCompleted(
                    message_id=new_message_id(),
                    parts=[MessagePart(kind="text", text="Patch applied cleanly.")],
                ),
            ),
            _event(
                session_id,
                8,
                TurnCompleted(turn_id=second_turn_id, outcome="completed"),
            ),
        ),
        expected_mode=TerminalMode.READY,
        expected_action=TerminalActionKind.PROMPT,
        transcript_contains=("Find the bug", "Patch it", "Patch applied"),
        details_contains=("2 turns",),
    )


def _streaming_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    turn_id = new_turn_id()
    return TerminalWorkflowScenario(
        name="streaming assistant output",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                UserMessageReceived(
                    message_id=user_message_id,
                    text="Explain the diff.",
                ),
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
                AssistantMessageDelta(message_id=assistant_message_id, delta="Reading"),
            ),
            _event(
                session_id,
                5,
                AssistantMessageDelta(message_id=assistant_message_id, delta=" now"),
            ),
        ),
        expected_mode=TerminalMode.THINKING,
        expected_action=TerminalActionKind.ACTIVE_TURN_WAIT,
        transcript_contains=("Reading now",),
        action_contains=("Working", "assistant is still working"),
    )


def _tool_activity_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    return TerminalWorkflowScenario(
        name="tool activity",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                TurnStarted(turn_id=turn_id, trigger_message_id=new_message_id()),
            ),
            _event(
                session_id,
                2,
                ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                    arguments_json='{"path":"README.md"}',
                ),
            ),
            _event(
                session_id,
                3,
                ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file",
                ),
            ),
            _event(
                session_id,
                4,
                ToolOutputChunk(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    stream="stdout",
                    chunk="opened README.md",
                ),
            ),
            _event(
                session_id,
                5,
                ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind="text",
                    path="artifacts/readme.txt",
                ),
            ),
        ),
        expected_mode=TerminalMode.RUNNING_TOOL,
        expected_action=TerminalActionKind.ACTIVE_TURN_WAIT,
        details_contains=(
            "selected tool: read_file",
            "opened README.md",
            "artifacts/readme.txt",
        ),
    )


def _pending_approval_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    return TerminalWorkflowScenario(
        name="pending approval",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="shell",
                ),
            ),
            _event(
                session_id,
                2,
                ApprovalRequested(
                    approval_id=new_approval_id(),
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    subject="run uv test command",
                    reason="command execution",
                    policy_risk_level="command",
                    policy_source_label="confirm-shell",
                ),
            ),
        ),
        expected_mode=TerminalMode.AWAITING_APPROVAL,
        expected_action=TerminalActionKind.PENDING_APPROVAL,
        action_contains=("Approval: run uv test command", "Alt+A approve"),
        details_contains=("selected tool: shell [awaiting approval]",),
    )


def _pending_question_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    return TerminalWorkflowScenario(
        name="pending question",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                UserQuestionAsked(
                    question_id=new_question_id(),
                    turn_id=new_turn_id(),
                    tool_call_id=new_tool_call_id(),
                    provider_tool_call_id="ask-1",
                    question="Which test should I run?",
                ),
            ),
        ),
        expected_mode=TerminalMode.AWAITING_ANSWER,
        expected_action=TerminalActionKind.PENDING_QUESTION,
        action_contains=("Question: Which test should I run?", "Ctrl+R submit answer"),
    )


def _prompt_conflict_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    turn_id = new_turn_id()
    return TerminalWorkflowScenario(
        name="prompt conflict",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                TurnStarted(turn_id=turn_id, trigger_message_id=new_message_id()),
            ),
        ),
        expected_mode=TerminalMode.THINKING,
        expected_action=TerminalActionKind.ACTIVE_TURN_WAIT,
        action_contains=("Working", "assistant is still working"),
    )


def _failed_turn_scenario() -> TerminalWorkflowScenario:
    session_id = new_session_id()
    turn_id = new_turn_id()
    assistant_message_id = new_message_id()
    return TerminalWorkflowScenario(
        name="failed turn",
        snapshot=_snapshot(session_id=session_id),
        events=(
            _event(
                session_id,
                1,
                TurnStarted(turn_id=turn_id, trigger_message_id=new_message_id()),
            ),
            _event(
                session_id,
                2,
                AssistantMessageStarted(message_id=assistant_message_id),
            ),
            _event(
                session_id,
                3,
                AssistantMessageDelta(message_id=assistant_message_id, delta="Half"),
            ),
            _event(session_id, 4, TurnFailed(turn_id=turn_id, error_message="boom")),
            _event(session_id, 5, SessionFailed(error_message="boom", retryable=True)),
        ),
        expected_mode=TerminalMode.FAILED,
        expected_action=TerminalActionKind.FAILED,
        transcript_contains=("Half", "[failed]", "Turn failed"),
        action_contains=("Session failed", "boom"),
    )


def _dashboard_handoff_scenario() -> TerminalWorkflowScenario:
    return TerminalWorkflowScenario(
        name="dashboard handoff",
        snapshot=_snapshot(dashboard_url="http://127.0.0.1:8765/?session=abc"),
        events=(),
        expected_mode=TerminalMode.READY,
        expected_action=TerminalActionKind.PROMPT,
        header_contains=("dashboard",),
        details_contains=("dashboard:", "http://127.0.0.1:8765"),
    )


def _reconnect_scenario() -> TerminalWorkflowScenario:
    return TerminalWorkflowScenario(
        name="reconnect",
        snapshot=_snapshot(),
        events=(),
        expected_mode=TerminalMode.READY,
        expected_action=TerminalActionKind.PROMPT,
        header_contains=("reconnecting",),
        action_contains=("Ready",),
        state_transform=lambda state: with_stream_status(
            state,
            TerminalStreamStatus.RECONNECTING,
            detail="retry 2",
        ),
    )


def _historical_only_scenario() -> TerminalWorkflowScenario:
    snapshot = _snapshot(status=SessionStatus.COMPLETED)
    return TerminalWorkflowScenario(
        name="historical-only state",
        snapshot=replace(
            snapshot,
            state=snapshot.state.model_copy(update={"last_sequence": 12}),
        ),
        events=(),
        expected_mode=TerminalMode.HISTORICAL_ONLY,
        expected_action=TerminalActionKind.HISTORICAL_ONLY,
        action_contains=("Historical session",),
    )


def _snapshot(
    *,
    session_id=None,
    status: SessionStatus = SessionStatus.RUNNING,
    dashboard_url: str | None = "http://127.0.0.1:8765/?session=abc",
) -> InteractiveSessionSnapshot:
    return InteractiveSessionSnapshot(
        state=SessionState(
            session_id=session_id or new_session_id(),
            status=status,
            last_sequence=0,
        ),
        cwd="/workspace",
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        dashboard_url=dashboard_url,
    )


def _event(session_id, sequence, payload) -> EventEnvelope:
    return EventEnvelope(session_id=session_id, sequence=sequence, payload=payload)
