"""Changeset argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _parse_viewport(value: str) -> tuple[int, int]:
    try:
        width_raw, height_raw = value.lower().split("x", 1)
        width = int(width_raw)
        height = int(height_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "viewport must use WIDTHxHEIGHT, for example 1440x900"
        ) from exc
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("viewport dimensions must be positive")
    return width, height


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

    evidence_parser = changeset_subparsers.add_parser(
        "evidence",
        help="attach and inspect manual review-loop evidence",
        description=(
            "Attach local manual evidence to a changeset without claiming "
            "Glassbox ran the command, check, or observation."
        ),
    )
    evidence_subparsers = evidence_parser.add_subparsers(
        dest="evidence_command",
        required=True,
    )

    evidence_attach_parser = evidence_subparsers.add_parser(
        "attach",
        help="attach summary-first manual evidence to a changeset",
    )
    evidence_attach_parser.add_argument("changeset_id", type=_parse_uuid)
    evidence_attach_parser.add_argument(
        "--kind",
        choices=(
            "manual_command",
            "external_check",
            "reviewer_note",
            "screenshot",
            "browser_observation",
            "accessibility_note",
            "local_file_reference",
            "sanitized_log",
            "operator_assertion",
        ),
        required=True,
    )
    evidence_attach_parser.add_argument("--summary", required=True)
    evidence_attach_parser.add_argument("--source-label", required=True)
    evidence_attach_parser.add_argument("--note")
    evidence_attach_parser.add_argument("--command", dest="command_text")
    evidence_attach_parser.add_argument("--external-url-label")
    evidence_attach_parser.add_argument("--local-file")
    evidence_attach_parser.add_argument("--local-file-label")
    evidence_attach_parser.add_argument(
        "--feedback", dest="feedback_id", type=_parse_uuid
    )
    evidence_attach_parser.add_argument(
        "--target-kind",
        choices=(
            "changeset",
            "feedback",
            "response",
            "verification_requirement",
            "review_brief",
            "publication_boundary",
            "unknown",
        ),
        default="changeset",
    )
    evidence_attach_parser.add_argument("--target-id")
    evidence_attach_parser.add_argument(
        "--freshness",
        choices=("current", "needs_inspection", "stale", "unknown"),
        default="unknown",
    )
    evidence_attach_parser.add_argument("--actor", default="operator")
    evidence_attach_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_attach_parser)

    def add_browser_dashboard_arguments(
        parser: argparse.ArgumentParser,
        *,
        capture_kind: str,
    ) -> None:
        parser.add_argument("changeset_id", type=_parse_uuid)
        parser.add_argument("--summary", required=True)
        parser.add_argument("--source-label", required=True)
        parser.add_argument("--route", dest="route_label", required=True)
        parser.add_argument("--environment", required=True)
        parser.add_argument("--browser", default="unknown")
        parser.add_argument("--viewport", type=_parse_viewport, required=True)
        parser.add_argument("--observed-at")
        parser.add_argument("--input-method", default="unknown")
        parser.add_argument("--console-checked", action="store_true", default=None)
        parser.add_argument(
            "--console-not-checked",
            action="store_false",
            dest="console_checked",
        )
        parser.add_argument("--screenshot-file", dest="screenshot_path_hint")
        parser.add_argument(
            "--screenshot-label",
            default="local screenshot metadata",
        )
        parser.add_argument("--screenshot-media-type", default="image/png")
        parser.add_argument("--screenshot-size-bytes", type=int)
        parser.add_argument("--screenshot-width", type=int)
        parser.add_argument("--screenshot-height", type=int)
        parser.add_argument("--skipped-case", action="append", default=[])
        parser.add_argument("--limitation", action="append", default=[])
        parser.add_argument("--feedback", dest="feedback_id", type=_parse_uuid)
        parser.add_argument(
            "--target-kind",
            choices=(
                "changeset",
                "feedback",
                "response",
                "verification_requirement",
                "review_brief",
                "publication_boundary",
                "unknown",
            ),
            default="changeset",
        )
        parser.add_argument("--target-id")
        parser.add_argument(
            "--freshness",
            choices=("current", "needs_inspection", "stale", "unknown"),
            default="unknown",
        )
        parser.add_argument("--actor", default="operator")
        parser.add_argument("--json", action="store_true")
        parser.set_defaults(evidence_capture_kind=capture_kind)
        _add_runtime_location_arguments(parser)

    evidence_browser_parser = evidence_subparsers.add_parser(
        "browser",
        help="attach advisory browser observation evidence to a changeset",
    )
    add_browser_dashboard_arguments(
        evidence_browser_parser,
        capture_kind="browser_check",
    )

    evidence_dashboard_parser = evidence_subparsers.add_parser(
        "dashboard",
        help="attach advisory dashboard walkthrough evidence to a changeset",
    )
    add_browser_dashboard_arguments(
        evidence_dashboard_parser,
        capture_kind="dashboard_walkthrough",
    )

    evidence_accessibility_parser = evidence_subparsers.add_parser(
        "accessibility",
        help="attach advisory accessibility observation evidence to a changeset",
    )
    evidence_accessibility_parser.add_argument("changeset_id", type=_parse_uuid)
    evidence_accessibility_parser.add_argument(
        "--kind",
        dest="observation_kind",
        choices=(
            "keyboard_pass",
            "screen_reader_note",
            "focus_order_issue",
            "wrapping_issue",
            "contrast_observation",
            "responsive_review",
        ),
        required=True,
    )
    evidence_accessibility_parser.add_argument("--summary", required=True)
    evidence_accessibility_parser.add_argument("--source-label", required=True)
    evidence_accessibility_parser.add_argument("--environment", required=True)
    evidence_accessibility_parser.add_argument("--observed-issue", required=True)
    evidence_accessibility_parser.add_argument("--tool", default="manual")
    evidence_accessibility_parser.add_argument("--route", dest="route_label")
    evidence_accessibility_parser.add_argument("--reviewer-label")
    evidence_accessibility_parser.add_argument(
        "--severity",
        choices=("info", "low", "medium", "high", "blocker"),
        default="medium",
    )
    evidence_accessibility_parser.add_argument(
        "--disposition",
        choices=(
            "open",
            "paired_with_feedback",
            "resolved_locally",
            "accepted_with_risk",
            "needs_follow_up",
        ),
        default="open",
    )
    evidence_accessibility_parser.add_argument("--follow-up")
    evidence_accessibility_parser.add_argument("--paired-tool-output-label")
    evidence_accessibility_parser.add_argument(
        "--skipped-case", action="append", default=[]
    )
    evidence_accessibility_parser.add_argument(
        "--limitation", action="append", default=[]
    )
    evidence_accessibility_parser.add_argument(
        "--feedback",
        dest="feedback_id",
        type=_parse_uuid,
    )
    evidence_accessibility_parser.add_argument(
        "--target-kind",
        choices=(
            "changeset",
            "feedback",
            "response",
            "verification_requirement",
            "review_brief",
            "publication_boundary",
            "unknown",
        ),
        default="changeset",
    )
    evidence_accessibility_parser.add_argument("--target-id")
    evidence_accessibility_parser.add_argument(
        "--freshness",
        choices=("current", "needs_inspection", "stale", "unknown"),
        default="unknown",
    )
    evidence_accessibility_parser.add_argument("--actor", default="operator")
    evidence_accessibility_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_accessibility_parser)

    evidence_list_parser = evidence_subparsers.add_parser(
        "list",
        help="list manual evidence for a changeset or target",
    )
    evidence_list_parser.add_argument(
        "--changeset", dest="changeset_id", type=_parse_uuid
    )
    evidence_list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    evidence_list_parser.add_argument(
        "--state",
        choices=("attached", "superseded", "rejected", "archived"),
    )
    evidence_list_parser.add_argument("--include-archived", action="store_true")
    evidence_list_parser.add_argument("--include-rejected", action="store_true")
    evidence_list_parser.add_argument("--include-superseded", action="store_true")
    evidence_list_parser.add_argument("--limit", type=int, default=None)
    evidence_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_list_parser)

    feedback_parser = changeset_subparsers.add_parser(
        "feedback",
        help="record and inspect local review feedback",
        description=(
            "Record local review feedback evidence for changesets. Feedback is "
            "not approval and does not stage, commit, push, open a PR, or merge."
        ),
    )
    feedback_subparsers = feedback_parser.add_subparsers(
        dest="feedback_command",
        required=True,
    )

    feedback_add_parser = feedback_subparsers.add_parser(
        "add",
        help="add local review feedback evidence to a changeset",
    )
    feedback_add_parser.add_argument("changeset_id", type=_parse_uuid)
    feedback_add_parser.add_argument(
        "--kind",
        choices=(
            "requested_change",
            "reviewer_question",
            "operator_note",
            "observation",
            "risk",
        ),
        required=True,
    )
    feedback_add_parser.add_argument("--summary", required=True)
    feedback_add_parser.add_argument("--body")
    feedback_add_parser.add_argument(
        "--provenance",
        choices=("reviewer", "operator", "manual", "imported", "unknown"),
        default="manual",
    )
    feedback_add_parser.add_argument("--source-label")
    feedback_add_parser.add_argument("--reviewer-label")
    feedback_add_parser.add_argument("--actor", default="operator")
    feedback_add_parser.add_argument(
        "--scope-kind",
        choices=(
            "changeset",
            "file",
            "task",
            "turn",
            "artifact",
            "verification",
            "branch_candidate",
        ),
        default="changeset",
    )
    feedback_add_parser.add_argument("--scope-reason")
    feedback_add_parser.add_argument("--file")
    feedback_add_parser.add_argument("--line-start", type=int)
    feedback_add_parser.add_argument("--line-end", type=int)
    feedback_add_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_add_parser)

    feedback_list_parser = feedback_subparsers.add_parser(
        "list",
        help="list local review feedback",
    )
    feedback_list_parser.add_argument(
        "--changeset", dest="changeset_id", type=_parse_uuid
    )
    feedback_list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    feedback_list_parser.add_argument(
        "--disposition",
        choices=(
            "open",
            "in_progress",
            "responded",
            "resolved_locally",
            "accepted_with_risk",
            "archived",
        ),
    )
    feedback_list_parser.add_argument("--include-archived", action="store_true")
    feedback_list_parser.add_argument("--file")
    feedback_list_parser.add_argument("--limit", type=int, default=None)
    feedback_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_list_parser)

    feedback_show_parser = feedback_subparsers.add_parser(
        "show",
        help="show local review feedback details",
    )
    feedback_show_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_show_parser)

    feedback_status_parser = feedback_subparsers.add_parser(
        "status",
        help="show response status for feedback on one changeset",
        description=(
            "Show open, responded, unresolved, stale, blocked, and accepted-risk "
            "review response status without mutating git."
        ),
    )
    feedback_status_parser.add_argument("changeset_id", type=_parse_uuid)
    feedback_status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_status_parser)

    feedback_resolve_parser = feedback_subparsers.add_parser(
        "resolve",
        help="mark feedback resolved locally with retained response text",
    )
    feedback_resolve_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_resolve_parser.add_argument("--summary", required=True)
    feedback_resolve_parser.add_argument("--residual-risk")
    feedback_resolve_parser.add_argument("--actor", default="operator")
    feedback_resolve_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_resolve_parser)

    feedback_reopen_parser = feedback_subparsers.add_parser(
        "reopen",
        help="reopen previously handled local review feedback",
    )
    feedback_reopen_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_reopen_parser.add_argument("--reason", required=True)
    feedback_reopen_parser.add_argument("--actor", default="operator")
    feedback_reopen_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_reopen_parser)

    feedback_archive_parser = feedback_subparsers.add_parser(
        "archive",
        help="archive feedback after explicit operator intent",
    )
    feedback_archive_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_archive_parser.add_argument("--reason", required=True)
    feedback_archive_parser.add_argument("--actor", default="operator")
    feedback_archive_parser.add_argument(
        "--replacement", dest="replacement_feedback_id", type=_parse_uuid
    )
    feedback_archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_archive_parser)

    feedback_accept_risk_parser = feedback_subparsers.add_parser(
        "accept-risk",
        help="mark feedback accepted with explicit local residual risk",
    )
    feedback_accept_risk_parser.add_argument("feedback_id", type=_parse_uuid)
    feedback_accept_risk_parser.add_argument("--risk-summary", required=True)
    feedback_accept_risk_parser.add_argument("--reason", required=True)
    feedback_accept_risk_parser.add_argument("--actor", default="operator")
    feedback_accept_risk_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(feedback_accept_risk_parser)


__all__ = ["_add_changeset_parsers"]
