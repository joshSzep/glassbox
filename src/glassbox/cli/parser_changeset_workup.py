"""Changeset workup preview parser helpers."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid
from glassbox.tools.workflow import DiffSummaryScope


def _add_changeset_workup_parser(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    workup_parser = changeset_subparsers.add_parser(
        "workup",
        help="run a guided local changeset workup flow",
        description=(
            "Guide the path from workspace diff or an existing changeset through "
            "inventory, verification planning, selected/skipped checks, lifecycle "
            "brief, and handoff posture. Durable steps require explicit "
            "confirmation flags."
        ),
    )
    workup_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    workup_parser.add_argument("--changeset", dest="changeset_id", type=_parse_uuid)
    workup_parser.add_argument("--objective")
    workup_parser.add_argument("--confirm-create", action="store_true")
    workup_parser.add_argument("--confirm-refresh", action="store_true")
    workup_parser.add_argument("--confirm-brief", action="store_true")
    workup_parser.add_argument(
        "--select-verification",
        dest="select_verification_ids",
        type=_parse_uuid,
        action="append",
        default=None,
    )
    workup_parser.add_argument(
        "--skip-verification",
        dest="skip_verification_ids",
        type=_parse_uuid,
        action="append",
        default=None,
    )
    workup_parser.add_argument("--skip-reason")
    workup_parser.add_argument(
        "--accept-risk-verification",
        dest="accept_risk_verification_ids",
        type=_parse_uuid,
        action="append",
        default=None,
    )
    workup_parser.add_argument("--risk-reason")
    workup_parser.add_argument("--risk", dest="residual_risks", action="append")
    workup_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(workup_parser)

    workup_preview_parser = changeset_subparsers.add_parser(
        "workup-preview",
        help="preview the review workup for current workspace changes",
        description=(
            "Inspect local workspace changes, candidate grouping, verification "
            "plan, repository impact, review risks, memory cues, and safe next "
            "commands without creating a changeset, staging files, or running "
            "commands."
        ),
    )
    workup_preview_parser.add_argument(
        "--scope",
        choices=tuple(item.value for item in DiffSummaryScope),
        default=DiffSummaryScope.WORKSPACE.value,
        help="diff scope to inspect",
    )
    workup_preview_parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        default=None,
        help="workspace-relative path filter; repeat for multiple paths",
    )
    workup_preview_parser.add_argument(
        "--session",
        dest="session_id",
        type=_parse_uuid,
        help="optional session used to make follow-up commands concrete",
    )
    workup_preview_parser.add_argument(
        "--max-files",
        type=int,
        default=200,
        help="maximum changed files to inspect",
    )
    workup_preview_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(workup_preview_parser)


__all__ = ["_add_changeset_workup_parser"]
