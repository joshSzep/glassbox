"""Scenario-based coverage for v5 terminal workflows."""

import pytest

from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.interactive_launch import resolve_interactive_launch_mode
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import command_item_by_id
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import terminal_action_from_state
from glassbox.cli.tui.widgets import composer_availability
from glassbox.cli.tui.widgets import render_action_strip
from glassbox.cli.tui.widgets import render_details_pane
from glassbox.cli.tui.widgets import render_session_header
from glassbox.cli.tui.widgets import render_transcript
from tests.unit.tui_workflow_scenarios import TerminalWorkflowScenario
from tests.unit.tui_workflow_scenarios import state_from_scenario
from tests.unit.tui_workflow_scenarios import terminal_workflow_scenarios


@pytest.mark.parametrize(
    "scenario",
    terminal_workflow_scenarios(),
    ids=lambda scenario: scenario.name,
)
def test_terminal_workflow_scenarios_render_observable_states(
    scenario: TerminalWorkflowScenario,
) -> None:
    state = state_from_scenario(scenario)
    action = terminal_action_from_state(state)
    rendered = "\n".join(
        (
            render_session_header(state, width=92),
            render_transcript(state, width=92),
            render_action_strip(state, feedback=None),
            render_details_pane(state, width=92),
        )
    )

    assert state.header.mode == scenario.expected_mode
    assert action.kind == scenario.expected_action
    for expected in (
        scenario.transcript_contains
        + scenario.action_contains
        + scenario.header_contains
        + scenario.details_contains
    ):
        assert expected in rendered


def test_terminal_dashboard_handoff_commands_stay_enabled() -> None:
    scenario = next(
        item
        for item in terminal_workflow_scenarios()
        if item.name == "dashboard handoff"
    )
    state = state_from_scenario(scenario)
    items = command_items_for_state(state)
    open_dashboard = command_item_by_id(items, TerminalCommandId.OPEN_DASHBOARD)
    copy_dashboard = command_item_by_id(items, TerminalCommandId.COPY_DASHBOARD_URL)
    copy_session = command_item_by_id(items, TerminalCommandId.COPY_SESSION_ID)

    assert open_dashboard is not None
    assert open_dashboard.enabled is True
    assert copy_dashboard is not None
    assert copy_dashboard.enabled is True
    assert copy_session is not None
    assert copy_session.enabled is True


def test_terminal_reconnect_and_historical_scenarios_block_mutation() -> None:
    scenarios = {
        item.name: state_from_scenario(item) for item in terminal_workflow_scenarios()
    }

    reconnecting = scenarios["reconnect"]
    historical = scenarios["historical-only state"]

    assert reconnecting.header.stream_status == TerminalStreamStatus.RECONNECTING
    assert composer_availability(reconnecting).can_submit is False
    assert composer_availability(reconnecting).disabled_reason == "runtime reconnecting"
    assert composer_availability(historical).can_edit is False
    assert (
        terminal_action_from_state(historical).kind
        == TerminalActionKind.HISTORICAL_ONLY
    )


def test_terminal_implicit_non_tty_launch_falls_back_to_plain() -> None:
    mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=False,
            stdout_is_tty=False,
            term="xterm-256color",
            ci=False,
            tui_available=True,
        )
    )

    assert mode == InteractiveLaunchMode.PLAIN
