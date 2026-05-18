"""Shared parser helpers for handoff profile flags."""

import argparse

from glassbox.core import HandoffIntent

_HANDOFF_INTENT_CHOICES = tuple(intent.value for intent in HandoffIntent)


def add_handoff_profile_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_labels: bool,
    format_choices: tuple[str, ...],
    format_help: str,
) -> None:
    """Add recipient-oriented handoff export profile arguments."""

    parser.add_argument(
        "--intent",
        choices=_HANDOFF_INTENT_CHOICES,
        default=HandoffIntent.REVIEW_ONLY.value,
        help="recipient intent for the export profile",
    )
    if include_labels:
        parser.add_argument(
            "--recipient",
            default=None,
            help="optional recipient label to include in the package",
        )
        parser.add_argument(
            "--exported-by",
            default=None,
            help="optional acting-operator label to include in the package",
        )
        parser.add_argument(
            "--expected-custodian",
            default=None,
            help="optional operator label expected to take custody after export",
        )
        parser.add_argument(
            "--note",
            default=None,
            help="optional handoff note to include in the package",
        )
    parser.add_argument(
        "--format",
        choices=format_choices,
        default=format_choices[0],
        help=format_help,
    )


__all__ = ["add_handoff_profile_arguments"]
