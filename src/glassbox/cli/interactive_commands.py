"""CLI command handlers for interactive and session workflow commands."""

import argparse
import asyncio
from pathlib import Path

import httpx

from glassbox.cli.daemon_attach import attach_tui_via_daemon
from glassbox.cli.daemon_attach import attach_via_daemon
from glassbox.cli.daemon_status import build_runtime_owner_status_report
from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import interactive_launch_options_from_args
from glassbox.cli.interactive_launch import resolve_interactive_launch_mode
from glassbox.cli.interactive_session import _interactive_session_loop
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.runtime_runner import _dashboard_session_url
from glassbox.cli.runtime_runner import _run_with_renderer
from glassbox.cli.runtime_runner import _start_chat_dashboard
from glassbox.cli.tui import create_session_tui_app
from glassbox.cli.tui import run_tui_app
from glassbox.cli.tui.conversation import with_runtime_owner
from glassbox.core import SessionConfig
from glassbox.core.ids import SessionId
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.daemon import clear_stale_runtime_owner
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.workspace_profile import resolve_session_start_defaults


def _run_command(args: argparse.Namespace) -> int:
    return asyncio.run(_run_command_async(args))


async def _run_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="start a local session runner",
    )
    config = _build_start_session_config(args, cwd)

    async def action(
        runtime_context: RuntimeContext,
        _prompt_state,
    ) -> None:
        session_state = await runtime_context.services.session_service.start_session(
            config
        )
        await asyncio.sleep(0)
        _print_autonomy_config_summary(config)
        await _submit_prompt_if_present(
            runtime_context,
            session_state.session_id,
            args.prompt,
        )

    return await _run_with_renderer(cwd, db_path, action)


def _chat_command(args: argparse.Namespace) -> int:
    return asyncio.run(_chat_command_async(args))


