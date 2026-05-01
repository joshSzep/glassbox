"""CLI command handlers for workspace observability summaries."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.status_observability import print_observability_report
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.knowledge_posture import build_workspace_knowledge_posture
from glassbox.runtime.observability import build_workspace_observability_report


def _observability_command(args: argparse.Namespace) -> int:
    observability_command = getattr(args, "observability_command", None)
    if observability_command == "status":
        return _observability_status_command(args)
    raise ValueError("specify an observability subcommand")


def _observability_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    runtime_status = inspect_runtime_owner(cwd, db_path=db_path)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = build_workspace_observability_report(
            workspace_root=cwd,
            runtime_status=runtime_status,
            session_repository=runtime_context.repositories.sessions,
            event_transport_stats=runtime_context.infrastructure.event_transport.stats(),
        )
        knowledge_posture = build_workspace_knowledge_posture(
            cwd,
            runtime_context.repositories.sessions,
        )

    if args.json:
        payload = report.model_dump(mode="json")
        payload["knowledge_posture"] = knowledge_posture.model_dump(mode="json")
        print_json_output(payload)
    else:
        print_observability_report(report, knowledge_posture)
    return 0
