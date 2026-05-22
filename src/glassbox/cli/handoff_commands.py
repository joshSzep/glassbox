"""Dispatch facade for local handoff CLI command families."""

import argparse

from glassbox.cli.handoff_command_decisions import handoff_accept_command
from glassbox.cli.handoff_command_decisions import handoff_archive_command
from glassbox.cli.handoff_command_decisions import handoff_guidance_command
from glassbox.cli.handoff_command_decisions import handoff_list_command
from glassbox.cli.handoff_command_decisions import handoff_reject_command
from glassbox.cli.handoff_command_decisions import handoff_show_command
from glassbox.cli.handoff_command_inspect import handoff_inspect_command
from glassbox.cli.handoff_command_prepare import handoff_import_command
from glassbox.cli.handoff_command_prepare import handoff_prepare_command


def _handoff_command(args: argparse.Namespace) -> int:
    if args.handoff_command == "prepare":
        return handoff_prepare_command(args)
    if args.handoff_command == "inspect":
        return handoff_inspect_command(args)
    if args.handoff_command == "import":
        return handoff_import_command(args)
    if args.handoff_command == "list":
        return handoff_list_command(args)
    if args.handoff_command == "show":
        return handoff_show_command(args)
    if args.handoff_command == "guidance":
        return handoff_guidance_command(args)
    if args.handoff_command == "accept":
        return handoff_accept_command(args)
    if args.handoff_command == "reject":
        return handoff_reject_command(args)
    if args.handoff_command == "archive":
        return handoff_archive_command(args)
    raise ValueError("specify a handoff subcommand")


__all__ = ["_handoff_command"]
