"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer, InteractivePromptState
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
from glassbox.runtime import (
    EvalRunner,
    EvalSuiteResult,
    ReplayResult,
    ReplayRunner,
    RuntimeContext,
    build_artifact_backed_context_snapshot,
    build_runtime_context_snapshot,
    build_working_set_snapshot,
    open_runtime_context,
)
from glassbox.runtime.eval_coverage import (
    audit_eval_coverage,
    build_eval_coverage_summary_lines,
)
from glassbox.web import GlassboxWebServer, WebServerConfig, build_web_server

_APPROVAL_MODE_CHOICES = ("confirm", "review", "on-request", "never")
_REPLAY_EXIT_CODES = {
    "exact_match": 0,
    "behavioral_drift": 10,
    "manifest_drift": 11,
    "unsupported_session": 12,
    "replay_failure": 13,
}


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
        if args.command == "fork":
            return _fork_command(args)
        if args.command == "status":
            return _status_command(args)
        if args.command == "replay":
            return _replay_command(args)
        if args.command == "replay-export":
            return _replay_export_command(args)
        if args.command == "eval":
            return _eval_command(args)
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
    chat_parser.add_argument(
        "--dashboard-host",
        default=None,
        help="host address for the co-hosted dashboard server",
    )
    chat_parser.add_argument(
        "--dashboard-port",
        type=_parse_port,
        default=None,
        help="port for the co-hosted dashboard server",
    )
    chat_parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="disable the co-hosted dashboard during interactive chat",
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

    fork_parser = subparsers.add_parser(
        "fork",
        help="create a child session from a historical turn",
        description=(
            "Create a new child session from the latest completed turn or an "
            "explicitly selected completed turn in an existing session."
        ),
    )
    fork_parser.add_argument("session_id", type=_parse_uuid)
    fork_parser.add_argument(
        "--turn",
        dest="turn_id",
        type=_parse_uuid,
        default=None,
        help="explicit completed turn identifier to fork from",
    )
    fork_parser.add_argument(
        "--branch-label",
        "--label",
        dest="branch_label",
        default=None,
        help="optional operator-visible label for the child branch",
    )
    fork_parser.add_argument(
        "--prompt",
        default=None,
        help="optional immediate prompt to submit to the new child session",
    )
    _add_runtime_location_arguments(fork_parser)

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

    replay_parser = subparsers.add_parser(
        "replay",
        help="replay a recorded session offline",
        description=(
            "Replay a recorded session offline against the current codebase and "
            "report whether behavior still matches the recorded baseline."
        ),
    )
    replay_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    replay_parser.add_argument(
        "--bundle",
        default=None,
        help="path to a portable replay bundle exported with replay-export",
    )
    replay_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured replay report as JSON",
    )
    _add_runtime_location_arguments(replay_parser)

    replay_export_parser = subparsers.add_parser(
        "replay-export",
        help="export a portable replay bundle",
        description=(
            "Export a recorded session into a portable replay bundle that can be "
            "checked in or replayed without the source SQLite session database."
        ),
    )
    replay_export_parser.add_argument("session_id", type=_parse_uuid)
    replay_export_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the exported replay bundle",
    )
    _add_runtime_location_arguments(replay_export_parser)

    eval_parser = subparsers.add_parser(
        "eval",
        help="run replay-backed eval suites",
        description=(
            "Run repository-local replay-backed eval cases and report a suite "
            "summary suitable for local validation or CI."
        ),
    )
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command")

    eval_run_parser = eval_subparsers.add_parser(
        "run",
        help="run one or more eval cases",
        description=(
            "Run discovered eval cases from the repository-local evals/ layout. "
            "Case IDs and tags narrow the selected suite."
        ),
    )
    eval_run_parser.add_argument(
        "case_ids",
        nargs="*",
        help="optional eval case IDs to run; defaults to all discovered cases",
    )
    eval_run_parser.add_argument(
        "--profile",
        default=None,
        help=(
            "named repository-owned verification profile to run before extra narrowing"
        ),
    )
    eval_run_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="require a tag on selected eval cases; repeat to require multiple tags",
    )
    eval_run_parser.add_argument(
        "--output-dir",
        default=None,
        help="directory for suite summary and per-case replay artifacts",
    )
    eval_run_parser.add_argument(
        "--refresh-output-dir",
        action="store_true",
        help=(
            "clear prior generated JSON artifacts in a managed .glassbox/evals/ "
            "output directory before writing the new suite result"
        ),
    )
    eval_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured eval suite report as JSON",
    )
    _add_runtime_location_arguments(eval_run_parser)

    eval_audit_parser = eval_subparsers.add_parser(
        "audit",
        help="audit capability coverage against the selected eval portfolio",
        description=(
            "Audit repository-local capability coverage expectations against the "
            "selected eval cases without executing replay bundles."
        ),
    )
    eval_audit_parser.add_argument(
        "case_ids",
        nargs="*",
        help="optional eval case IDs to audit; defaults to the selected suite",
    )
    eval_audit_parser.add_argument(
        "--profile",
        default=None,
        help=(
            "named repository-owned verification profile to audit before extra "
            "narrowing"
        ),
    )
    eval_audit_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="require a tag on selected eval cases; repeat to require multiple tags",
    )
    eval_audit_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured coverage audit report as JSON",
    )
    _add_runtime_location_arguments(eval_audit_parser)

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
        type=_parse_port,
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


