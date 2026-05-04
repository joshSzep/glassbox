"""Unit coverage for plain interactive review-loop commands."""

from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.cli.interactive_client import ReviewLoopActionResult
from glassbox.cli.interactive_review_commands import _dashboard_review_url
from glassbox.cli.interactive_review_commands import _parse_review_command
from glassbox.cli.interactive_review_commands import _print_review_result
from glassbox.cli.interactive_session import _interactive_help_text
from glassbox.cli.interactive_session import _parse_interactive_input


def test_plain_interactive_parser_routes_review_commands() -> None:
    assert _parse_interactive_input("/review create tighten copy") == (
        "review",
        "/review create tighten copy",
    )
    assert _parse_interactive_input("/changeset verify change-1") == (
        "review",
        "/changeset verify change-1",
    )


def test_plain_review_command_vocabulary_matches_tui_aliases() -> None:
    create = _parse_review_command("/review create objective text")
    status = _parse_review_command("/changeset")
    verify = _parse_review_command("/review verification-plan change-1")
    handoff = _parse_review_command("/review handoff change-1")
    dashboard = _parse_review_command("/review dashboard change-1")

    assert create.action == "create"
    assert create.argument == "objective text"
    assert status.action == ReviewLoopAction.SHOW_FEEDBACK_STATUS
    assert status.argument is None
    assert verify.action == ReviewLoopAction.PREVIEW_VERIFICATION
    assert verify.argument == "change-1"
    assert handoff.action == ReviewLoopAction.INSPECT_HANDOFF
    assert dashboard.action == "dashboard"


def test_plain_review_result_prints_dashboard_detail_handoff(capsys) -> None:
    _print_review_result(
        ReviewLoopActionResult(
            action="create",
            headline="Created review changeset change-1",
            changeset_id="change-1",
            details=("No tests, staging, commit, push, PR, or merge was run.",),
            limitations=("manual evidence remains advisory",),
            safe_next_actions=("glassbox changeset show change-1 --cwd .",),
            dashboard_path="/app/changesets/change-1",
        ),
        dashboard_url="http://127.0.0.1:8765/?session=session-1",
    )

    output = capsys.readouterr().out
    assert "Created review changeset change-1" in output
    assert "No tests, staging, commit, push, PR, or merge was run." in output
    assert "manual evidence remains advisory" in output
    assert "glassbox changeset show change-1 --cwd ." in output
    assert "Dashboard: http://127.0.0.1:8765/app/changesets/change-1" in output


def test_plain_review_help_documents_safe_shortcuts() -> None:
    help_text = _interactive_help_text("prompt")

    assert "/review create [OBJECTIVE]" in help_text
    assert (
        "/review verify CHANGESET_ID preview verification without running commands"
        in help_text
    )
    assert (
        "/review handoff CHANGESET_ID inspect handoff readiness without publishing"
        in help_text
    )
    assert "/changeset ... compatibility alias" in help_text


def test_dashboard_review_url_targets_changeset_detail_route() -> None:
    assert (
        _dashboard_review_url(
            "http://127.0.0.1:8765/?session=session-1",
            "change/1",
        )
        == "http://127.0.0.1:8765/app/changesets/change%2F1"
    )
