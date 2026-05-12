"""Tests for the terminal command registry."""

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import command_from_slash
from glassbox.cli.tui.commands import command_item_by_id
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.commands import filter_command_items
from glassbox.cli.tui.commands import slash_command_from_text
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import reduce_events
from glassbox.cli.tui.conversation import with_composer_draft
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import SessionState
from glassbox.core.types import SessionStatus


def test_command_registry_exposes_expected_palette_actions() -> None:
    items = command_items_for_state(_state())
    command_ids = {item.spec.command_id for item in items}

    assert TerminalCommandId.STATUS in command_ids
    assert TerminalCommandId.OPEN_DASHBOARD in command_ids
    assert TerminalCommandId.COPY_SESSION_ID in command_ids
    assert TerminalCommandId.COPY_DASHBOARD_URL in command_ids
    assert TerminalCommandId.COPY_ARTIFACT_PATH in command_ids
    assert TerminalCommandId.OPEN_ARTIFACT_PATH in command_ids
    assert TerminalCommandId.TOGGLE_DETAILS in command_ids
    assert TerminalCommandId.TOGGLE_MARKDOWN in command_ids
    assert TerminalCommandId.JUMP_LATEST in command_ids
    assert TerminalCommandId.APPROVE in command_ids
    assert TerminalCommandId.DENY in command_ids
    assert TerminalCommandId.SUBMIT_ANSWER in command_ids
    assert TerminalCommandId.INTERRUPT in command_ids
    assert TerminalCommandId.CLEAR_TRANSCRIPT in command_ids
    assert TerminalCommandId.REVIEW_CREATE_CHANGESET in command_ids
    assert TerminalCommandId.REVIEW_OPERATOR_QUEUE in command_ids
    assert TerminalCommandId.REVIEW_NEXT_ACTIONS in command_ids
    assert TerminalCommandId.REVIEW_WORKUP_GUIDE in command_ids
    assert TerminalCommandId.REVIEW_REFRESH_INVENTORY in command_ids
    assert TerminalCommandId.REVIEW_OPEN_DASHBOARD in command_ids
    assert TerminalCommandId.REVIEW_GENERATE_BRIEF in command_ids
    assert TerminalCommandId.REVIEW_PREVIEW_VERIFICATION in command_ids
    assert TerminalCommandId.REVIEW_EVIDENCE_GRAPH in command_ids
    assert TerminalCommandId.REVIEW_INSPECT_HANDOFF in command_ids
    assert TerminalCommandId.REVIEW_MAINTENANCE_CHECKS in command_ids
    assert TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS in command_ids
    assert TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP in command_ids
    assert TerminalCommandId.QUIT in command_ids


def test_terminal_keybindings_route_core_app_actions() -> None:
    expected = {
        ("ctrl+escape", "quit"),
        ("ctrl+l", "latest"),
        ("ctrl+p", "command_palette"),
        ("ctrl+g", "focus_composer"),
        ("pageup", "transcript_page_up"),
        ("pagedown", "transcript_page_down"),
        ("ctrl+e", "toggle_details"),
        ("ctrl+d", "open_dashboard"),
        ("alt+d", "copy_dashboard_url"),
        ("alt+a", "approve"),
        ("alt+x", "deny"),
        ("ctrl+r", "submit_answer"),
        ("ctrl+c", "interrupt"),
        ("escape", "cancel_transient"),
    }

    assert expected.issubset(
        {(binding.key, binding.action) for binding in TUI_KEY_BINDINGS}
    )


def test_composer_keybindings_submit_and_insert_newline() -> None:
    assert any(
        binding.key == "enter" and binding.action == "submit_prompt"
        for binding in ComposerWidget.BINDINGS
    )
    assert any(
        binding.key == "ctrl+enter" and binding.action == "insert_newline"
        for binding in ComposerWidget.BINDINGS
    )


def test_command_registry_filters_by_title_description_and_slash_alias() -> None:
    items = command_items_for_state(_state())

    assert [item.spec.command_id for item in filter_command_items(items, "dash")] == [
        TerminalCommandId.OPEN_DASHBOARD,
        TerminalCommandId.COPY_DASHBOARD_URL,
        TerminalCommandId.REVIEW_OPEN_DASHBOARD,
    ]
    assert [
        item.spec.command_id for item in filter_command_items(items, "/latest")
    ] == [TerminalCommandId.JUMP_LATEST]
    markdown_command_ids = [
        item.spec.command_id for item in filter_command_items(items, "markdown")
    ]
    assert markdown_command_ids == [TerminalCommandId.TOGGLE_MARKDOWN]
    review_command_ids = [
        item.spec.command_id for item in filter_command_items(items, "/review")
    ]
    assert TerminalCommandId.REVIEW_CREATE_CHANGESET in review_command_ids
    assert TerminalCommandId.REVIEW_WORKUP_GUIDE in review_command_ids
    assert TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS in review_command_ids
    assert TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP in review_command_ids
    missing_fixup_command_ids = [
        item.spec.command_id for item in filter_command_items(items, "missing fixup")
    ]
    assert missing_fixup_command_ids == [TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS]
    queue_command_ids = [
        item.spec.command_id for item in filter_command_items(items, "queue")
    ]
    assert TerminalCommandId.REVIEW_OPERATOR_QUEUE in queue_command_ids
    assert TerminalCommandId.REVIEW_NEXT_ACTIONS in queue_command_ids
    assert TerminalCommandId.REVIEW_MAINTENANCE_CHECKS in queue_command_ids