def _parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value}") from exc
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError(f"invalid port: {value}")
    return port


def _resolve_runtime_location(args: argparse.Namespace) -> tuple[Path, Path | None]:
    cwd = Path(args.cwd).resolve()
    db_path = Path(args.db_path).resolve() if args.db_path is not None else None
    return cwd, db_path


def _resolve_optional_output_path(
    cwd: Path,
    output: str | None,
    *,
    default_name: str,
) -> Path:
    if output is None:
        return (cwd / default_name).resolve()

    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = cwd / output_path
    return output_path.resolve()


def _resolve_optional_explicit_path(cwd: Path, output: str | None) -> Path | None:
    if output is None:
        return None

    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = cwd / output_path
    return output_path.resolve()


def _run_command(args: argparse.Namespace) -> int:
    return asyncio.run(_run_command_async(args))


async def _run_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)
    config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
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
    base_config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    async def action(
        runtime_context: RuntimeContext,
        prompt_state: InteractivePromptState,
    ) -> None:
        dashboard_server: GlassboxWebServer | None = None
        dashboard_url: str | None = None
        try:
            dashboard_server, dashboard_url = await _start_chat_dashboard(
                runtime_context,
                args,
            )
            await asyncio.sleep(0)

            config = base_config.model_copy(update={"dashboard_url": dashboard_url})
            session_state = (
                await runtime_context.services.session_service.start_session(config)
            )
            await asyncio.sleep(0)
            if args.prompt:
                await runtime_context.services.session_service.submit_user_message(
                    session_state.session_id,
                    args.prompt,
                )
                await asyncio.sleep(0)
            print(f"Attached to session {session_state.session_id}")
            if dashboard_url is not None:
                print(
                    "Dashboard available at "
                    f"{_dashboard_session_url(dashboard_url, session_state.session_id)}"
                )
            await _interactive_session_loop(
                runtime_context,
                session_state.session_id,
                prompt_state,
            )
        finally:
            if dashboard_server is not None:
                await dashboard_server.stop()

    return await _run_with_renderer(cwd, db_path, action)


def _attach_command(args: argparse.Namespace) -> int:
    return asyncio.run(_attach_command_async(args))


