"""Shared parser helpers for handoff profile flags."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid
from glassbox.core import HandoffIntent

_HANDOFF_INTENT_CHOICES = tuple(intent.value for intent in HandoffIntent)


def add_handoff_profile_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_labels: bool,
    format_choices: tuple[str, ...],
    format_help: str,
) -> None:
    """Add recipient-oriented handoff export profile arguments."""

    parser.add_argument(
        "--intent",
        choices=_HANDOFF_INTENT_CHOICES,
        default=HandoffIntent.REVIEW_ONLY.value,
        help="recipient intent for the export profile",
    )
    if include_labels:
        parser.add_argument(
            "--recipient",
            default=None,
            help="optional recipient label to include in the package",
        )
        parser.add_argument(
            "--exported-by",
            default=None,
            help="optional acting-operator label to include in the package",
        )
        parser.add_argument(
            "--expected-custodian",
            default=None,
            help="optional operator label expected to take custody after export",
        )
        parser.add_argument(
            "--note",
            default=None,
            help="optional handoff note to include in the package",
        )
    parser.add_argument(
        "--format",
        choices=format_choices,
        default=format_choices[0],
        help=format_help,
    )


def _add_handoff_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    handoff_parser = subparsers.add_parser(
        "handoff",
        help="prepare, inspect, import, and record local handoff decisions",
        description=(
            "Prepare, inspect, import, and record local handoff workflow state "
            "without granting approval, publication, or runtime ownership."
        ),
    )
    handoff_subparsers = handoff_parser.add_subparsers(
        dest="handoff_command",
        required=True,
    )

    _add_handoff_prepare_parser(handoff_subparsers)
    _add_handoff_inspect_parser(handoff_subparsers)
    _add_handoff_import_parser(handoff_subparsers)

    list_parser = handoff_subparsers.add_parser(
        "list",
        help="list projected handoff records",
    )
    list_parser.add_argument("--session-id", type=_parse_uuid, default=None)
    list_parser.add_argument("--include-archived", action="store_true")
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = handoff_subparsers.add_parser(
        "show",
        help="show one projected handoff record",
    )
    show_parser.add_argument("session_id", type=_parse_uuid)
    show_parser.add_argument("package_id")
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    guidance_parser = handoff_subparsers.add_parser(
        "guidance",
        help="preview fork-or-continue guidance for an imported handoff",
    )
    _add_handoff_decision_target_arguments(guidance_parser)
    guidance_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(guidance_parser)

    accept_parser = handoff_subparsers.add_parser(
        "accept",
        help="accept local custody or imported follow-up",
    )
    _add_handoff_decision_target_arguments(accept_parser)
    accept_parser.add_argument("--accepted-by", default="operator")
    accept_parser.add_argument("--reason", default=None)
    accept_parser.add_argument(
        "--follow-up-intent",
        choices=_HANDOFF_INTENT_CHOICES,
        default=None,
    )
    accept_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(accept_parser)

    reject_parser = handoff_subparsers.add_parser(
        "reject",
        help="reject local custody with a retained reason",
    )
    _add_handoff_decision_target_arguments(reject_parser)
    reject_parser.add_argument("--rejected-by", default="operator")
    reject_parser.add_argument("--reason", required=True)
    reject_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(reject_parser)

    archive_parser = handoff_subparsers.add_parser(
        "archive",
        help="archive a handoff as historical workflow evidence",
    )
    _add_handoff_decision_target_arguments(archive_parser)
    archive_parser.add_argument("--archived-by", default="operator")
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(archive_parser)


def _add_handoff_decision_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", type=_parse_uuid)
    parser.add_argument("package_id")


def _add_handoff_prepare_parser(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    prepare_parser = handoff_subparsers.add_parser(
        "prepare",
        help="prepare a session or changeset handoff package",
        description=(
            "Prepare or preview a recipient-oriented handoff package from an "
            "existing session or changeset."
        ),
    )
    prepare_subparsers = prepare_parser.add_subparsers(
        dest="handoff_prepare_source",
        required=True,
    )

    session_parser = prepare_subparsers.add_parser(
        "session",
        help="prepare a session handoff package",
    )
    session_parser.add_argument("session_id", type=_parse_uuid)
    session_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the exported session handoff package",
    )
    session_parser.add_argument(
        "--markdown-output",
        dest="markdown_output_path",
        help="also write a reviewer-safe Markdown handoff summary",
    )
    add_handoff_profile_arguments(
        session_parser,
        include_labels=True,
        format_choices=("json",),
        format_help="export format; session handoff packages are stable JSON",
    )
    session_parser.add_argument("--json", action="store_true")
    session_parser.add_argument(
        "--preview",
        action="store_true",
        help="preview redaction and local-only evidence without writing a package",
    )
    _add_runtime_location_arguments(session_parser)

    changeset_parser = prepare_subparsers.add_parser(
        "changeset",
        help="prepare a changeset review handoff package",
    )
    changeset_parser.add_argument("changeset_id", type=_parse_uuid)
    changeset_parser.add_argument(
        "output_path",
        nargs="?",
        help="optional output path for the exported changeset handoff package",
    )
    add_handoff_profile_arguments(
        changeset_parser,
        include_labels=True,
        format_choices=("json", "json+markdown"),
        format_help="export stable JSON, or JSON plus a Markdown summary",
    )
    changeset_parser.add_argument(
        "--markdown-output",
        dest="markdown_output_path",
        help="also write a compact reviewer-safe Markdown summary",
    )
    changeset_parser.add_argument(
        "--preview",
        action="store_true",
        help="preview redaction and local-only evidence without writing a package",
    )
    changeset_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(changeset_parser)


def _add_handoff_inspect_parser(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    inspect_parser = handoff_subparsers.add_parser(
        "inspect",
        help="inspect a handoff package without importing it",
        description=(
            "Inspect package compatibility, redaction posture, local-only gaps, "
            "safe first commands, and non-claims without mutating local state."
        ),
    )
    inspect_parser.add_argument("package")
    inspect_parser.add_argument("--json", action="store_true")
    inspect_parser.add_argument(
        "--markdown",
        action="store_true",
        help="render supported session or changeset packages as safe Markdown",
    )
    _add_runtime_location_arguments(inspect_parser)


def _add_handoff_import_parser(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    import_parser = handoff_subparsers.add_parser(
        "import",
        help="import a session handoff package for inspection",
        description=(
            "Import a supported session handoff package into historical "
            "inspection-only local state after the package has been inspected."
        ),
    )
    import_parser.add_argument("package")
    import_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(import_parser)


__all__ = ["_add_handoff_parsers", "add_handoff_profile_arguments"]
