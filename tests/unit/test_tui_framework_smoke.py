"""Smoke tests for the accepted v5 terminal UI framework."""

import asyncio

from textual.app import App
from textual.app import ComposeResult
from textual.widgets import Static


class _SmokeApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("Glassbox TUI smoke", id="message")


def test_textual_smoke_app_can_run_under_test_driver() -> None:
    asyncio.run(_run_smoke_app())


async def _run_smoke_app() -> None:
    app = _SmokeApp()
    async with app.run_test(size=(80, 24)) as pilot:
        widget = pilot.app.query_one("#message", Static)

        assert isinstance(widget, Static)

        pilot.app.exit()
