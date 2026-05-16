"""Changeset export parser helpers."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_changeset_export_parsers(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    export_parser = changeset_subparsers.add_parser(
        "export",
        help="write a reviewer-safe changeset evidence package",
        description=(
            "Write a changeset-centered evidence package with redacted summaries, "
            "artifact references, verification posture, and non-claims."
        ),
    )
    export_parser.add_argument("changeset_id", type=_parse_uuid)
    export_parser.add_argument("output_path")
    export_parser.add_argument(
        "--markdown-output",
        dest="markdown_output_path",
        help="also write a compact reviewer-safe Markdown summary",
    )
    export_parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "preview included, redacted, local-only, and omitted evidence without "
            "writing the package"
        ),
    )
    export_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(export_parser)

    export_inspect_parser = changeset_subparsers.add_parser(
        "export-inspect",
        help="inspect a reviewer-safe changeset evidence package",
        description=(
            "Inspect a changeset evidence package without importing local state "
            "or reading raw artifacts."
        ),
    )
    export_inspect_parser.add_argument("bundle_path")
    export_inspect_parser.add_argument("--json", action="store_true")


__all__ = ["_add_changeset_export_parsers"]