async def _attach_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(
        runtime_context: RuntimeContext,
        prompt_state: InteractivePromptState,
    ) -> None:
        repository = runtime_context.repositories.sessions
        state = repository.get_session_state(args.session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")

        _ensure_session_can_attach(args.session_id, state)
        print(f"Attached to session {args.session_id}")
        await _interactive_session_loop(
            runtime_context,
            args.session_id,
            prompt_state,
        )

    return await _run_with_renderer(cwd, db_path, action)


def _resume_command(args: argparse.Namespace) -> int:
    return asyncio.run(_resume_command_async(args))


async def _resume_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
        await runtime_context.services.session_service.resume_session(args.session_id)
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _message_command(args: argparse.Namespace) -> int:
    return asyncio.run(_message_command_async(args))


async def _message_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
        await runtime_context.services.session_service.submit_user_message(
            args.session_id,
            args.prompt,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _fork_command(args: argparse.Namespace) -> int:
    return asyncio.run(_fork_command_async(args))


async def _fork_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
        forked_session = await runtime_context.services.session_service.fork_session(
            args.session_id,
            turn_id=args.turn_id,
            branch_label=args.branch_label,
        )
        await asyncio.sleep(0)
        print(
            "Forked session "
            f"{forked_session.child_session_id} "
            f"from {forked_session.parent_session_id} "
            f"at turn {forked_session.forked_from_turn_id} "
            f"(sequence {forked_session.forked_from_sequence})"
        )
        print(
            "Imported "
            f"{forked_session.inherited_message_count} transcript messages "
            "into child session"
        )
        if forked_session.branch_label is not None:
            print(f"Branch label: {forked_session.branch_label}")
        if args.prompt:
            await runtime_context.services.session_service.submit_user_message(
                forked_session.child_session_id,
                args.prompt,
            )
            await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _answer_command(args: argparse.Namespace) -> int:
    return asyncio.run(_answer_command_async(args))


async def _answer_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
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
        _print_session_status(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
            args.session_id,
        )

    return 0


def _replay_command(args: argparse.Namespace) -> int:
    return asyncio.run(_replay_command_async(args))


async def _replay_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    if (args.session_id is None) == (args.bundle is None):
        raise ValueError("specify exactly one of session_id or --bundle")

    if args.bundle is not None:
        result = await ReplayRunner().replay_bundle_file(
            Path(args.bundle),
            workspace_root=cwd,
        )
    else:
        session_id = args.session_id
        assert session_id is not None

        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            result = await ReplayRunner(
                runtime_context.repositories.sessions,
                runtime_context.repositories.artifacts,
            ).replay_session(session_id)

    if args.json:
        print(json.dumps(_replay_result_payload(result), indent=2, sort_keys=True))
    else:
        _print_replay_report(result)

    return _replay_exit_code(result)


def _replay_export_command(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)
    output_path = _resolve_optional_output_path(
        cwd,
        args.output,
        default_name=f"glassbox-replay-{args.session_id}.json",
    )

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        exported_path = ReplayRunner(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        ).export_session_bundle(args.session_id, output_path)

    print(f"Exported replay bundle for session {args.session_id}: {exported_path}")
    return 0


def _eval_command(args: argparse.Namespace) -> int:
    return asyncio.run(_eval_command_async(args))


async def _eval_command_async(args: argparse.Namespace) -> int:
    if args.eval_command == "run":
        cwd, _db_path = _resolve_runtime_location(args)
        del _db_path
        suite_result = await EvalRunner().run_suite(
            cwd,
            profile_id=args.profile,
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
            output_dir=_resolve_optional_explicit_path(cwd, args.output_dir),
            refresh_output_dir=args.refresh_output_dir,
        )

        if args.json:
            print(
                json.dumps(
                    suite_result.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_eval_suite_report(suite_result)

        return suite_result.exit_code

    if args.eval_command == "audit":
        cwd, _db_path = _resolve_runtime_location(args)
        del _db_path
        audit_result = audit_eval_coverage(
            cwd,
            profile_id=args.profile,
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
        )

        if args.json:
            print(
                json.dumps(
                    audit_result.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_eval_coverage_audit(result=audit_result, workspace_root=cwd)
        return 0

    raise ValueError("specify an eval subcommand")


async def _interactive_session_loop(
    runtime_context: RuntimeContext,
    session_id: UUID,
    prompt_state: InteractivePromptState,
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
            _print_session_status(
                repository,
                runtime_context.repositories.artifacts,
                session_id,
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


def _print_session_status(repository, artifact_repository, session_id: UUID) -> None:
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
    runtime_context = build_runtime_context_snapshot(
        record.cwd,
        repository.list_runtime_notes(session_id),
        working_set=build_working_set_snapshot(repository, session_id),
        artifact_context=build_artifact_backed_context_snapshot(
            repository,
            artifact_repository,
            session_id,
        ),
    )
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
    _print_runtime_context_summary(runtime_context)

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


def _print_runtime_context_summary(runtime_context) -> None:
    repository_context = runtime_context.repository_context

    print("Runtime context:")
    print(f"  Workspace summary: {repository_context.workspace_name}")
    if repository_context.high_signal_paths:
        print("  High-signal paths: " + ", ".join(repository_context.high_signal_paths))
    if repository_context.top_level_directories:
        directory_line = ", ".join(repository_context.top_level_directories)
        if repository_context.additional_directory_count:
            directory_line += (
                f" (+{repository_context.additional_directory_count} more)"
            )
        print(f"  Top-level directories: {directory_line}")
    if repository_context.top_level_files:
        file_line = ", ".join(repository_context.top_level_files)
        if repository_context.additional_file_count:
            file_line += f" (+{repository_context.additional_file_count} more)"
        print(f"  Top-level files: {file_line}")
    if repository_context.project_markers:
        print("  Project markers: " + ", ".join(repository_context.project_markers))

    if runtime_context.runtime_notes:
        print(f"  Runtime notes: {len(runtime_context.runtime_notes)} visible")
        for note in runtime_context.runtime_notes:
            inherited_suffix = ""
            if note.inherited and note.source_session_id is not None:
                inherited_suffix = (
                    f" (inherited from {str(note.source_session_id)[:8]})"
                )
            elif note.inherited:
                inherited_suffix = " (inherited)"
            print(f"    - [{note.category}] {note.message}{inherited_suffix}")
        if runtime_context.additional_runtime_note_count:
            print(
                "    - "
                f"+{runtime_context.additional_runtime_note_count} more active note(s)"
            )
    else:
        print("  Runtime notes: none")

    if runtime_context.working_set.items:
        print(f"  Working set: {len(runtime_context.working_set.items)} visible")
        for item in runtime_context.working_set.items:
            reason_text = "; ".join(item.reasons[:2])
            inherited_suffix = " (inherited)" if item.inherited else ""
            detail_suffix = f": {reason_text}" if reason_text else ""
            print(
                f"    - [{item.subject_kind}] {item.subject}"
                f"{inherited_suffix}"
                f" - {item.summary}{detail_suffix}"
            )
        if runtime_context.working_set.additional_item_count:
            print(
                "    - "
                f"+{runtime_context.working_set.additional_item_count} "
                "more working-set item(s)"
            )
    else:
        print("  Working set: none")

    if runtime_context.artifact_context.summaries:
        print(
            "  Artifact-backed context: "
            f"{len(runtime_context.artifact_context.summaries)} visible"
        )
        for summary in runtime_context.artifact_context.summaries:
            freshness_suffix = f" ({summary.freshness})"
            inherited_suffix = " (inherited)" if summary.inherited else ""
            failing_tests_suffix = ""
            if summary.failing_tests:
                failing_tests_suffix = ": failing tests: " + ", ".join(
                    summary.failing_tests[:2]
                )
            print(
                f"    - [{summary.summary_kind}] {summary.summary}"
                f"{freshness_suffix}{inherited_suffix}{failing_tests_suffix}"
            )
        if runtime_context.artifact_context.additional_summary_count:
            print(
                "    - "
                f"+{runtime_context.artifact_context.additional_summary_count} "
                "more artifact-backed summary item(s)"
            )
    else:
        print("  Artifact-backed context: none")


def _print_replay_report(result: ReplayResult) -> None:
    session_id = result.source_session_id
    if session_id is not None:
        print(f"Replay session {session_id}")
    print(f"Outcome: {_format_replay_outcome(result.outcome)}")

    if result.message:
        print(f"Summary: {result.message}")

    if result.outcome == "exact_match":
        print(
            "Matched: transcript, tool calls, approval flow, question flow, "
            "event families, and final state"
        )
        return

    if result.mismatches:
        print("Mismatches:")
        for mismatch in result.mismatches:
            print(f"  - {mismatch}")

    for detail_line in _replay_detail_lines(result):
        print(detail_line)


def _print_eval_suite_report(result: EvalSuiteResult) -> None:
    print(f"Eval workspace {result.workspace_root}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.profile_verification_stage})")
    print(f"Selected cases: {result.selected_case_count}")
    print(f"Passed: {result.passed_case_count}")
    print(f"Failed: {result.failed_case_count}")
    print("Outcomes:")
    for outcome, count in result.outcome_counts.items():
        print(f"  - {_format_replay_outcome(outcome)}: {count}")
    print(f"Artifacts: {result.output_dir}")
    if result.coverage_audit is not None:
        for line in build_eval_coverage_summary_lines(result.coverage_audit):
            print(line)
    print("Cases:")
    for case_result in result.cases:
        status = "passed" if case_result.passed else "failed"
        print(
            f"  - {case_result.case_id}: "
            f"{_format_replay_outcome(case_result.replay_outcome)} ({status})"
        )
        if case_result.message:
            print(f"    Summary: {case_result.message}")
        if case_result.relevant_mismatches:
            print(
                "    Relevant mismatches: " + ", ".join(case_result.relevant_mismatches)
            )
        if case_result.ignored_mismatches:
            print(
                "    Ignored mismatches: " + ", ".join(case_result.ignored_mismatches)
            )
        print(f"    Artifact: {case_result.artifact_path}")


def _print_eval_coverage_audit(*, workspace_root: Path, result) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.verification_stage})")
    for line in build_eval_coverage_summary_lines(result):
        print(line)
    if result.uncovered_release_critical_capability_ids:
        print("Uncovered release-critical capability details:")
        for capability_id in result.uncovered_release_critical_capability_ids:
            print(f"  - {capability_id}")
    if result.unmapped_case_ids:
        print("Unmapped case details:")
        for case_id in result.unmapped_case_ids:
            print(f"  - {case_id}")


def _replay_detail_lines(result: ReplayResult) -> list[str]:
    if result.baseline is None or result.replay is None:
        return []

    detail_lines: list[str] = []
    mismatch_set = set(result.mismatches)
    if "transcript drift" in mismatch_set:
        detail_lines.append(
            "Transcript: baseline "
            f"{len(result.baseline.transcript)} message(s), replay "
            f"{len(result.replay.transcript)} message(s)"
        )
    if "tool_calls drift" in mismatch_set:
        detail_lines.append(
            "Tool calls: baseline "
            f"{len(result.baseline.tool_calls)} call(s), replay "
            f"{len(result.replay.tool_calls)} call(s)"
        )
    if "approvals drift" in mismatch_set:
        detail_lines.append(
            "Approvals: baseline "
            f"{len(result.baseline.approvals)} item(s), replay "
            f"{len(result.replay.approvals)} item(s)"
        )
    if "questions drift" in mismatch_set:
        detail_lines.append(
            "Questions: baseline "
            f"{len(result.baseline.questions)} item(s), replay "
            f"{len(result.replay.questions)} item(s)"
        )
    if "event_families drift" in mismatch_set:
        detail_lines.append(
            "Event families: baseline "
            f"{len(result.baseline.event_families)} event(s), replay "
            f"{len(result.replay.event_families)} event(s)"
        )
    if "final_state drift" in mismatch_set:
        detail_lines.append(
            "Final state: baseline "
            f"{result.baseline.final_state.status}, replay "
            f"{result.replay.final_state.status}"
        )
    return detail_lines


def _replay_result_payload(result: ReplayResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["exit_code"] = _replay_exit_code(result)
    return payload


def _replay_exit_code(result: ReplayResult) -> int:
    return _REPLAY_EXIT_CODES[result.outcome]


def _format_replay_outcome(outcome: str) -> str:
    return outcome.replace("_", " ")


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

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state: InteractivePromptState,
    ) -> None:
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
    action: Callable[[RuntimeContext, InteractivePromptState], Awaitable[None]],
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        prompt_state = InteractivePromptState()
        renderer = CliEventRenderer(sys.stdout, prompt_state=prompt_state)
        async with runtime_context.infrastructure.event_bus.subscribe() as subscription:
            render_task = asyncio.create_task(
                renderer.render_subscription(subscription)
            )
            try:
                await action(runtime_context, prompt_state)
            except Exception:
                await asyncio.sleep(0)
                raise
            finally:
                prompt_state.clear()
                render_task.cancel()
                with suppress(asyncio.CancelledError):
                    await render_task

    return 0


def _serve_command(args: argparse.Namespace) -> int:
    from glassbox.web import WebServerConfig, run_server

    cwd, db_path = _resolve_runtime_location(args)
    dashboard_url = WebServerConfig(host=args.host, port=args.port).dashboard_url
    print(f"Dashboard available at {dashboard_url}")
    print("Use ?session=SESSION_ID to open a specific session in the dashboard.")
    run_server(cwd, host=args.host, port=args.port, db_path=db_path)
    return 0


def _dashboard_session_url(dashboard_url: str, session_id: UUID) -> str:
    return f"{dashboard_url}?session={session_id}"


def _chat_dashboard_config(
    args: argparse.Namespace,
) -> tuple[WebServerConfig | None, bool]:
    dashboard_host = getattr(args, "dashboard_host", None)
    dashboard_port = getattr(args, "dashboard_port", None)

    if args.no_dashboard:
        if dashboard_host is not None or dashboard_port is not None:
            raise ValueError(
                "cannot combine --no-dashboard with --dashboard-host "
                "or --dashboard-port"
            )
        return None, False

    explicit_dashboard_request = (
        dashboard_host is not None or dashboard_port is not None
    )
    return (
        WebServerConfig(
            host=dashboard_host or "127.0.0.1",
            port=dashboard_port or 8765,
        ),
        explicit_dashboard_request,
    )


async def _start_chat_dashboard(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
) -> tuple[GlassboxWebServer | None, str | None]:
    dashboard_config, explicit_dashboard_request = _chat_dashboard_config(args)
    if dashboard_config is None:
        return None, None

    dashboard_server = build_web_server(
        runtime_context,
        host=dashboard_config.host,
        port=dashboard_config.port,
    )
    try:
        await dashboard_server.start()
    except RuntimeError as exc:
        if explicit_dashboard_request:
            raise RuntimeError(
                f"dashboard startup failed at {dashboard_config.dashboard_url}: {exc}"
            ) from exc
        print(
            "Warning: dashboard unavailable at "
            f"{dashboard_config.dashboard_url}: {exc}",
            file=sys.stderr,
        )
        return None, None

    return dashboard_server, dashboard_server.config.dashboard_url
