"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer
from glassbox.core import SessionConfig, TranscriptMessage
from glassbox.core.events import (
    EventEnvelope,
    SessionFailed,
    SessionStarted,
    UserQuestionAsked,
)
from glassbox.core.models import (
    ApprovalRecord,
    SessionState,
    ToolCallRecord,
    TurnMetricsRecord,
)
from glassbox.core.types import ApprovalDecision, SessionStatus
from glassbox.runtime import RuntimeContext, open_runtime_context

_APPROVAL_MODE_CHOICES = ("confirm", "review", "on-request", "never")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Glassbox CLI."""

    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "run":
            return _run_command(args)
        if args.command == "chat":
            return _chat_command(args)
        if args.command == "attach":
            return _attach_command(args)
        if args.command == "message":
            return _message_command(args)
        if args.command == "resume":
            return _resume_command(args)
        if args.command == "status":
            return _status_command(args)
        if args.command == "answer":
            return _answer_command(args)
        if args.command == "approve":
            return _resolve_approval_command(args, ApprovalDecision.APPROVED)
        if args.command == "deny":
            return _resolve_approval_command(args, ApprovalDecision.DENIED)
        if args.command == "rebuild":
            return _rebuild_command(args)
        if args.command == "serve":
            return _serve_command(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"database operation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glassbox",
        description="Run the Glassbox local-first CLI agent and dashboard runtime.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="start a new session",
        description="Start a new session and optionally submit an initial prompt.",
    )
    run_parser.add_argument("prompt", nargs="?", help="optional initial user prompt")
    _add_runtime_location_arguments(run_parser)
    run_parser.add_argument(
        "--model-name",
        default="openai:gpt-5.4",
        help="model identifier recorded in the session metadata",
    )
    run_parser.add_argument(
        "--approval-mode",
        default="confirm",
        choices=_APPROVAL_MODE_CHOICES,
        help="approval mode for risky tool actions",
    )

    chat_parser = subparsers.add_parser(
        "chat",
        help="start a new interactive session",
        description=(
            "Start a new session and keep the terminal open for follow-up "
            "prompts. Type /exit to leave the interactive session."
        ),
    )
    chat_parser.add_argument("prompt", nargs="?", help="optional initial user prompt")
    _add_runtime_location_arguments(chat_parser)
    chat_parser.add_argument(
        "--model-name",
        default="openai:gpt-5.4",
        help="model identifier recorded in the session metadata",
    )
    chat_parser.add_argument(
        "--approval-mode",
        default="confirm",
        choices=_APPROVAL_MODE_CHOICES,
        help="approval mode for risky tool actions",
    )

    attach_parser = subparsers.add_parser(
        "attach",
        help="attach to an existing interactive session",
        description=(
            "Open an interactive terminal workflow for an existing session. "
            "Type /exit to leave the attached session."
        ),
    )
    attach_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(attach_parser)

    message_parser = subparsers.add_parser(
        "message",
        help="submit a new prompt to an existing session",
        description="Submit a new user message into an existing session.",
    )
    message_parser.add_argument("session_id", type=_parse_uuid)
    message_parser.add_argument("prompt", help="user prompt to submit")
    _add_runtime_location_arguments(message_parser)

    answer_parser = subparsers.add_parser(
        "answer",
        help="answer a pending ask_user question",
        description=(
            "Submit an answer to a pending ask_user question in an existing "
            "session. Use the question_id from the earlier 'Question asked' "
            "CLI output line."
        ),
    )
    answer_parser.add_argument(
        "session_id",
        type=_parse_uuid,
        help="session identifier that is awaiting user input",
    )
    answer_parser.add_argument(
        "question_id",
        type=_parse_uuid,
        help="question identifier shown when the session asked for input",
    )
    answer_parser.add_argument("answer", help="answer text to provide")
    _add_runtime_location_arguments(answer_parser)

    resume_parser = subparsers.add_parser(
        "resume",
        help="resume an existing session",
        description="Replay the resume event for an existing session.",
    )
    resume_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(resume_parser)

    status_parser = subparsers.add_parser(
        "status",
        help="inspect session state",
        description=(
            "Print the current session state, approvals, tool activity, "
            "and recent metrics."
        ),
    )
    status_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(status_parser)

    approve_parser = subparsers.add_parser(
        "approve",
        help="approve a pending action",
        description="Approve a pending tool action and resume the suspended turn.",
    )
    approve_parser.add_argument("session_id", type=_parse_uuid)
    approve_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(approve_parser)

    deny_parser = subparsers.add_parser(
        "deny",
        help="deny a pending action",
        description=(
            "Deny a pending tool action and resume the suspended turn "
            "without running it."
        ),
    )
    deny_parser.add_argument("session_id", type=_parse_uuid)
    deny_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(deny_parser)

    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="rebuild derived projections",
        description="Rebuild projection tables from canonical persisted events.",
    )
    rebuild_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    rebuild_parser.add_argument(
        "--all",
        action="store_true",
        help="rebuild projections for all sessions in the database",
    )
    _add_runtime_location_arguments(rebuild_parser)

    serve_parser = subparsers.add_parser(
        "serve",
        help="start the dashboard server",
        description=(
            "Start the web dashboard server for the selected workspace database."
        ),
    )
    _add_runtime_location_arguments(serve_parser)
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the server to",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="port to bind the server to",
    )

    return parser


def _add_runtime_location_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cwd",
        default=".",
        help="workspace directory associated with the session database",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="override the SQLite database path",
    )


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID: {value}") from exc


def _resolve_runtime_location(args: argparse.Namespace) -> tuple[Path, Path | None]:
    cwd = Path(args.cwd).resolve()
    db_path = Path(args.db_path).resolve() if args.db_path is not None else None
    return cwd, db_path


def _run_command(args: argparse.Namespace) -> int:
    return asyncio.run(_run_command_async(args))


async def _run_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)
    config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    async def action(runtime_context: RuntimeContext) -> None:
        session_state = await runtime_context.services.session_service.start_session(
            config
        )
        await asyncio.sleep(0)
        if args.prompt:
            await runtime_context.services.session_service.submit_user_message(
                session_state.session_id,
                args.prompt,
            )
            await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _chat_command(args: argparse.Namespace) -> int:
    return asyncio.run(_chat_command_async(args))


async def _chat_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)
    config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    async def action(runtime_context: RuntimeContext) -> None:
        session_state = await runtime_context.services.session_service.start_session(
            config
        )
        await asyncio.sleep(0)
        if args.prompt:
            await runtime_context.services.session_service.submit_user_message(
                session_state.session_id,
                args.prompt,
            )
            await asyncio.sleep(0)
        print(f"Attached to session {session_state.session_id}")
        await _interactive_session_loop(runtime_context, session_state.session_id)

    return await _run_with_renderer(cwd, db_path, action)


def _attach_command(args: argparse.Namespace) -> int:
    return asyncio.run(_attach_command_async(args))


async def _attach_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        repository = runtime_context.repositories.sessions
        state = repository.get_session_state(args.session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")

        _ensure_session_can_attach(args.session_id, state)
        print(f"Attached to session {args.session_id}")
        await _interactive_session_loop(runtime_context, args.session_id)

    return await _run_with_renderer(cwd, db_path, action)


def _resume_command(args: argparse.Namespace) -> int:
    return asyncio.run(_resume_command_async(args))


async def _resume_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.resume_session(args.session_id)
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _message_command(args: argparse.Namespace) -> int:
    return asyncio.run(_message_command_async(args))


async def _message_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.submit_user_message(
            args.session_id,
            args.prompt,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _answer_command(args: argparse.Namespace) -> int:
    return asyncio.run(_answer_command_async(args))


async def _answer_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.provide_user_answer(
            args.session_id,
            args.question_id,
            args.answer,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _status_command(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        _print_session_status(runtime_context.repositories.sessions, args.session_id)

    return 0


async def _interactive_session_loop(
    runtime_context: RuntimeContext,
    session_id: UUID,
) -> None:
    repository = runtime_context.repositories.sessions

    while True:
        state = repository.get_session_state(session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {session_id}")

        mode = _interactive_mode(state)
        _render_interactive_prompt_context(repository, session_id, state, mode)

        if mode == "paused":
            return

        try:
            user_input = _read_interactive_input(_interactive_prompt_label(mode))
        except EOFError, KeyboardInterrupt:
            print()
            print(f"Leaving interactive session {session_id}")
            return

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
            _print_session_status(repository, session_id)
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


def _rebuild_command(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    if args.all == (args.session_id is not None):
        raise ValueError("specify exactly one of session_id or --all")

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions

        if args.all:
            sessions = repository.list_sessions()
            if not sessions:
                print("No sessions found to rebuild")
                return 0

            for session in sessions:
                repository.rebuild_session_projections(session.session_id)
                print(f"Rebuilt projections for session {session.session_id}")
            print(f"Rebuilt projections for {len(sessions)} session(s)")
            return 0

        session_id = args.session_id
        assert session_id is not None
        if repository.get_session(session_id) is None:
            raise ValueError(f"unknown session_id: {session_id}")

        repository.rebuild_session_projections(session_id)
        print(f"Rebuilt projections for session {session_id}")
        return 0


def _latest_message_summary(
    transcript_messages: Sequence[TranscriptMessage],
) -> str | None:
    if not transcript_messages:
        return None

    latest_message = transcript_messages[-1]
    text = " ".join(
        part.text.strip().replace("\n", " ")
        for part in latest_message.parts
        if part.text.strip()
    ).strip()
    if not text:
        return latest_message.role
    return f"{latest_message.role}: {text}"


def _current_turn_id(
    state,
    approvals: Sequence[ApprovalRecord],
) -> UUID | None:
    if state.current_turn_id is not None:
        return state.current_turn_id
    if state.status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def _find_turn_metrics(
    turn_metrics: Sequence[TurnMetricsRecord],
    turn_id: UUID | None,
) -> TurnMetricsRecord | None:
    if turn_id is None:
        return None
    for metrics in turn_metrics:
        if metrics.turn_id == turn_id:
            return metrics
    return None


def _recent_tool_calls(
    tool_calls: Sequence[ToolCallRecord],
    *,
    limit: int = 3,
) -> list[ToolCallRecord]:
    def sort_key(tool_call: ToolCallRecord) -> datetime:
        return tool_call.completed_at or tool_call.started_at or datetime.min

    return sorted(tool_calls, key=sort_key, reverse=True)[:limit]


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


def _render_interactive_prompt_context(
    repository,
    session_id: UUID,
    state: SessionState,
    mode: str,
) -> None:
    if mode == "answer":
        session_events = repository.read_session_events(session_id)
        question_text = _pending_question_text_from_events(
            session_events,
            state.pending_question_id,
        )
        print(
            _format_pending_question_line(
                state.pending_question_id,
                question_text,
            )
        )
        print(
            "Interactive mode: answer the pending question, or use /status, "
            "/help, or /exit."
        )
        return
    if mode == "approval":
        print(_interactive_blocked_input_message(state, session_id))
        print("Interactive mode: use /approve, /deny, /status, /help, or /exit.")
        return
    if mode == "prompt":
        print(
            "Interactive mode: type the next prompt, or use /status, /help, or /exit."
        )
        return
    print(_format_interactive_chat_pause_line(repository, session_id, state))


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


def _print_session_status(repository, session_id: UUID) -> None:
    record = repository.get_session(session_id)
    state = repository.get_session_state(session_id)
    if record is None or state is None:
        raise ValueError(f"unknown session_id: {session_id}")

    transcript_messages = repository.list_transcript_messages(session_id)
    pending_approvals = repository.list_approvals(session_id)
    tool_calls = repository.list_tool_calls(session_id)
    turn_metrics = repository.list_turn_metrics(session_id, limit=5)
    session_events = repository.read_session_events(session_id)

    current_turn_id = _current_turn_id(state, pending_approvals)
    current_turn_metrics = _find_turn_metrics(turn_metrics, current_turn_id)
    latest_turn_metrics = current_turn_metrics or (
        turn_metrics[0] if turn_metrics else None
    )
    recent_tool_calls = _recent_tool_calls(tool_calls)
    dashboard_url = _dashboard_url_from_events(session_events)
    latest_session_failure = _latest_session_failure(session_events)
    pending_question_text = _pending_question_text_from_events(
        session_events,
        state.pending_question_id,
    )

    print(f"Session {record.session_id}")
    print(f"Status: {state.status}")
    print(f"Last sequence: {state.last_sequence}")
    print(_format_current_turn_line(current_turn_id, state.status))
    print(f"Workspace: {record.cwd}")
    print(f"Model: {record.model_name}")
    print(f"Approval mode: {record.approval_mode}")
    if dashboard_url is not None:
        print(f"Dashboard URL: {dashboard_url}")
    print(f"Transcript messages: {len(transcript_messages)}")

    if latest_session_failure is not None:
        print(_format_session_failure(latest_session_failure))

    latest_summary = _latest_message_summary(transcript_messages)
    if latest_summary is not None:
        print(f"Latest message: {latest_summary}")
    if state.pending_question_id is not None:
        print(
            _format_pending_question_line(
                state.pending_question_id,
                pending_question_text,
            )
        )
    print(
        _format_next_action_line(
            record.session_id,
            state.status,
            current_turn_id,
            state.pending_approval_id,
            state.pending_question_id,
            latest_session_failure,
        )
    )

    if latest_turn_metrics is not None:
        label = (
            "Current turn metrics"
            if current_turn_metrics is not None
            else "Latest turn metrics"
        )
        print(f"{label}: {_format_turn_metrics(latest_turn_metrics)}")
    else:
        print("Latest turn metrics: none")

    if pending_approvals:
        print(f"Pending approvals: {len(pending_approvals)}")
        for approval in pending_approvals:
            print(f"  - {_format_approval_summary(approval)}")
    else:
        print("Pending approvals: none")

    if recent_tool_calls:
        print("Recent tool activity:")
        for tool_call in recent_tool_calls:
            print(f"  - {_format_tool_call_summary(tool_call)}")
    else:
        print("Recent tool activity: none")


def _format_current_turn_line(turn_id: UUID | None, status: str) -> str:
    if turn_id is None:
        return "Current turn: none"
    return f"Current turn: {turn_id} ({status})"


def _format_turn_metrics(metrics: TurnMetricsRecord) -> str:
    return (
        f"turn {metrics.turn_id}; "
        f"model {metrics.model_call_count} call(s), "
        f"{metrics.model_input_tokens_total} input / "
        f"{metrics.model_output_tokens_total} output tokens, "
        f"{metrics.model_duration_ms_total} ms; "
        f"tools {metrics.tool_call_count} call(s), "
        f"{metrics.tool_duration_ms_total} ms, "
        f"{metrics.succeeded_tool_call_count} succeeded / "
        f"{metrics.failed_tool_call_count} failed; "
        f"turn duration {_format_duration(metrics.turn_duration_ms)}"
    )


def _format_duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "n/a"
    return f"{duration_ms} ms"


def _format_approval_summary(approval: ApprovalRecord) -> str:
    return (
        f"{approval.approval_id} for turn {approval.turn_id}: "
        f"{approval.subject} ({approval.reason})"
    )


def _dashboard_url_from_events(events: Sequence[EventEnvelope]) -> str | None:
    for event in events:
        if isinstance(event.payload, SessionStarted):
            return event.payload.dashboard_url
    return None


def _latest_session_failure(
    events: Sequence[EventEnvelope],
) -> SessionFailed | None:
    for event in reversed(events):
        if isinstance(event.payload, SessionFailed):
            return event.payload
    return None


def _format_session_failure(session_failure: SessionFailed) -> str:
    retryable_suffix = " (retryable)" if session_failure.retryable else ""
    return f"Session failure: {session_failure.error_message}{retryable_suffix}"


def _format_tool_call_summary(tool_call: ToolCallRecord) -> str:
    summary_suffix = f": {tool_call.summary}" if tool_call.summary else ""
    return (
        f"{tool_call.tool_name} {tool_call.status} "
        f"(turn {tool_call.turn_id}){summary_suffix}"
    )


def _pending_question_text_from_events(
    events: Sequence[EventEnvelope],
    pending_question_id,
) -> str | None:
    if pending_question_id is None:
        return None

    pending_question_id_text = str(pending_question_id)
    for event in reversed(events):
        if not isinstance(event.payload, UserQuestionAsked):
            continue
        if str(event.payload.question_id) != pending_question_id_text:
            continue
        return event.payload.question
    return None


def _format_pending_question_line(question_id, question_text: str | None) -> str:
    if question_text:
        return f"Pending question: {question_id}: {question_text}"
    return f"Pending question: {question_id}"


def _format_next_action_line(
    session_id,
    status: str,
    current_turn_id,
    pending_approval_id,
    pending_question_id,
    latest_session_failure: SessionFailed | None,
) -> str:
    if status == "awaiting_approval" and pending_approval_id is not None:
        return (
            "Next action: resolve approval "
            f"{pending_approval_id} with 'glassbox approve {session_id} "
            f"{pending_approval_id}' or 'glassbox deny {session_id} "
            f"{pending_approval_id}', or use the dashboard approvals pane"
        )

    if status == "awaiting_user_input" and pending_question_id is not None:
        return (
            "Next action: answer question "
            f"{pending_question_id} with 'glassbox answer {session_id} "
            f"{pending_question_id} ANSWER', or use the dashboard Next Action "
            "pane"
        )

    if status == "running" and current_turn_id is None:
        return (
            "Next action: submit a new prompt with 'glassbox message "
            f"{session_id} PROMPT', or use the dashboard Next Action pane"
        )

    if status == "running":
        return (
            "Next action: wait for the active turn to finish before sending "
            "another prompt"
        )

    if status == "completed":
        return (
            "Next action: this session is complete; start a new session with "
            "'glassbox run PROMPT'"
        )

    if status == "failed":
        failure_guidance = "inspect the failure details above"
        if latest_session_failure is not None and latest_session_failure.retryable:
            failure_guidance = "inspect the retryable failure details above"
        return (
            "Next action: "
            f"{failure_guidance}, or start a new session with 'glassbox run PROMPT'"
        )

    return "Next action: inspect the session details above before taking another step"


def _resolve_approval_command(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    return asyncio.run(_resolve_approval_command_async(args, decision))


async def _resolve_approval_command_async(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.resolve_approval(
            args.session_id,
            args.approval_id,
            decision,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


async def _run_with_renderer(
    cwd: Path,
    db_path: Path | None,
    action: Callable[[RuntimeContext], Awaitable[None]],
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        renderer = CliEventRenderer(sys.stdout)
        async with runtime_context.infrastructure.event_bus.subscribe() as subscription:
            render_task = asyncio.create_task(
                renderer.render_subscription(subscription)
            )
            try:
                await action(runtime_context)
            except Exception:
                await asyncio.sleep(0)
                raise
            finally:
                render_task.cancel()
                with suppress(asyncio.CancelledError):
                    await render_task

    return 0


def _serve_command(args: argparse.Namespace) -> int:
    from glassbox.web import run_server

    cwd, db_path = _resolve_runtime_location(args)
    dashboard_url = _dashboard_root_url(args.host, args.port)
    print(f"Dashboard available at {dashboard_url}")
    print("Use ?session=SESSION_ID to open a specific session in the dashboard.")
    run_server(cwd, host=args.host, port=args.port, db_path=db_path)
    return 0


def _dashboard_root_url(host: str, port: int) -> str:
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}/"
