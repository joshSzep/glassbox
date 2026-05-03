"""Changeset feedback parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_changeset_feedback_parsers(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    feedback_parser = changeset_subparsers.add_parser(
        "feedback",
        help="record and inspect local review feedback",
        description=(
            "Record local review feedback evidence for changesets. Feedback is "
            "not approval and does not stage, commit, push, open a PR, or merge."
        ),
    )
    feedback_subparsers = feedback_parser.add_subparsers(
        dest="feedback_command",
        required=True,
    )

    feedback_add_parser = feedback_subparsers.add_parser(
        "add",
        help="add local review feedback evidence to a changeset",
    )
    feedback_add_parser.add_argument("changeset_id", type=_parse_uuid)
    feedback_add_parser.add_argument(
        "--kind",
        choices=(
            "requested_change",
            "reviewer_question",
            "operator_note",
            "observation",
            "risk",
        ),
        required=True,
    )
    feedback_add_parser.add_argument("--summary", required=True)
    feedback_add_parser.add_argument("--body")
    feedback_add_parser.add_argument(
        "--provenance",
        choices=("reviewer", "operator", "manual", "imported", "unknown"),
        default="manual",
    )
    feedback_add_parser.add_argument("--source-label")
    feedback_add_parser.add_argument("--reviewer-label")
    feedback_add_parser.add_argument("--actor", default="operator")
    feedback_add_parser.add_argument(
        "--scope-kind",
        choices=(
            "changeset",
            "file",
            "task",
            "turn",
            "artifact",
            "verification",
            "branch_candidate",
        ),
        default="changeset",
    )
    feedback_add_parser.add_argument("--scope-reason")
    feedback_add_parser.add_argument("--file")
    feedback_add_parser.add_argument("--line-start", type=int)
    feedback_add_parser.add_argument("--line-end", type=int)
    feedback_add_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_add_parser)

    feedback_list_parser = feedback_subparsers.add_parser(
        "list",
        help="list local review feedback",
    )
    feedback_list_parser.add_argument(
        "--changeset", dest="changeset_id", type=_parse_uuid
    )
    feedback_list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    feedback_list_parser.add_argument(
        "--disposition",
        choices=(
            "open",
            "in_progress",
            "responded",
            "resolved_locally",
            "accepted_with_risk",
            "archived",
        ),
    )
    feedback_list_parser.add_argument("--include-archived", action="store_true")
    feedback_list_parser.add_argument("--file")
    feedback_list_parser.add_argument("--limit", type=int, default=None)
    feedback_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_list_parser)

    feedback_show_parser = feedback_subparsers.add_parser(
        "show",
        help="show local review feedback details",
    )
    feedback_show_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_show_parser)

    feedback_status_parser = feedback_subparsers.add_parser(
        "status",
        help="show response status for feedback on one changeset",
        description=(
            "Show open, responded, unresolved, stale, blocked, and accepted-risk "
            "review response status without mutating git."
        ),
    )
    feedback_status_parser.add_argument("changeset_id", type=_parse_uuid)
    feedback_status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_status_parser)

    feedback_resolve_parser = feedback_subparsers.add_parser(
        "resolve",
        help="mark feedback resolved locally with retained response text",
    )
    feedback_resolve_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_resolve_parser.add_argument("--summary", required=True)
    feedback_resolve_parser.add_argument("--residual-risk")
    feedback_resolve_parser.add_argument("--actor", default="operator")
    feedback_resolve_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_resolve_parser)

    feedback_reopen_parser = feedback_subparsers.add_parser(
        "reopen",
        help="reopen previously handled local review feedback",
    )
    feedback_reopen_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_reopen_parser.add_argument("--reason", required=True)
    feedback_reopen_parser.add_argument("--actor", default="operator")
    feedback_reopen_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_reopen_parser)

    feedback_archive_parser = feedback_subparsers.add_parser(
        "archive",
        help="archive feedback after explicit operator intent",
    )
    feedback_archive_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_archive_parser.add_argument("--reason", required=True)
    feedback_archive_parser.add_argument("--actor", default="operator")
    feedback_archive_parser.add_argument(
        "--replacement", dest="replacement_feedback_id", type=_parse_uuid
    )
    feedback_archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_archive_parser)

    feedback_accept_risk_parser = feedback_subparsers.add_parser(
        "accept-risk",
        help="mark feedback accepted with explicit local residual risk",
    )
    feedback_accept_risk_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_accept_risk_parser.add_argument("--risk-summary", required=True)
    feedback_accept_risk_parser.add_argument("--reason", required=True)
    feedback_accept_risk_parser.add_argument("--actor", default="operator")
    feedback_accept_risk_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_accept_risk_parser)
