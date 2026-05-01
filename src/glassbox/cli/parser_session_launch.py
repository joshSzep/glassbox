"""Interactive launch parser wiring for session commands."""

import argparse


def add_interactive_launch_arguments(parser: argparse.ArgumentParser) -> None:
    launch_group = parser.add_mutually_exclusive_group()
    launch_group.add_argument(
        "--plain",
        dest="interactive_launch_mode",
        action="store_const",
        const="plain",
        default=None,
        help="run the line-oriented compatibility terminal experience",
    )
    launch_group.add_argument(
        "--tui",
        dest="interactive_launch_mode",
        action="store_const",
        const="tui",
        default=None,
        help="request the full-screen terminal UI when the migration gate enables it",
    )


__all__ = ["add_interactive_launch_arguments"]
