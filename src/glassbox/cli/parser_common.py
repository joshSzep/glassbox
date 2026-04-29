"""Shared helpers for Glassbox CLI parser construction."""

import argparse
from uuid import UUID

_APPROVAL_MODE_CHOICES = ("confirm", "review", "on-request", "never")
_AUTONOMY_MODE_CHOICES = (
    "manual",
    "guided",
    "inspect",
    "edit-safe",
    "test-driven",
    "autonomous-local",
    "release-candidate",
)
_SESSION_STATUS_CHOICES = (
    "idle",
    "running",
    "awaiting_approval",
    "awaiting_user_input",
    "completed",
    "failed",
    "cancelled",
)
_EVAL_EXPECTATION_MODE_CHOICES = ("exact_match", "selected_invariants")
_EVAL_SEVERITY_CHOICES = ("critical", "high", "medium", "low")
_EVAL_VERIFICATION_STAGE_CHOICES = (
    "commit-time",
    "push-time",
    "release-candidate",
    "advisory",
)
_EVAL_PROFILE_TRACK_CHOICES = ("deterministic", "live-provider-canary")
_EVAL_BASELINE_REFRESH_POLICY_CHOICES = (
    "review_required",
    "intentional_only",
    "advisory",
)
_EVAL_INVARIANT_CHOICES = (
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
)


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


def _add_session_start_default_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model-name",
        default=None,
        help=(
            "model identifier recorded in the session metadata; overrides "
            "glassbox.profile.json"
        ),
    )
    parser.add_argument(
        "--approval-mode",
        default=None,
        choices=_APPROVAL_MODE_CHOICES,
        help=("approval mode for risky tool actions; overrides glassbox.profile.json"),
    )
    _add_autonomy_selection_arguments(parser)


def _add_autonomy_selection_arguments(parser: argparse.ArgumentParser) -> None:
    """Add scriptable autonomy selection flags."""

    parser.add_argument(
        "--autonomy-mode",
        default=None,
        choices=_AUTONOMY_MODE_CHOICES,
        help="bounded autonomy mode; overrides glassbox.profile.json",
    )
    parser.add_argument(
        "--autonomy-budget-preset",
        default=None,
        help=(
            "named autonomy budget preset or built-in mode budget; overrides "
            "glassbox.profile.json"
        ),
    )


def _hide_subparser_from_help(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_name: str,
) -> None:
    subparsers._choices_actions = [
        action
        for action in subparsers._choices_actions
        if getattr(action, "dest", None) != command_name
    ]


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
