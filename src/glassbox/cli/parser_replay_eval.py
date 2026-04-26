"""Replay and eval argument parser construction."""

import argparse

from glassbox.cli.parser_common import _EVAL_BASELINE_REFRESH_POLICY_CHOICES
from glassbox.cli.parser_common import _EVAL_EXPECTATION_MODE_CHOICES
from glassbox.cli.parser_common import _EVAL_INVARIANT_CHOICES
from glassbox.cli.parser_common import _EVAL_PROFILE_TRACK_CHOICES
from glassbox.cli.parser_common import _EVAL_SEVERITY_CHOICES
from glassbox.cli.parser_common import _EVAL_VERIFICATION_STAGE_CHOICES
from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_replay_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    replay_parser = subparsers.add_parser(
        "replay",
        help="run replay-backed baselines or work with portable bundles",
        description=(
            "Run replay verification against recorded sessions or work with "
            "portable replay bundles."
        ),
    )
    replay_subparsers = replay_parser.add_subparsers(
        dest="replay_command",
        required=True,
    )

    replay_run_parser = replay_subparsers.add_parser(
        "run",
        help="replay a recorded session offline",
        description=(
            "Replay a recorded session against the current codebase and report "
            "whether behavior still matches the recorded baseline."
        ),
    )
    replay_run_parser.add_argument("session_id", type=_parse_uuid)
    replay_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured replay report as JSON",
    )
    _add_runtime_location_arguments(replay_run_parser)

    replay_bundle_parser = replay_subparsers.add_parser(
        "bundle",
        help="work with portable replay bundles",
        description=(
            "Export, inspect, or run portable replay bundles without the source "
            "session database."
        ),
    )
    replay_bundle_subparsers = replay_bundle_parser.add_subparsers(
        dest="replay_bundle_command",
        required=True,
    )
    replay_bundle_export_parser = replay_bundle_subparsers.add_parser(
        "export",
        help="export a portable replay bundle",
        description=(
            "Export a recorded session into a portable replay bundle that can be "
            "checked in or replayed without the source SQLite session database."
        ),
    )
    replay_bundle_export_parser.add_argument("session_id", type=_parse_uuid)
    replay_bundle_export_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the exported replay bundle",
    )
    _add_runtime_location_arguments(replay_bundle_export_parser)

    replay_bundle_inspect_parser = replay_bundle_subparsers.add_parser(
        "inspect",
        help="inspect a portable replay bundle",
        description=(
            "Inspect and validate a portable replay bundle without running it."
        ),
    )
    replay_bundle_inspect_parser.add_argument(
        "bundle_path",
        help="path to a portable replay bundle exported with replay bundle export",
    )
    replay_bundle_inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the replay bundle inspection summary as JSON",
    )
    replay_bundle_run_parser = replay_bundle_subparsers.add_parser(
        "run",
        help="replay a portable replay bundle offline",
        description=(
            "Replay a portable replay bundle against the current codebase and "
            "report whether behavior still matches the recorded baseline."
        ),
    )
    replay_bundle_run_parser.add_argument(
        "bundle_path",
        help="path to a portable replay bundle exported with replay bundle export",
    )
    replay_bundle_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured replay report as JSON",
    )
    _add_runtime_location_arguments(replay_bundle_run_parser)


