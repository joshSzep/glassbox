"""CLI package entrypoint for Glassbox."""

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Compatibility wrapper for the package entrypoint."""

    from glassbox.cli.entry import run_main

    return run_main(argv)