def test_command_registry_reports_contextual_disabled_reasons() -> None:
    state = _state(dashboard_url=None)
    items = command_items_for_state(state)
    open_dashboard = command_item_by_id(items, TerminalCommandId.OPEN_DASHBOARD)
    approve = command_item_by_id(items, TerminalCommandId.APPROVE)
    submit_answer = command_item_by_id(items, TerminalCommandId.SUBMIT_ANSWER)
    copy_artifact = command_item_by_id(items, TerminalCommandId.COPY_ARTIFACT_PATH)
    review_dashboard = command_item_by_id(
        items, TerminalCommandId.REVIEW_OPEN_DASHBOARD
    )

    assert open_dashboard is not None
    assert approve is not None
    assert submit_answer is not None
    assert copy_artifact is not None
    assert review_dashboard is not None
    assert open_dashboard.disabled_reason == "dashboard unavailable"
    assert approve.disabled_reason == "no pending approval"
    assert submit_answer.disabled_reason == "no pending question"
    assert copy_artifact.disabled_reason == "no artifact path"
    assert review_dashboard.disabled_reason == "dashboard unavailable"


def test_command_registry_enables_approval_and_answer_commands() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    state = reduce_events(
        _state(session_id=session_id),
        [
            _event(
                session_id,
                1,
                ApprovalRequested(
                    approval_id=new_approval_id(),
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            ),
            _event(
                session_id,
                2,
                UserQuestionAsked(
                    question_id=new_question_id(),
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    provider_tool_call_id="ask-1",
                    question="Which file?",
                ),
            ),
        ],
    )
    state = with_composer_draft(state, "src/app.py")
    items = command_items_for_state(state)
    approve = command_item_by_id(items, TerminalCommandId.APPROVE)
    deny = command_item_by_id(items, TerminalCommandId.DENY)
    submit_answer = command_item_by_id(items, TerminalCommandId.SUBMIT_ANSWER)

    assert approve is not None
    assert deny is not None
    assert submit_answer is not None
    assert approve.enabled is True
    assert deny.enabled is True
    assert submit_answer.enabled is True


def test_command_from_slash_routes_compatibility_aliases() -> None:
    assert command_from_slash("/dashboard") == TerminalCommandId.OPEN_DASHBOARD
    assert command_from_slash("/markdown") == TerminalCommandId.TOGGLE_MARKDOWN
    assert command_from_slash("/md") == TerminalCommandId.TOGGLE_MARKDOWN
    assert command_from_slash("/copy-session now") == TerminalCommandId.COPY_SESSION_ID
    assert command_from_slash("/copy-artifact") == TerminalCommandId.COPY_ARTIFACT_PATH
    assert (
        command_from_slash("/review") == TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS
    )
    assert (
        command_from_slash("/review create")
        == TerminalCommandId.REVIEW_CREATE_CHANGESET
    )
    assert command_from_slash("/review workup") == TerminalCommandId.REVIEW_WORKUP_GUIDE
    assert command_from_slash("/queue") == TerminalCommandId.REVIEW_OPERATOR_QUEUE
    assert (
        command_from_slash("/operator queue") == TerminalCommandId.REVIEW_OPERATOR_QUEUE
    )
    assert command_from_slash("/next-actions") == TerminalCommandId.REVIEW_NEXT_ACTIONS
    assert (
        command_from_slash("/changeset brief")
        == TerminalCommandId.REVIEW_GENERATE_BRIEF
    )
    assert (
        command_from_slash("/review evidence-graph")
        == TerminalCommandId.REVIEW_EVIDENCE_GRAPH
    )
    assert (
        command_from_slash("/maintenance checks")
        == TerminalCommandId.REVIEW_MAINTENANCE_CHECKS
    )
    assert (
        command_from_slash("/review fixup 11111111-1111-1111-1111-111111111111")
        == TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP
    )
    assert command_from_slash("hello") is None
    assert command_from_slash("/unknown") is None


def test_slash_command_from_text_preserves_review_arguments() -> None:
    create = slash_command_from_text("/review create Tighten handoff docs")
    workup = slash_command_from_text(
        "/review workup 11111111-1111-1111-1111-111111111111"
    )
    brief = slash_command_from_text(
        "/changeset brief 11111111-1111-1111-1111-111111111111"
    )
    evidence = slash_command_from_text(
        "/evidence-graph 33333333-3333-3333-3333-333333333333"
    )
    fixup = slash_command_from_text(
        "/review fixup 22222222-2222-2222-2222-222222222222"
    )

    assert create is not None
    assert create.command_id == TerminalCommandId.REVIEW_CREATE_CHANGESET
    assert create.argument == "Tighten handoff docs"
    assert workup is not None
    assert workup.command_id == TerminalCommandId.REVIEW_WORKUP_GUIDE
    assert workup.argument == "11111111-1111-1111-1111-111111111111"
    assert brief is not None
    assert brief.command_id == TerminalCommandId.REVIEW_GENERATE_BRIEF
    assert brief.argument == "11111111-1111-1111-1111-111111111111"
    assert evidence is not None
    assert evidence.command_id == TerminalCommandId.REVIEW_EVIDENCE_GRAPH
    assert evidence.argument == "33333333-3333-3333-3333-333333333333"
    assert fixup is not None
    assert fixup.command_id == TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP
    assert fixup.argument == "22222222-2222-2222-2222-222222222222"


def _state(*, session_id=None, dashboard_url="http://127.0.0.1:8765/"):
    return conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=session_id or new_session_id(),
                status=SessionStatus.RUNNING,
            ),
            cwd="/workspace",
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            dashboard_url=dashboard_url,
        )
    )


def _event(session_id, sequence, payload) -> EventEnvelope:
    return EventEnvelope(session_id=session_id, sequence=sequence, payload=payload)
