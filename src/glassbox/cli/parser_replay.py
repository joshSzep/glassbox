"""Replay argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_replay_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    replay_parser = subparsers.add_parser(
        "replay",
        help="run replay-backed baselines or work with portable bundles",
        description=(
            "Run replay verification against recorded sessions or work with "
            "portable replay bundles."
        ),
    )
    replay_subparsers = replay_parser.add_subparsers(
        dest="replay_command",
        required=True,
    )

    replay_run_parser = replay_subparsers.add_parser(
        "run",
        help="replay a recorded session offline",
        description=(
            "Replay a recorded session against the current codebase and report "
            "whether behavior still matches the recorded baseline."
        ),
    )
    replay_run_parser.add_argument("session_id", type=_parse_uuid)
    replay_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured replay report as JSON",
    )
    _add_runtime_location_arguments(replay_run_parser)

    replay_bundle_parser = replay_subparsers.add_parser(
        "bundle",
        help="work with portable replay bundles",
        description=(
            "Export, inspect, or run portable replay bundles without the source "
            "session database."
        ),
    )
    replay_bundle_subparsers = replay_bundle_parser.add_subparsers(
        dest="replay_bundle_command",
        required=True,
    )
    replay_bundle_export_parser = replay_bundle_subparsers.add_parser(
        "export",
        help="export a portable replay bundle",
        description=(
            "Export a recorded session into a portable replay bundle that can be "
            "checked in or replayed without the source SQLite session database."
        ),
    )
    replay_bundle_export_parser.add_argument("session_id", type=_parse_uuid)
    replay_bundle_export_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the exported replay bundle",
    )
    _add_runtime_location_arguments(replay_bundle_export_parser)

    replay_bundle_inspect_parser = replay_bundle_subparsers.add_parser(
        "inspect",
        help="inspect a portable replay bundle",
        description=(
            "Inspect and validate a portable replay bundle without running it."
        ),
    )
    replay_bundle_inspect_parser.add_argument(
        "bundle_path",
        help="path to a portable replay bundle exported with replay bundle export",
    )
    replay_bundle_inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the replay bundle inspection summary as JSON",
    )
    replay_bundle_run_parser = replay_bundle_subparsers.add_parser(
        "run",
        help="replay a portable replay bundle offline",
        description=(
            "Replay a portable replay bundle against the current codebase and "
            "report whether behavior still matches the recorded baseline."
        ),
    )
    replay_bundle_run_parser.add_argument(
        "bundle_path",
        help="path to a portable replay bundle exported with replay bundle export",
    )
    replay_bundle_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured replay report as JSON",
    )
    _add_runtime_location_arguments(replay_bundle_run_parser)
