"""Changeset argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_changeset_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "changeset",
        aliases=["changesets"],
        help="create and inspect reviewable local changesets",
        description="Create and inspect explicit local changeset evidence.",
    )
    changeset_subparsers = parser.add_subparsers(
        dest="changeset_command",
        required=True,
    )

    create_parser = changeset_subparsers.add_parser(
        "create",
        help="create a changeset from retained local evidence",
        description=(
            "Create one local changeset from a session, task, candidate, "
            "or workspace diff."
        ),
    )
    create_parser.add_argument(
        "--from",
        dest="source_kind",
        choices=("session", "task", "branch-candidate", "workspace-diff"),
        required=True,
        help="source evidence used for the changeset",
    )
    create_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    create_parser.add_argument("--task", dest="task_id", type=_parse_uuid)
    create_parser.add_argument(
        "--branch-search", dest="branch_search_id", type=_parse_uuid
    )
    create_parser.add_argument("--candidate", dest="candidate_id", type=_parse_uuid)
    create_parser.add_argument("--objective")
    create_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(create_parser)

    adoption_preview_parser = changeset_subparsers.add_parser(
        "adoption-preview",
        help="preview adopting a selected branch-search candidate",
        description=(
            "Preview candidate diff, verification, risk, worktree state, and "
            "limitations before adopting branch-search evidence into a changeset."
        ),
    )
    adoption_preview_parser.add_argument(
        "--branch-search",
        dest="branch_search_id",
        type=_parse_uuid,
        required=True,
    )
    adoption_preview_parser.add_argument(
        "--candidate",
        dest="candidate_id",
        type=_parse_uuid,
        required=True,
    )
    adoption_preview_parser.add_argument(
        "--worktree", dest="worktree_id", type=_parse_uuid
    )
    adoption_preview_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(adoption_preview_parser)

    adopt_candidate_parser = changeset_subparsers.add_parser(
        "adopt-candidate",
        help="adopt a selected branch-search candidate into a changeset",
        description=(
            "Record selected branch-search candidate adoption as changeset "
            "evidence after explicit confirmation. This does not merge, commit, "
            "push, or open a PR."
        ),
    )
    adopt_candidate_parser.add_argument(
        "--branch-search",
        dest="branch_search_id",
        type=_parse_uuid,
        required=True,
    )
    adopt_candidate_parser.add_argument(
        "--candidate",
        dest="candidate_id",
        type=_parse_uuid,
        required=True,
    )
    adopt_candidate_parser.add_argument(
        "--worktree", dest="worktree_id", type=_parse_uuid
    )
    adopt_candidate_parser.add_argument("--objective")
    adopt_candidate_parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm adoption after reviewing adoption-preview output",
    )
    adopt_candidate_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(adopt_candidate_parser)

    list_parser = changeset_subparsers.add_parser(
        "list",
        help="list changesets",
        description="List recent local changesets.",
    )
    list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    list_parser.add_argument("--include-archived", action="store_true")
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = changeset_subparsers.add_parser(
        "show",
        help="show changeset details",
        description="Show changeset source references and basic review evidence.",
    )
    show_parser.add_argument("changeset_id", type=_parse_uuid)
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    refresh_parser = changeset_subparsers.add_parser(
        "refresh",
        help="refresh structured change inventory for a changeset",
        description=(
            "Refresh structured workspace-diff inventory evidence without staging "
            "files or making review-readiness claims."
        ),
    )
    refresh_parser.add_argument("changeset_id", type=_parse_uuid)
    refresh_parser.add_argument("--actor", default="operator")
    refresh_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(refresh_parser)

    verification_plan_parser = changeset_subparsers.add_parser(
        "verification-plan",
        help="preview verification plan for a changeset",
        description=(
            "Preview recommended verification commands, eval profiles, recipes, "
            "and retained evidence without running commands."
        ),
    )
    verification_plan_parser.add_argument("changeset_id", type=_parse_uuid)
    verification_plan_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(verification_plan_parser)

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

    export_parser = changeset_subparsers.add_parser(
        "export",
        help="write a reviewer-safe changeset evidence package",
        description=(
            "Write a changeset-centered evidence package with redacted summaries, "
            "artifact references, verification posture, and non-claims."
        ),
    )
    export_parser.add_argument("changeset_id", type=_parse_uuid)
    export_parser.add_argument("output_path")
    export_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(export_parser)

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

    archive_parser = changeset_subparsers.add_parser(
        "archive",
        help="archive a changeset",
        description="Archive a changeset after explicit operator intent.",
    )
    archive_parser.add_argument("changeset_id", type=_parse_uuid)
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--actor", default="operator")
    archive_parser.add_argument(
        "--replacement", dest="replacement_changeset_id", type=_parse_uuid
    )
    archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(archive_parser)


__all__ = ["_add_changeset_parsers"]
