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


def _add_handoff_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    from glassbox.cli.parser_handoff_decisions import add_handoff_decision_parsers
    from glassbox.cli.parser_handoff_prepare import add_handoff_package_parsers

    handoff_parser = subparsers.add_parser(
        "handoff",
        help="prepare, inspect, import, and record local handoff decisions",
        description=(
            "Prepare, inspect, import, and record local handoff workflow state "
            "without granting approval, publication, or runtime ownership."
        ),
    )
    handoff_subparsers = handoff_parser.add_subparsers(
        dest="handoff_command",
        required=True,
    )

    def add_session_profile_arguments(parser: argparse.ArgumentParser) -> None:
        add_handoff_profile_arguments(
            parser,
            include_labels=True,
            format_choices=("json",),
            format_help="export format; session handoff packages are stable JSON",
        )

    def add_changeset_profile_arguments(parser: argparse.ArgumentParser) -> None:
        add_handoff_profile_arguments(
            parser,
            include_labels=True,
            format_choices=("json", "json+markdown"),
            format_help="export stable JSON, or JSON plus a Markdown summary",
        )

    add_handoff_package_parsers(
        handoff_subparsers,
        add_session_profile_arguments=add_session_profile_arguments,
        add_changeset_profile_arguments=add_changeset_profile_arguments,
    )
    add_handoff_decision_parsers(
        handoff_subparsers,
        intent_choices=_HANDOFF_INTENT_CHOICES,
    )


__all__ = ["_add_handoff_parsers", "add_handoff_profile_arguments"]
