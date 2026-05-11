"""Changeset workup preview parser helpers."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid
from glassbox.tools.workflow import DiffSummaryScope


def _add_changeset_workup_parser(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
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
