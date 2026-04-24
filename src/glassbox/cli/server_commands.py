"""CLI command handlers for web server commands."""

from __future__ import annotations

import argparse

from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.web import WebServerConfig
from glassbox.web import run_server


def _serve_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    dashboard_url = WebServerConfig(host=args.host, port=args.port).dashboard_url
    print(f"Dashboard available at {dashboard_url}")
    print("Use ?session=SESSION_ID to open a specific session in the dashboard.")
    run_server(cwd, host=args.host, port=args.port, db_path=db_path)
    return 0
