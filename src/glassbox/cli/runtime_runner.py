"""Shared CLI helpers for runtime-backed command execution."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer
from glassbox.cli.renderer import InteractivePromptState
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context import RuntimeContext
from glassbox.web import GlassboxWebServer
from glassbox.web import WebServerConfig
from glassbox.web import build_web_server


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
    return dashboard_server, dashboard_config.dashboard_url
