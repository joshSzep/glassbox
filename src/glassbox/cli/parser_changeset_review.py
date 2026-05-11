"""Changeset review and verification parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_changeset_review_parsers(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    verification_plan_parser = changeset_subparsers.add_parser(
        "verification-plan",
        help="preview verification plan for a changeset or path list",
        description=(
            "Preview recommended verification commands, eval profiles, recipes, "
            "and retained evidence without running commands."
        ),
    )
    verification_plan_parser.add_argument("changeset_id", nargs="?", type=_parse_uuid)
    verification_plan_parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        default=[],
        help=(
            "workspace-relative changed path to plan for when no changeset ID is "
            "available; may be repeated"
        ),
    )
    verification_plan_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(verification_plan_parser)

    select_parser = changeset_subparsers.add_parser(
        "verification-select",
        help="record operator selection for a verification plan entry",
        description=(
            "Persist that a previewed verification plan entry was selected. "
            "This records local evidence but does not run the command."
        ),
    )
    select_parser.add_argument("changeset_id", type=_parse_uuid)
    select_parser.add_argument(
        "--verification", dest="verification_id", type=_parse_uuid, required=True
    )
    select_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(select_parser)

    skip_parser = changeset_subparsers.add_parser(
        "verification-skip",
        help="record an explicit skip for a verification plan entry",
        description=(
            "Persist an operator skip for a previewed verification plan entry. "
            "A skipped check is not represented as passed."
        ),
    )
    skip_parser.add_argument("changeset_id", type=_parse_uuid)
    skip_parser.add_argument(
        "--verification", dest="verification_id", type=_parse_uuid, required=True
    )
    skip_parser.add_argument("--reason", required=True)
    skip_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(skip_parser)

    accept_risk_parser = changeset_subparsers.add_parser(
        "verification-accept-risk",
        help="record accepted residual risk for a verification plan entry",
        description=(
            "Persist local accepted-risk evidence for a previewed verification "
            "plan entry without treating the check as passed."
        ),
    )
    accept_risk_parser.add_argument("changeset_id", type=_parse_uuid)
    accept_risk_parser.add_argument(
        "--verification",
        dest="verification_id",
        type=_parse_uuid,
        required=True,
    )
    accept_risk_parser.add_argument("--reason", required=True)
    accept_risk_parser.add_argument(
        "--risk",
        dest="residual_risks",
        action="append",
        default=[],
        help="residual risk statement; may be repeated",
    )
    accept_risk_parser.add_argument("--accepted-by", default="operator")
    accept_risk_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(accept_risk_parser)

    supersede_parser = changeset_subparsers.add_parser(
        "verification-supersede",
        help="record that one verification plan entry supersedes another",
        description=(
            "Persist local supersede evidence for previewed verification plan "
            "entries without running either command."
        ),
    )
    supersede_parser.add_argument("changeset_id", type=_parse_uuid)
    supersede_parser.add_argument(
        "--verification", dest="verification_id", type=_parse_uuid, required=True
    )
    supersede_parser.add_argument(
        "--replacement",
        dest="replacement_verification_id",
        type=_parse_uuid,
        required=True,
    )
    supersede_parser.add_argument("--reason", required=True)
    supersede_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(supersede_parser)

    record_verification_parser = changeset_subparsers.add_parser(
        "record-verification",
        help="record retained verification evidence for a changeset",
        description=(
            "Record changeset verification posture from existing task verification "
            "ledger evidence without running commands."
        ),
    )
    record_verification_parser.add_argument("changeset_id", type=_parse_uuid)
    record_verification_parser.add_argument("--task", dest="task_id", type=_parse_uuid)
    record_verification_parser.add_argument(
        "--verification",
        dest="verification_id",
        type=_parse_uuid,
    )
    record_verification_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(record_verification_parser)

    brief_parser = changeset_subparsers.add_parser(
        "brief",
        help="generate a reviewer-safe brief for a changeset",
        description=(
            "Generate or refresh a deterministic reviewer-safe brief artifact "
            "from retained changeset evidence."
        ),
    )
    brief_parser.add_argument("changeset_id", type=_parse_uuid)
    brief_parser.add_argument("--actor", default="operator")
    brief_parser.add_argument(
        "--format",
        choices=("summary", "markdown"),
        default="summary",
        help="text output format when --json is not used",
    )
    brief_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(brief_parser)

    commit_message_parser = changeset_subparsers.add_parser(
        "commit-message",
        help="suggest a commit message for a changeset",
        description=(
            "Draft a deterministic evidence-backed commit message suggestion "
            "without staging files or committing."
        ),
    )
    commit_message_parser.add_argument("changeset_id", type=_parse_uuid)
    commit_message_parser.add_argument(
        "--style",
        choices=("plain", "conventional"),
        default="plain",
    )
    commit_message_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(commit_message_parser)

    record_precommit_parser = changeset_subparsers.add_parser(
        "record-precommit",
        help="record retained pre-commit or eval evidence for a changeset",
        description=(
            "Record a summary-only pre-commit or eval evidence artifact and "
            "update advisory commit readiness without running hooks or committing."
        ),
    )
    record_precommit_parser.add_argument("changeset_id", type=_parse_uuid)
    record_precommit_parser.add_argument("--summary", required=True)
    record_precommit_parser.add_argument(
        "--kind",
        choices=("pre-commit", "eval-report"),
        default="pre-commit",
    )
    record_precommit_parser.add_argument(
        "--state",
        choices=("passed", "failed", "stale", "missing"),
        default=None,
    )
    record_precommit_parser.add_argument("--actor", default="operator")
    record_precommit_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(record_precommit_parser)

    commit_prep_parser = changeset_subparsers.add_parser(
        "commit-prep",
        help="show read-only commit preparation guidance for a changeset",
        description=(
            "Show commit readiness, suggested message, blockers, risky files, "
            "and safe next commands without staging files or committing."
        ),
    )
    commit_prep_parser.add_argument("changeset_id", type=_parse_uuid)
    commit_prep_parser.add_argument(
        "--style",
        choices=("plain", "conventional"),
        default="plain",
    )
    commit_prep_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(commit_prep_parser)

    handoff_readiness_parser = changeset_subparsers.add_parser(
        "handoff-readiness",
        help="show read-only final handoff posture for a changeset",
        description=(
            "Show advisory review-loop handoff posture, blockers, limitations, "
            "and safe next commands without staging, committing, pushing, "
            "opening a PR, merging, deploying, or publishing."
        ),
    )
    handoff_readiness_parser.add_argument("changeset_id", type=_parse_uuid)
    handoff_readiness_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(handoff_readiness_parser)
