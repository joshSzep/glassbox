"""Launch helpers that pair TUI apps with interactive session clients."""

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.app import GlassboxTerminalApp
from glassbox.cli.tui.app import create_tui_app


async def create_session_tui_app(
    *,
    client: InteractiveSessionClient,
    launch_options: InteractiveLaunchOptions,
    dashboard_url: str | None,
) -> GlassboxTerminalApp:
    initial_snapshot = await client.fetch_snapshot()
    return create_tui_app(
        client=client,
        initial_snapshot=initial_snapshot,
        launch_options=launch_options,
        dashboard_url=dashboard_url,
    )