async def _chat_command_async(args: argparse.Namespace) -> int:
    launch_options = interactive_launch_options_from_args(args, tui_available=True)
    launch_mode = resolve_interactive_launch_mode(launch_options)

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="start an interactive chat session",
    )
    base_config = _build_start_session_config(args, cwd)

    if launch_mode == InteractiveLaunchMode.TUI:
        return await _chat_tui_command_async(
            args,
            cwd=cwd,
            db_path=db_path,
            base_config=base_config,
            launch_options=launch_options,
        )

    async def action(runtime_context: RuntimeContext, prompt_state) -> None:
        dashboard_server = None
        dashboard_url = None
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
            _print_autonomy_config_summary(config)
            await _submit_prompt_if_present(
                runtime_context,
                session_state.session_id,
                args.prompt,
            )
            print(f"Attached to session {session_state.session_id}")
            if dashboard_url is not None:
                print(
                    "Dashboard available at "
                    + _dashboard_session_url(
                        dashboard_url,
                        session_state.session_id,
                    )
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


async def _chat_tui_command_async(
    args: argparse.Namespace,
    *,
    cwd: Path,
    db_path: Path | None,
    base_config: SessionConfig,
    launch_options,
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        dashboard_server = None
        dashboard_url = None
        try:
            dashboard_server, dashboard_url = await _start_chat_dashboard(
                runtime_context,
                args,
            )
            config = base_config.model_copy(update={"dashboard_url": dashboard_url})
            session_state = (
                await runtime_context.services.session_service.start_session(config)
            )
            _print_autonomy_config_summary(config)
            await _submit_prompt_if_present(
                runtime_context,
                session_state.session_id,
                args.prompt,
            )
            app = await create_session_tui_app(
                client=LocalInteractiveSessionClient(
                    runtime_context=runtime_context,
                    session_id=session_state.session_id,
                    dashboard_url=dashboard_url,
                ),
                launch_options=launch_options,
                dashboard_url=dashboard_url,
            )
            await run_tui_app(app)
        finally:
            if dashboard_server is not None:
                await dashboard_server.stop()
    return 0


def _attach_command(args: argparse.Namespace) -> int:
    return asyncio.run(_attach_command_async(args))


async def _attach_command_async(args: argparse.Namespace) -> int:
    launch_options = interactive_launch_options_from_args(args, tui_available=True)
    launch_mode = resolve_interactive_launch_mode(launch_options)

    cwd, db_path = resolve_runtime_location(args)
    daemon_status = inspect_runtime_owner(cwd, db_path=db_path)

    if daemon_status.state == "running":
        assert daemon_status.record is not None
        if daemon_status.health != "ok":
            report = build_runtime_owner_status_report(daemon_status, cwd, db_path)
            raise ValueError(
                "live runtime unavailable at "
                f"{daemon_status.record.dashboard_url}; cannot attach session "
                f"{args.session_id}\n"
                f"Inspect health: {report.health_url}\n"
                f"Status: {report.commands.status}\n"
                f"Recover: {report.commands.stop} && {report.commands.start}"
            )
        if launch_mode == InteractiveLaunchMode.TUI:
            return await attach_tui_via_daemon(
                args,
                dashboard_url=daemon_status.record.dashboard_url,
                launch_options=launch_options,
            )
        return await attach_via_daemon(
            args,
            dashboard_url=daemon_status.record.dashboard_url,
        )

    if daemon_status.state == "stale":
        clear_stale_runtime_owner(cwd, db_path=db_path)
        print(
            "Workspace daemon owner metadata is stale; reopening the persisted "
            "session locally."
        )

    if launch_mode == InteractiveLaunchMode.TUI:
        return await _attach_tui_local_command_async(
            args,
            cwd=cwd,
            db_path=db_path,
            launch_options=launch_options,
        )

    async def action(runtime_context: RuntimeContext, prompt_state) -> None:
        repository = runtime_context.repositories.sessions
        state = repository.get_session_state(args.session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")

        from glassbox.cli.interactive_session import _ensure_session_can_attach

        _ensure_session_can_attach(args.session_id, state)
        print(f"Attached to session {args.session_id}")
        await _interactive_session_loop(
            runtime_context,
            args.session_id,
            prompt_state,
        )

    return await _run_with_renderer(cwd, db_path, action)


async def _attach_tui_local_command_async(
    args: argparse.Namespace,
    *,
    cwd: Path,
    db_path: Path | None,
    launch_options,
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        state = runtime_context.repositories.sessions.get_session_state(args.session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")
        app = await create_session_tui_app(
            client=LocalInteractiveSessionClient(
                runtime_context=runtime_context,
                session_id=args.session_id,
            ),
            launch_options=launch_options,
            dashboard_url=None,
        )
        app.state = with_runtime_owner(app.state, "persisted local session")
        await run_tui_app(app)
    return 0


def _resume_command(args: argparse.Namespace) -> int:
    return asyncio.run(_resume_command_async(args))


async def _resume_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="resume a session locally",
    )
    autonomy_config = _build_ad_hoc_autonomy_config(args, cwd)

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        if autonomy_config is not None:
            _print_autonomy_config_summary(autonomy_config)
        await runtime_context.services.session_service.resume_session(args.session_id)
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _message_command(args: argparse.Namespace) -> int:
    return asyncio.run(_message_command_async(args))


async def _message_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="submit a message locally",
    )
    autonomy_config = _build_ad_hoc_autonomy_config(args, cwd)

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        if autonomy_config is not None:
            _print_autonomy_config_summary(autonomy_config)
        await runtime_context.services.session_service.submit_user_message(
            args.session_id,
            args.prompt,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _cancel_command(args: argparse.Namespace) -> int:
    return asyncio.run(_cancel_command_async(args))


async def _cancel_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    daemon_status = inspect_runtime_owner(cwd, db_path=db_path)
    if daemon_status.state == "running" and daemon_status.record is not None:
        if daemon_status.health != "ok":
            raise ValueError(
                "live runtime unavailable at "
                f"{daemon_status.record.dashboard_url}; cannot cancel session "
                f"{args.session_id}"
            )
        async with httpx.AsyncClient(
            base_url=daemon_status.record.dashboard_url,
            timeout=httpx.Timeout(5.0, connect=1.0, read=5.0, write=5.0),
        ) as client:
            response = await client.post(
                f"/sessions/{args.session_id}/cancel",
                json={
                    "reason": args.reason,
                    "turn_id": str(args.turn_id) if args.turn_id else None,
                },
            )
        if response.status_code in {404, 409, 422}:
            raise ValueError(response.json().get("detail", response.text))
        response.raise_for_status()
        print(f"Cancellation requested for session {args.session_id}")
        return 0

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="cancel a local session turn",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await runtime_context.services.session_service.cancel_turn(
            args.session_id,
            turn_id=args.turn_id,
            requested_by="cli",
            reason=args.reason,
        )
        await asyncio.sleep(0)
        print(f"Cancellation requested for session {args.session_id}")

    return await _run_with_renderer(cwd, db_path, action)


def _fork_command(args: argparse.Namespace) -> int:
    return asyncio.run(_fork_command_async(args))


async def _fork_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="fork a session locally",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
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
            await _submit_prompt_if_present(
                runtime_context,
                forked_session.child_session_id,
                args.prompt,
            )

    return await _run_with_renderer(cwd, db_path, action)


def _build_start_session_config(
    args: argparse.Namespace,
    cwd: Path,
) -> SessionConfig:
    defaults = resolve_session_start_defaults(
        cwd,
        explicit_model_name=args.model_name,
        explicit_approval_mode=args.approval_mode,
        explicit_autonomy_mode=getattr(args, "autonomy_mode", None),
        explicit_autonomy_budget_preset=getattr(args, "autonomy_budget_preset", None),
    )
    return SessionConfig(
        model_name=defaults.model_name,
        cwd=cwd,
        approval_mode=defaults.approval_mode,
        autonomy_mode=defaults.autonomy_mode,
        autonomy_budget=defaults.autonomy_budget,
        autonomy_budget_preset=defaults.autonomy_budget_preset,
    )


def _print_autonomy_config_summary(config: SessionConfig) -> None:
    budget = config.autonomy_budget
    if budget is None:
        print(f"Autonomy: {config.autonomy_mode.value}; budget unavailable")
        return
    print(
        "Autonomy: "
        f"{config.autonomy_mode.value}; "
        f"budget {config.autonomy_budget_preset or config.autonomy_mode.value}; "
        f"steps {budget.max_steps}, tools {budget.max_tool_calls}, "
        f"writes {budget.max_write_operations}, "
        f"commands {budget.max_command_operations}"
    )


def _build_ad_hoc_autonomy_config(
    args: argparse.Namespace,
    cwd: Path,
) -> SessionConfig | None:
    autonomy_mode = getattr(args, "autonomy_mode", None)
    autonomy_budget_preset = getattr(args, "autonomy_budget_preset", None)
    if not (autonomy_mode or autonomy_budget_preset):
        return None
    defaults = resolve_session_start_defaults(
        cwd,
        explicit_model_name=None,
        explicit_approval_mode=None,
        explicit_autonomy_mode=autonomy_mode,
        explicit_autonomy_budget_preset=autonomy_budget_preset,
    )
    return SessionConfig(
        model_name=defaults.model_name,
        cwd=cwd,
        approval_mode=defaults.approval_mode,
        autonomy_mode=defaults.autonomy_mode,
        autonomy_budget=defaults.autonomy_budget,
        autonomy_budget_preset=defaults.autonomy_budget_preset,
    )


async def _submit_prompt_if_present(
    runtime_context: RuntimeContext,
    session_id: SessionId,
    prompt: str | None,
) -> None:
    if not prompt:
        return
    await runtime_context.services.session_service.submit_user_message(
        session_id,
        prompt,
    )
    await asyncio.sleep(0)


def _answer_command(args: argparse.Namespace) -> int:
    return asyncio.run(_answer_command_async(args))


async def _answer_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="answer a question locally",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await runtime_context.services.session_service.provide_user_answer(
            args.session_id,
            args.question_id,
            args.answer,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _resolve_approval_command(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    return asyncio.run(_resolve_approval_command_async(args, decision))


async def _resolve_approval_command_async(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="resolve an approval locally",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await runtime_context.services.session_service.resolve_approval(
            args.session_id,
            args.approval_id,
            decision,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)
