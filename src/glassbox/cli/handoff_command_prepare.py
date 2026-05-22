"""Prepare/import compatibility delegation for the handoff CLI."""

import argparse

from glassbox.cli.changeset_command_lifecycle import _changeset_export_command
from glassbox.cli.session_state_commands import _session_command
from glassbox.runtime.handoff_source_resolution import resolve_handoff_prepare_source


def handoff_prepare_command(args: argparse.Namespace) -> int:
    source = resolve_handoff_prepare_source(args.handoff_prepare_source)
    if source.source_kind == "session":
        args.session_command = "export"
        return _session_command(args)
    if args.output_path is None:
        args.output_path = f"glassbox-changeset-{args.changeset_id}.json"
    return _changeset_export_command(args)


def handoff_import_command(args: argparse.Namespace) -> int:
    args.session_command = "import"
    args.triage = False
    return _session_command(args)


__all__ = ["handoff_import_command", "handoff_prepare_command"]
