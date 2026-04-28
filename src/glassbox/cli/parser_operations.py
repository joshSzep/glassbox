"""Operational command argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _hide_subparser_from_help
from glassbox.cli.parser_common import _parse_port
from glassbox.cli.parser_common import _parse_uuid


def _add_operations_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    observability_parser = subparsers.add_parser(
        "observability",
        help="summarize runtime, projection, and verification health",
        description=(
            "Summarize workspace runtime health, projection lag, event transport "
            "state, and retained verification activity."
        ),
    )
    observability_subparsers = observability_parser.add_subparsers(
        dest="observability_command",
        required=True,
    )

    observability_status_parser = observability_subparsers.add_parser(
        "status",
        help="print a workspace observability summary",
        description="Print a workspace observability summary and next actions.",
    )
    observability_status_parser.add_argument(
        "--json",
        action="store_true",
        help="print the observability report as JSON",
    )
    _add_runtime_location_arguments(observability_status_parser)

    provider_parser = subparsers.add_parser(
        "provider",
        help="diagnose provider runtime configuration",
        description="Inspect redacted provider runtime configuration diagnostics.",
    )
    provider_subparsers = provider_parser.add_subparsers(
        dest="provider_command",
        required=True,
    )
    provider_diagnostics_parser = provider_subparsers.add_parser(
        "diagnostics",
        help="print provider setup diagnostics",
        description=(
            "Print redacted provider setup diagnostics before starting a live "
            "session or provider canary."
        ),
    )
    provider_diagnostics_parser.add_argument(
        "--model-name",
        default=None,
        help="model identifier to diagnose; overrides glassbox.profile.json",
    )
    provider_diagnostics_parser.add_argument(
        "--json",
        action="store_true",
        help="print provider diagnostics as JSON",
    )
    _add_runtime_location_arguments(provider_diagnostics_parser)

    performance_parser = subparsers.add_parser(
        "performance",
        help="inspect larger-session performance expectations",
        description="Inspect repository-owned larger-session performance budgets.",
    )
    performance_subparsers = performance_parser.add_subparsers(
        dest="performance_command",
        required=True,
    )

    performance_subparsers.add_parser(
        "budgets",
        help="print performance budgets and mitigation guidance",
        description=(
            "Print explicit performance budgets and operator mitigation guidance "
            "for larger local workspaces."
        ),
    )

    projection_parser = subparsers.add_parser(
        "projection",
        help="inspect or rebuild derived projections",
        description=(
            "Inspect projection health or rebuild projection tables from "
            "canonical persisted events."
        ),
    )
    projection_subparsers = projection_parser.add_subparsers(
        dest="projection_command",
        required=True,
    )

    projection_check_parser = projection_subparsers.add_parser(
        "check",
        help="inspect projection health without rebuilding",
        description="Inspect projection health without rebuilding derived tables.",
    )
    projection_check_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    projection_check_parser.add_argument(
        "--all",
        action="store_true",
        help="check projections for all sessions in the database",
    )
    _add_runtime_location_arguments(projection_check_parser)

    projection_rebuild_parser = projection_subparsers.add_parser(
        "rebuild",
        help="rebuild derived projections",
        description="Rebuild projection tables from canonical persisted events.",
    )
    projection_rebuild_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    projection_rebuild_parser.add_argument(
        "--all",
        action="store_true",
        help="rebuild projections for all sessions in the database",
    )
    _add_runtime_location_arguments(projection_rebuild_parser)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="work with the browser dashboard",
        description="Start the browser dashboard for the selected workspace.",
    )
    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_command",
        required=True,
    )

    serve_parser = dashboard_subparsers.add_parser(
        "serve",
        help="start the dashboard server",
        description=(
            "Start the web dashboard server for the selected workspace database."
        ),
    )
    _add_runtime_location_arguments(serve_parser)
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the server to",
    )
    serve_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help="port to bind the server to",
    )

    daemon_parser = subparsers.add_parser(
        "daemon",
        help="manage the workspace background runtime owner",
        description=(
            "Start, inspect, or stop the persistent background runtime owner "
            "for the selected workspace."
        ),
    )
    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command",
        metavar="{start,stop,status}",
        required=True,
    )

    daemon_start_parser = daemon_subparsers.add_parser(
        "start",
        help="start the workspace daemon",
        description="Start the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_start_parser)
    daemon_start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the daemon dashboard to",
    )
    daemon_start_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help="port to bind the daemon dashboard to",
    )

    daemon_stop_parser = daemon_subparsers.add_parser(
        "stop",
        help="stop the workspace daemon",
        description="Stop the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_stop_parser)

    daemon_status_parser = daemon_subparsers.add_parser(
        "status",
        help="inspect the workspace daemon",
        description="Inspect the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_status_parser)
    daemon_status_parser.add_argument(
        "--json",
        action="store_true",
        help="print daemon discovery and health details as JSON",
    )

    daemon_run_owner_parser = daemon_subparsers.add_parser(
        "run-owner",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    _hide_subparser_from_help(daemon_subparsers, "run-owner")
    _add_runtime_location_arguments(daemon_run_owner_parser)
    daemon_run_owner_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=argparse.SUPPRESS,
    )
    daemon_run_owner_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help=argparse.SUPPRESS,
    )
