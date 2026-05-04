"""Interactive terminal session control and prompt-routing helpers."""

import asyncio
from collections.abc import Sequence
from uuid import UUID

from glassbox.cli.interactive_review_commands import _execute_interactive_review_command
from glassbox.cli.renderer import InteractivePromptState
from glassbox.cli.status_formatters import _format_next_action_line
from glassbox.cli.status_formatters import _format_pending_question_line
from glassbox.cli.status_formatters import _latest_session_failure
from glassbox.cli.status_formatters import _pending_question_text_from_events
from glassbox.cli.status_formatters import _print_session_status
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.session_queries import SessionQueryService


async def _interactive_session_loop(
    runtime_context: RuntimeContext,
    session_id: UUID,
    prompt_state: InteractivePromptState,
    dashboard_url: str | None = None,
) -> None:
    repository = runtime_context.repositories.sessions
    prompt_state.clear()

    while True:
        state = repository.get_session_state(session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {session_id}")

        mode = _interactive_mode(state)
        prompt_context_lines = _interactive_prompt_context_lines(
            repository,
            session_id,
            state,
            mode,
        )
        _render_interactive_prompt_context(prompt_context_lines)

        if mode == "paused":
            prompt_state.clear()
            return

        prompt_label = _interactive_prompt_label(mode)
        prompt_state.activate(prompt_label, prompt_context_lines)
        try:
            user_input = await _read_interactive_input_async(prompt_label)
        except EOFError, KeyboardInterrupt:
            prompt_state.clear()
            print()
            print(f"Leaving interactive session {session_id}")
            return
        finally:
            prompt_state.clear()

        state = repository.get_session_state(session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        mode = _interactive_mode(state)

        action_kind, action_value = _parse_interactive_input(user_input)
        if action_kind == "continue":
            continue
        if action_kind == "exit":
            print(f"Leaving interactive session {session_id}")
            return
        if action_kind == "help":
            print(_interactive_help_text(mode))
            continue
        if action_kind == "status":
            query_service = SessionQueryService(
                repository,
                runtime_context.repositories.artifacts,
            )
            _print_session_status(query_service.get_session_status_view(session_id))
            continue
        if action_kind == "review":
            await _execute_interactive_review_command(
                runtime_context,
                session_id,
                action_value,
                dashboard_url=dashboard_url,
            )
            continue
        if action_kind == "approve":
            if state.status != SessionStatus.AWAITING_APPROVAL:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            approval_id = state.pending_approval_id
            if approval_id is None:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            await runtime_context.services.session_service.resolve_approval(
                session_id,
                approval_id,
                ApprovalDecision.APPROVED,
            )
            await asyncio.sleep(0)
            continue
        if action_kind == "deny":
            if state.status != SessionStatus.AWAITING_APPROVAL:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            approval_id = state.pending_approval_id
            if approval_id is None:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            await runtime_context.services.session_service.resolve_approval(
                session_id,
                approval_id,
                ApprovalDecision.DENIED,
            )
            await asyncio.sleep(0)
            continue
        if action_kind == "submit":
            if mode == "prompt":
                await runtime_context.services.session_service.submit_user_message(
                    session_id,
                    action_value,
                )
                await asyncio.sleep(0)
                continue
            if mode == "answer":
                question_id = state.pending_question_id
                if question_id is None:
                    print(_interactive_blocked_input_message(state, session_id))
                    continue
                await runtime_context.services.session_service.provide_user_answer(
                    session_id,
                    question_id,
                    action_value,
                )
                await asyncio.sleep(0)
                continue
            print(_interactive_blocked_input_message(state, session_id))
            continue


def _can_accept_interactive_chat_prompt(state: SessionState) -> bool:
    return state.status == SessionStatus.RUNNING and state.current_turn_id is None


def _can_accept_interactive_answer(state: SessionState) -> bool:
    return (
        state.status == SessionStatus.AWAITING_USER_INPUT
        and state.pending_question_id is not None
    )


def _interactive_mode(state: SessionState) -> str:
    if _can_accept_interactive_chat_prompt(state):
        return "prompt"
    if _can_accept_interactive_answer(state):
        return "answer"
    if state.status == SessionStatus.AWAITING_APPROVAL:
        return "approval"
    return "paused"


def _read_interactive_input(prompt: str) -> str:
    return input(prompt)


async def _read_interactive_input_async(prompt: str) -> str:
    return await asyncio.to_thread(_read_interactive_input, prompt)


def _parse_interactive_input(user_input: str) -> tuple[str, str]:
    trimmed = user_input.strip()
    if not trimmed:
        return "continue", ""
    if trimmed == "/exit":
        return "exit", ""
    if trimmed == "/help":
        return "help", ""
    if trimmed == "/status":
        return "status", ""
    if trimmed == "/approve":
        return "approve", ""
    if trimmed == "/deny":
        return "deny", ""
    if trimmed.startswith("/review") or trimmed.startswith("/changeset"):
        return "review", trimmed
    if trimmed.startswith("/"):
        print("Unknown interactive command. Use /help for available commands.")
        return "continue", ""
    return "submit", user_input


def _ensure_session_can_attach(session_id: UUID, state: SessionState) -> None:
    if state.status in {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }:
        raise ValueError(f"cannot attach session {session_id} in status {state.status}")

    if state.status == SessionStatus.RUNNING and state.current_turn_id is not None:
        raise ValueError(
            f"cannot attach session {session_id} while turn "
            f"{state.current_turn_id} is still active"
        )


def _current_turn_id(
    state: SessionState,
    approvals: Sequence[ApprovalRecord],
) -> UUID | None:
    if state.current_turn_id is not None:
        return state.current_turn_id
    if state.status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def _format_interactive_chat_pause_line(
    repository,
    session_id: UUID,
    state: SessionState,
) -> str:
    session_events = repository.read_session_events(session_id)
    pending_approvals = repository.list_approvals(session_id)
    latest_session_failure = _latest_session_failure(session_events)
    current_turn_id = _current_turn_id(state, pending_approvals)
    next_action = _format_next_action_line(
        session_id,
        state.status,
        current_turn_id,
        state.pending_approval_id,
        state.pending_question_id,
        latest_session_failure,
    )
    return f"Interactive chat paused. {next_action}"


def _interactive_prompt_label(mode: str) -> str:
    if mode == "prompt":
        return "prompt> "
    if mode == "answer":
        return "answer> "
    if mode == "approval":
        return "approval> "
    return "session> "


def _interactive_prompt_context_lines(
    repository,
    session_id: UUID,
    state: SessionState,
    mode: str,
) -> list[str]:
    if mode == "answer":
        session_events = repository.read_session_events(session_id)
        question_text = _pending_question_text_from_events(
            session_events,
            state.pending_question_id,
        )
        return [
            _format_pending_question_line(
                state.pending_question_id,
                question_text,
            ),
            "Interactive mode: answer the pending question, or use /status, "
            "/help, or /exit.",
        ]
    if mode == "approval":
        return [
            _interactive_blocked_input_message(state, session_id),
            "Interactive mode: use /approve, /deny, /status, /help, or /exit.",
        ]
    if mode == "prompt":
        return [
            "Interactive mode: type the next prompt, or use /status, /help, or /exit."
        ]
    return [_format_interactive_chat_pause_line(repository, session_id, state)]


def _render_interactive_prompt_context(context_lines: Sequence[str]) -> None:
    for context_line in context_lines:
        print(context_line)


def _interactive_blocked_input_message(state: SessionState, session_id: UUID) -> str:
    if state.status == SessionStatus.AWAITING_APPROVAL:
        approval_id = state.pending_approval_id
        if approval_id is None:
            return (
                "This session is awaiting approval resolution. Use /status or "
                "/help for more detail."
            )
        return (
            "This session is awaiting approval resolution for "
            f"{approval_id}. Freeform text is disabled until you use /approve "
            "or /deny."
        )

    next_action = _format_next_action_line(
        session_id,
        state.status,
        state.current_turn_id,
        state.pending_approval_id,
        state.pending_question_id,
        None,
    )
    return (
        "This session cannot accept freeform interactive input right now. "
        f"{next_action}"
    )


def _interactive_help_text(mode: str) -> str:
    lines = [
        "Interactive commands:",
        "  /status  show the full session status",
        "  /review create [OBJECTIVE] create local changeset evidence",
        "  /review status [CHANGESET_ID] inspect feedback and response posture",
        "  /review refresh CHANGESET_ID refresh structured inventory evidence",
        "  /review brief CHANGESET_ID generate a lifecycle review brief",
        "  /review verify CHANGESET_ID preview verification without running commands",
        "  /review handoff CHANGESET_ID inspect handoff readiness without publishing",
        "  /review dashboard CHANGESET_ID print the dashboard review URL",
        "  /changeset ... compatibility alias for /review ...",
        "  /help    show interactive command help",
        "  /exit    leave the interactive session",
        "  /approve approve the pending action when awaiting approval",
        "  /deny    deny the pending action when awaiting approval",
    ]
    if mode == "prompt":
        lines.append("Freeform input sends the next user prompt.")
    elif mode == "answer":
        lines.append("Freeform input answers the pending ask_user question.")
    elif mode == "approval":
        lines.append("Freeform input is disabled while the session awaits approval.")
    return "\n".join(lines)
