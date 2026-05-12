"""Changeset argument parser construction."""

import argparse

from glassbox.cli.parser_changeset_evidence import _add_changeset_evidence_parsers
from glassbox.cli.parser_changeset_export import _add_changeset_export_parsers
from glassbox.cli.parser_changeset_feedback import _add_changeset_feedback_parsers
from glassbox.cli.parser_changeset_review import _add_changeset_review_parsers
from glassbox.cli.parser_changeset_workup import _add_changeset_workup_parser
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

    _add_changeset_workup_parser(changeset_subparsers)

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

    evidence_graph_parser = changeset_subparsers.add_parser(
        "evidence-graph",
        help="inspect evidence graph support for a changeset",
        description=(
            "Inspect derived evidence graph support for a changeset without "
            "reading raw artifacts or command logs."
        ),
    )
    evidence_graph_parser.add_argument("changeset_id", type=_parse_uuid)
    evidence_graph_parser.add_argument("--json", action="store_true")
    evidence_graph_parser.add_argument(
        "--summary",
        action="store_true",
        help="print only graph counts and claim posture",
    )
    evidence_graph_parser.add_argument(
        "--claim-id",
        help="return one claim support record by ID",
    )
    evidence_graph_parser.add_argument(
        "--node-id",
        help="return a bounded neighborhood around one node ID",
    )
    evidence_graph_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="neighborhood depth for --node-id",
    )
    evidence_graph_parser.add_argument(
        "--reviewer-safe",
        action="store_true",
        help="omit operator-only and local-only graph nodes",
    )
    _add_runtime_location_arguments(evidence_graph_parser)

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

    _add_changeset_export_parsers(changeset_subparsers)
    _add_changeset_review_parsers(changeset_subparsers)
    _add_changeset_evidence_parsers(changeset_subparsers)
    _add_changeset_feedback_parsers(changeset_subparsers)

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
