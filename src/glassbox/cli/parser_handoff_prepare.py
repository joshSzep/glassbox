"""Package-oriented handoff parser helpers."""

import argparse
from collections.abc import Callable

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid

HandoffProfileArgumentAdder = Callable[[argparse.ArgumentParser], None]


def add_handoff_package_parsers(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    add_session_profile_arguments: HandoffProfileArgumentAdder,
    add_changeset_profile_arguments: HandoffProfileArgumentAdder,
) -> None:
    add_handoff_prepare_parser(
        handoff_subparsers,
        add_session_profile_arguments=add_session_profile_arguments,
        add_changeset_profile_arguments=add_changeset_profile_arguments,
    )
    add_handoff_inspect_parser(handoff_subparsers)
    add_handoff_import_parser(handoff_subparsers)


def add_handoff_prepare_parser(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    add_session_profile_arguments: HandoffProfileArgumentAdder,
    add_changeset_profile_arguments: HandoffProfileArgumentAdder,
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
    add_session_profile_arguments(session_parser)
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
    add_changeset_profile_arguments(changeset_parser)
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


def add_handoff_inspect_parser(
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


def add_handoff_import_parser(
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


__all__ = [
    "add_handoff_import_parser",
    "add_handoff_inspect_parser",
    "add_handoff_package_parsers",
    "add_handoff_prepare_parser",
]