def _add_eval_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    eval_parser = subparsers.add_parser(
        "eval",
        help="run replay-backed eval suites",
        description=(
            "Run repository-local replay-backed eval cases and report a suite "
            "summary suitable for local validation or CI."
        ),
    )
    eval_subparsers = eval_parser.add_subparsers(
        dest="eval_command",
        required=True,
    )

    eval_run_parser = eval_subparsers.add_parser(
        "run",
        help="run one or more eval cases",
        description=(
            "Run discovered eval cases from the repository-local evals/ layout. "
            "Case IDs and tags narrow the selected suite."
        ),
    )
    eval_run_parser.add_argument(
        "case_ids",
        nargs="*",
        help="optional eval case IDs to run; defaults to all discovered cases",
    )
    eval_run_parser.add_argument(
        "--profile",
        default=None,
        help=(
            "named repository-owned verification profile to run before extra narrowing"
        ),
    )
    eval_run_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="require a tag on selected eval cases; repeat to require multiple tags",
    )
    eval_run_parser.add_argument(
        "--output-dir",
        default=None,
        help="directory for suite summary and per-case replay artifacts",
    )
    eval_run_parser.add_argument(
        "--refresh-output-dir",
        action="store_true",
        help=(
            "clear prior generated JSON artifacts in a managed .glassbox/evals/ "
            "output directory before writing the new suite result"
        ),
    )
    eval_run_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured eval suite report as JSON",
    )
    _add_runtime_location_arguments(eval_run_parser)

    eval_audit_parser = eval_subparsers.add_parser(
        "audit",
        help="audit capability coverage against the selected eval portfolio",
        description=(
            "Audit repository-local capability coverage expectations against the "
            "selected eval cases without executing replay bundles."
        ),
    )
    eval_audit_parser.add_argument(
        "case_ids",
        nargs="*",
        help="optional eval case IDs to audit; defaults to the selected suite",
    )
    eval_audit_parser.add_argument(
        "--profile",
        default=None,
        help=(
            "named repository-owned verification profile to audit before extra "
            "narrowing"
        ),
    )
    eval_audit_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="require a tag on selected eval cases; repeat to require multiple tags",
    )
    eval_audit_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured coverage audit report as JSON",
    )
    _add_runtime_location_arguments(eval_audit_parser)

    eval_profile_parser = eval_subparsers.add_parser(
        "profile",
        help="work with repository-owned eval profiles",
        description="Inspect repository-owned eval profiles and tracks.",
    )
    eval_profile_subparsers = eval_profile_parser.add_subparsers(
        dest="eval_profile_command",
        required=True,
    )

    eval_profile_list_parser = eval_profile_subparsers.add_parser(
        "list",
        help="list repository-owned eval profiles",
        description=(
            "List repository-owned eval profiles and optionally narrow them by "
            "deterministic or live-provider-canary track."
        ),
    )
    eval_profile_list_parser.add_argument(
        "--track",
        choices=_EVAL_PROFILE_TRACK_CHOICES,
        default=None,
        help="optional profile track filter",
    )
    eval_profile_list_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured profile listing as JSON",
    )
    _add_runtime_location_arguments(eval_profile_list_parser)

    eval_profile_show_parser = eval_profile_subparsers.add_parser(
        "show",
        help="show one repository-owned eval profile",
        description="Show one repository-owned eval profile definition.",
    )
    eval_profile_show_parser.add_argument("profile_id")
    eval_profile_show_parser.add_argument(
        "--json",
        action="store_true",
        help="print the eval profile definition as JSON",
    )
    _add_runtime_location_arguments(eval_profile_show_parser)

    eval_recommend_parser = eval_subparsers.add_parser(
        "recommend",
        help="recommend replay or eval scope for a change set",
        description=(
            "Recommend repository-owned replay cases and eval profiles from a set "
            "of touched workspace paths using the eval impact manifest and "
            "existing case, coverage, and profile metadata."
        ),
    )
    eval_recommend_parser.add_argument(
        "paths",
        nargs="+",
        help="one or more changed workspace paths to analyze",
    )
    eval_recommend_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured recommendation report as JSON",
    )
    _add_runtime_location_arguments(eval_recommend_parser)

    eval_report_parser = eval_subparsers.add_parser(
        "report",
        help="generate a release sign-off report from named eval profiles",
        description=(
            "Run one or more named repository-owned eval profiles and aggregate "
            "their retained evidence into a release-oriented sign-off report."
        ),
    )
    eval_report_parser.add_argument(
        "profile_ids",
        nargs="+",
        help="one or more named profiles to include in the release sign-off report",
    )
    eval_report_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help=(
            "require a tag on selected eval cases inside each requested profile; "
            "repeat to require multiple tags"
        ),
    )
    eval_report_parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "directory for the generated release sign-off report and per-profile "
            "eval artifacts"
        ),
    )
    eval_report_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured release sign-off report as JSON",
    )
    _add_runtime_location_arguments(eval_report_parser)

    eval_case_parser = eval_subparsers.add_parser(
        "case",
        help="work with repository-owned eval cases",
        description="Inspect, promote, or refresh repository-owned eval cases.",
    )
    eval_case_subparsers = eval_case_parser.add_subparsers(
        dest="eval_case_command",
        required=True,
    )

    eval_case_list_parser = eval_case_subparsers.add_parser(
        "list",
        help="list repository-owned eval cases",
        description="List repository-owned eval case manifests.",
    )
    eval_case_list_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="require a tag on listed eval cases; repeat to require multiple tags",
    )
    eval_case_list_parser.add_argument(
        "--json",
        action="store_true",
        help="print eval case summaries as JSON",
    )
    _add_runtime_location_arguments(eval_case_list_parser)

    eval_case_show_parser = eval_case_subparsers.add_parser(
        "show",
        help="show one repository-owned eval case",
        description="Show one repository-owned eval case manifest.",
    )
    eval_case_show_parser.add_argument("case_id")
    eval_case_show_parser.add_argument(
        "--json",
        action="store_true",
        help="print the eval case manifest as JSON",
    )
    _add_runtime_location_arguments(eval_case_show_parser)

    eval_promote_parser = eval_case_subparsers.add_parser(
        "promote",
        help="promote one recorded session into a new eval case",
        description=(
            "Export a replayable session into evals/bundles/ and create a new "
            "repository-local eval case manifest in one guided step."
        ),
    )
    eval_promote_parser.add_argument("case_id")
    eval_promote_parser.add_argument("session_id", type=_parse_uuid)
    eval_promote_parser.add_argument("--title", required=True)
    eval_promote_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="tag to add to the promoted eval case; repeat as needed",
    )
    eval_promote_parser.add_argument("--notes", default=None)
    eval_promote_parser.add_argument(
        "--reason",
        default=None,
        help="optional initial promotion note stored in the case history",
    )
    eval_promote_parser.add_argument(
        "--expectation-mode",
        choices=_EVAL_EXPECTATION_MODE_CHOICES,
        default="exact_match",
    )
    eval_promote_parser.add_argument(
        "--invariant",
        dest="invariants",
        action="append",
        default=[],
        choices=_EVAL_INVARIANT_CHOICES,
        help="selected invariant for the case; repeat as needed",
    )
    eval_promote_parser.add_argument("--owner", default=None)
    eval_promote_parser.add_argument(
        "--capability",
        dest="capabilities",
        action="append",
        default=[],
        help="capability protected by the case; repeat as needed",
    )
    eval_promote_parser.add_argument(
        "--severity",
        choices=_EVAL_SEVERITY_CHOICES,
        default="medium",
    )
    eval_promote_parser.add_argument(
        "--verification-stage",
        dest="verification_stages",
        action="append",
        default=None,
        choices=_EVAL_VERIFICATION_STAGE_CHOICES,
        help="verification stage for the case; repeat as needed",
    )
    eval_promote_parser.add_argument(
        "--baseline-refresh-policy",
        choices=_EVAL_BASELINE_REFRESH_POLICY_CHOICES,
        default="review_required",
    )
    eval_promote_parser.add_argument(
        "--report-output",
        default=None,
        help="optional path for the generated baseline review artifact",
    )
    eval_promote_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured promotion report as JSON",
    )
    _add_runtime_location_arguments(eval_promote_parser)

    eval_refresh_parser = eval_case_subparsers.add_parser(
        "refresh",
        help="refresh one existing eval baseline from a new source session",
        description=(
            "Export a new replay bundle into an existing eval case and emit a "
            "review artifact that summarizes what changed and why."
        ),
    )
    eval_refresh_parser.add_argument("case_id")
    eval_refresh_parser.add_argument("session_id", type=_parse_uuid)
    eval_refresh_parser.add_argument(
        "--reason",
        required=True,
        help="required refresh rationale stored in the case history",
    )
    eval_refresh_parser.add_argument(
        "--acknowledge-policy",
        action="store_true",
        help="required when refreshing blocking or release-candidate cases",
    )
    eval_refresh_parser.add_argument("--title", default=None)
    eval_refresh_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=None,
        help="replace case tags with the provided values; repeat as needed",
    )
    eval_refresh_parser.add_argument("--notes", default=None)
    eval_refresh_parser.add_argument(
        "--expectation-mode",
        choices=_EVAL_EXPECTATION_MODE_CHOICES,
        default=None,
    )
    eval_refresh_parser.add_argument(
        "--invariant",
        dest="invariants",
        action="append",
        default=None,
        choices=_EVAL_INVARIANT_CHOICES,
        help="replace selected invariants with the provided values",
    )
    eval_refresh_parser.add_argument("--owner", default=None)
    eval_refresh_parser.add_argument(
        "--capability",
        dest="capabilities",
        action="append",
        default=None,
        help="replace protected capabilities with the provided values",
    )
    eval_refresh_parser.add_argument(
        "--severity",
        choices=_EVAL_SEVERITY_CHOICES,
        default=None,
    )
    eval_refresh_parser.add_argument(
        "--verification-stage",
        dest="verification_stages",
        action="append",
        default=None,
        choices=_EVAL_VERIFICATION_STAGE_CHOICES,
        help="replace verification stages with the provided values",
    )
    eval_refresh_parser.add_argument(
        "--baseline-refresh-policy",
        choices=_EVAL_BASELINE_REFRESH_POLICY_CHOICES,
        default=None,
    )
    eval_refresh_parser.add_argument(
        "--report-output",
        default=None,
        help="optional path for the generated baseline review artifact",
    )
    eval_refresh_parser.add_argument(
        "--json",
        action="store_true",
        help="print the structured refresh report as JSON",
    )
    _add_runtime_location_arguments(eval_refresh_parser)
