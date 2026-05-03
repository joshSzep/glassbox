"""CLI command handlers for interactive and session workflow commands."""

import argparse
import asyncio
from pathlib import Path

from glassbox.cli.chat_startup import print_chat_startup_summary
from glassbox.cli.daemon_attach import attach_tui_via_daemon
from glassbox.cli.daemon_attach import attach_via_daemon
from glassbox.cli.daemon_status import build_runtime_owner_status_report
from glassbox.cli.interactive_autonomy import (
    build_ad_hoc_autonomy_config as _build_ad_hoc_autonomy_config,
)
from glassbox.cli.interactive_autonomy import (
    build_start_session_config as _build_start_session_config,
)
from glassbox.cli.interactive_autonomy import (
    print_autonomy_config_summary as _print_autonomy_config_summary,
)
from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.cli.interactive_daemon_actions import request_cancel_via_daemon
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import interactive_launch_options_from_args
from glassbox.cli.interactive_launch import resolve_interactive_launch_mode
from glassbox.cli.interactive_local_actions import answer_question_locally
from glassbox.cli.interactive_local_actions import cancel_session_turn_locally
from glassbox.cli.interactive_local_actions import fork_session_locally
from glassbox.cli.interactive_local_actions import resolve_approval_locally
from glassbox.cli.interactive_local_actions import resume_session_locally
from glassbox.cli.interactive_local_actions import submit_prompt_if_present
from glassbox.cli.interactive_local_actions import submit_session_message_locally
from glassbox.cli.interactive_session import _interactive_session_loop
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.runtime_runner import _dashboard_session_url
from glassbox.cli.runtime_runner import _run_with_renderer
from glassbox.cli.runtime_runner import _start_chat_dashboard
from glassbox.cli.tui import create_session_tui_app
from glassbox.cli.tui import run_tui_app
from glassbox.cli.tui.conversation import with_runtime_owner
from glassbox.core import SessionConfig
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.bootstrap_storage import resolve_runtime_storage_paths
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.daemon import clear_stale_runtime_owner
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.web.app import _STATIC_NEXT_DIR
from glassbox.web.spa_static import validate_spa_static_assets


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
        await submit_prompt_if_present(
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
            print_chat_startup_summary(
                session_id=session_state.session_id,
                config=config,
                database_path=resolve_runtime_storage_paths(
                    cwd,
                    db_path=db_path,
                ).database_path,
                dashboard_url=dashboard_url,
                dashboard_disabled=args.no_dashboard,
                dashboard_asset_problems=validate_spa_static_assets(_STATIC_NEXT_DIR),
                provider_report=build_provider_diagnostics_report(
                    cwd,
                    explicit_model_name=config.model_name,
                ),
                include_prompt_suggestions=args.prompt is None,
            )
            await submit_prompt_if_present(
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
                dashboard_url=dashboard_url,
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
            print_chat_startup_summary(
                session_id=session_state.session_id,
                config=config,
                database_path=resolve_runtime_storage_paths(
                    cwd,
                    db_path=db_path,
                ).database_path,
                dashboard_url=dashboard_url,
                dashboard_disabled=args.no_dashboard,
                dashboard_asset_problems=validate_spa_static_assets(_STATIC_NEXT_DIR),
                provider_report=build_provider_diagnostics_report(
                    cwd,
                    explicit_model_name=config.model_name,
                ),
                include_prompt_suggestions=args.prompt is None,
            )
            await submit_prompt_if_present(
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
            dashboard_url=None,
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
        await resume_session_locally(runtime_context, args, autonomy_config)

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
        await submit_session_message_locally(runtime_context, args, autonomy_config)

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
        await request_cancel_via_daemon(
            dashboard_url=daemon_status.record.dashboard_url,
            session_id=args.session_id,
            turn_id=args.turn_id,
            reason=args.reason,
        )
        print(f"Cancellation requested for session {args.session_id}")
        return 0

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="cancel a local session turn",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await cancel_session_turn_locally(runtime_context, args)

    return await _run_with_renderer(cwd, db_path, action)


def _fork_command(args: argparse.Namespace) -> int:
    return asyncio.run(_fork_command_async(args))


async def _fork_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="fork a session locally",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await fork_session_locally(runtime_context, args)

    return await _run_with_renderer(cwd, db_path, action)


def _answer_command(args: argparse.Namespace) -> int:
    return asyncio.run(_answer_command_async(args))


async def _answer_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="answer a question locally",
    )

    async def action(runtime_context: RuntimeContext, _prompt_state) -> None:
        await answer_question_locally(runtime_context, args)

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
        await resolve_approval_locally(runtime_context, args, decision)

    return await _run_with_renderer(cwd, db_path, action)
