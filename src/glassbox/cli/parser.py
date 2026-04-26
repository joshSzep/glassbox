"""Argument parser construction for the Glassbox CLI."""

import argparse
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CommandTreeColorTheme:
    prog: str
    action: str
    reset: str


_APPROVAL_MODE_CHOICES = ("confirm", "review", "on-request", "never")
_SESSION_STATUS_CHOICES = (
    "idle",
    "running",
    "awaiting_approval",
    "awaiting_user_input",
    "completed",
    "failed",
    "cancelled",
)
_EVAL_EXPECTATION_MODE_CHOICES = ("exact_match", "selected_invariants")
_EVAL_SEVERITY_CHOICES = ("critical", "high", "medium", "low")
_EVAL_VERIFICATION_STAGE_CHOICES = (
    "commit-time",
    "push-time",
    "release-candidate",
    "advisory",
)
_EVAL_PROFILE_TRACK_CHOICES = ("deterministic", "live-provider-canary")
_EVAL_BASELINE_REFRESH_POLICY_CHOICES = (
    "review_required",
    "intentional_only",
    "advisory",
)
_EVAL_INVARIANT_CHOICES = (
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level Glassbox CLI parser."""

    parser = argparse.ArgumentParser(
        prog="glassbox",
        description="Run the Glassbox local-first CLI agent and dashboard runtime.",
    )
    subparsers = parser.add_subparsers(dest="command")

    _add_command_parsers(subparsers)
    _add_session_workflow_parsers(subparsers)
    _add_replay_parsers(subparsers)
    _add_eval_parsers(subparsers)
    _add_artifact_parsers(subparsers)
    _add_backup_parsers(subparsers)
    _add_operations_parsers(subparsers)

    return parser


def format_command_tree(
    parser: argparse.ArgumentParser,
    *,
    color_theme: CommandTreeColorTheme | None = None,
) -> str:
    lines = [
        _format_command_tree_node(
            parser.prog,
            parser.description,
            color_theme.prog if color_theme else None,
            color_theme,
        )
    ]
    _append_command_tree_lines(parser, lines, prefix="", color_theme=color_theme)
    return "\n".join(lines)


def _add_command_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    command_parser = subparsers.add_parser(
        "command",
        help="inspect the Glassbox command surface",
        description="Inspect the available Glassbox command surface.",
    )
    command_subparsers = command_parser.add_subparsers(
        dest="command_command",
        required=True,
    )

    command_subparsers.add_parser(
        "tree",
        help="print the command tree",
        description="Print the Glassbox command tree.",
    )


def _append_command_tree_lines(
    parser: argparse.ArgumentParser,
    lines: list[str],
    *,
    prefix: str,
    color_theme: CommandTreeColorTheme | None,
) -> None:
    entries = _visible_subparser_entries(parser)
    max_name_length = max((len(name) for name, _, _ in entries), default=0)
    for index, (name, child_parser, help_text) in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "`-- " if is_last else "|-- "
        name_padding = " " * (max_name_length - len(name))
        name_color = color_theme.action if color_theme else None
        node = _format_command_tree_node(
            name,
            help_text,
            name_color,
            color_theme,
            name_padding=name_padding,
        )
        lines.append(f"{prefix}{branch}{node}")
        child_prefix = f"{prefix}{'    ' if is_last else '|   '}"
        _append_command_tree_lines(
            child_parser,
            lines,
            prefix=child_prefix,
            color_theme=color_theme,
        )


def _format_command_tree_node(
    name: str,
    help_text: str | None,
    color: str | None,
    color_theme: CommandTreeColorTheme | None,
    *,
    name_padding: str = "",
) -> str:
    formatted_name = f"{_colorize(name, color, color_theme)}{name_padding}"
    if not help_text:
        return formatted_name.rstrip()
    return f"{formatted_name}  {help_text}"


def _colorize(
    text: str,
    color: str | None,
    color_theme: CommandTreeColorTheme | None,
) -> str:
    if color is None or color_theme is None:
        return text
    return f"{color}{text}{color_theme.reset}"


def _visible_subparser_entries(
    parser: argparse.ArgumentParser,
) -> list[tuple[str, argparse.ArgumentParser, str | None]]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            visible_choices = [
                choice
                for choice in action._choices_actions
                if choice.help is not argparse.SUPPRESS
            ]
            return [
                (choice.dest, action.choices[choice.dest], choice.help)
                for choice in visible_choices
                if choice.dest in action.choices
            ]
    return []


def _add_session_workflow_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    session_parser = subparsers.add_parser(
        "session",
        help="work with sessions",
        description=(
            "Start, inspect, mutate, branch, resume, and hand off persisted sessions."
        ),
    )
    session_subparsers = session_parser.add_subparsers(
        dest="session_command",
        required=True,
    )

    session_run_parser = session_subparsers.add_parser(
        "run",
        help="start a new session",
        description="Start a new session and optionally submit an initial prompt.",
    )
    session_run_parser.add_argument(
        "prompt",
        nargs="?",
        help="optional initial user prompt",
    )
    _add_runtime_location_arguments(session_run_parser)
    _add_session_start_default_arguments(session_run_parser)

    session_chat_parser = session_subparsers.add_parser(
        "chat",
        help="start a new interactive session",
        description=(
            "Start a new session and keep the terminal open for follow-up "
            "prompts. Type /exit to leave the interactive session."
        ),
    )
    session_chat_parser.add_argument(
        "prompt",
        nargs="?",
        help="optional initial user prompt",
    )
    _add_runtime_location_arguments(session_chat_parser)
    _add_session_start_default_arguments(session_chat_parser)
    session_chat_parser.add_argument(
        "--dashboard-host",
        default=None,
        help="host address for the co-hosted dashboard server",
    )
    session_chat_parser.add_argument(
        "--dashboard-port",
        type=_parse_port,
        default=None,
        help="port for the co-hosted dashboard server",
    )
    session_chat_parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="disable the co-hosted dashboard during interactive chat",
    )

    session_list_parser = session_subparsers.add_parser(
        "list",
        help="list persisted sessions",
        description="List persisted sessions by recent activity.",
    )
    session_list_parser.add_argument(
        "--status",
        choices=_SESSION_STATUS_CHOICES,
        default=None,
        help="only list sessions with this projected status",
    )
    session_list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="maximum number of recent sessions to list",
    )
    session_list_parser.add_argument(
        "--json",
        action="store_true",
        help="print session summaries as JSON",
    )
    _add_runtime_location_arguments(session_list_parser)

    attach_parser = session_subparsers.add_parser(
        "attach",
        help="attach to an existing interactive session",
        description=(
            "Open an interactive terminal workflow for an existing session. "
            "Type /exit to leave the attached session."
        ),
    )
    attach_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(attach_parser)

    message_parser = session_subparsers.add_parser(
        "message",
        help="submit a new prompt to an existing session",
        description="Submit a new user message into an existing session.",
    )
    message_parser.add_argument("session_id", type=_parse_uuid)
    message_parser.add_argument("prompt", help="user prompt to submit")
    _add_runtime_location_arguments(message_parser)

    answer_parser = session_subparsers.add_parser(
        "answer",
        help="answer a pending ask_user question",
        description=(
            "Submit an answer to a pending ask_user question in an existing "
            "session. Use the question_id from the earlier 'Question asked' "
            "CLI output line."
        ),
    )
    answer_parser.add_argument(
        "session_id",
        type=_parse_uuid,
        help="session identifier that is awaiting user input",
    )
    answer_parser.add_argument(
        "question_id",
        type=_parse_uuid,
        help="question identifier shown when the session asked for input",
    )
    answer_parser.add_argument("answer", help="answer text to provide")
    _add_runtime_location_arguments(answer_parser)

    approve_parser = session_subparsers.add_parser(
        "approve",
        help="approve a pending action",
        description="Approve a pending tool action and resume the suspended turn.",
    )
    approve_parser.add_argument("session_id", type=_parse_uuid)
    approve_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(approve_parser)

    deny_parser = session_subparsers.add_parser(
        "deny",
        help="deny a pending action",
        description=(
            "Deny a pending tool action and resume the suspended turn "
            "without running it."
        ),
    )
    deny_parser.add_argument("session_id", type=_parse_uuid)
    deny_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(deny_parser)

    resume_parser = session_subparsers.add_parser(
        "resume",
        help="resume an existing session",
        description="Replay the resume event for an existing session.",
    )
    resume_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(resume_parser)

    fork_parser = session_subparsers.add_parser(
        "fork",
        help="create a child session from a historical turn",
        description=(
            "Create a new child session from the latest completed turn or an "
            "explicitly selected completed turn in an existing session."
        ),
    )
    fork_parser.add_argument("session_id", type=_parse_uuid)
    fork_parser.add_argument(
        "--turn",
        dest="turn_id",
        type=_parse_uuid,
        default=None,
        help="explicit completed turn identifier to fork from",
    )
    fork_parser.add_argument(
        "--branch-label",
        "--label",
        dest="branch_label",
        default=None,
        help="optional operator-visible label for the child branch",
    )
    fork_parser.add_argument(
        "--prompt",
        default=None,
        help="optional immediate prompt to submit to the new child session",
    )
    _add_runtime_location_arguments(fork_parser)

    status_parser = session_subparsers.add_parser(
        "status",
        help="inspect session state",
        description=(
            "Print the current session state, approvals, tool activity, "
            "and recent metrics."
        ),
    )
    status_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(status_parser)

    session_export_parser = session_subparsers.add_parser(
        "export",
        help="export a portable session handoff package",
        description=(
            "Export a persisted session into an inspectable handoff package for "
            "review or debugging without copying the full workspace database."
        ),
    )
    session_export_parser.add_argument("session_id", type=_parse_uuid)
    session_export_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the exported session handoff package",
    )
    session_export_parser.add_argument(
        "--exported-by",
        default=None,
        help="optional acting-operator label to include in the handoff package",
    )
    session_export_parser.add_argument(
        "--expected-custodian",
        default=None,
        help="optional operator label expected to take custody after export",
    )
    session_export_parser.add_argument(
        "--note",
        default=None,
        help="optional handoff note to include in the package",
    )
    session_export_parser.add_argument(
        "--json",
        action="store_true",
        help="print the export command result as JSON",
    )
    _add_runtime_location_arguments(session_export_parser)

    session_import_parser = session_subparsers.add_parser(
        "import",
        help="import a portable session handoff package",
        description=(
            "Import a session export package into local inspectable session "
            "state without silently merging it with existing sessions."
        ),
    )
    session_import_parser.add_argument(
        "package",
        help="path to a package written by session export",
    )
    session_import_parser.add_argument(
        "--json",
        action="store_true",
        help="print the import result as JSON",
    )
    _add_runtime_location_arguments(session_import_parser)


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


def _add_operations_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    observability_parser = subparsers.add_parser(
        "observability",
        help="summarize runtime, projection, and verification health",
        description=(
            "Summarize workspace runtime health, projection lag, event transport "
            "state, and retained verification activity."
        ),
    )
    observability_subparsers = observability_parser.add_subparsers(
        dest="observability_command",
        required=True,
    )

    observability_status_parser = observability_subparsers.add_parser(
        "status",
        help="print a workspace observability summary",
        description="Print a workspace observability summary and next actions.",
    )
    observability_status_parser.add_argument(
        "--json",
        action="store_true",
        help="print the observability report as JSON",
    )
    _add_runtime_location_arguments(observability_status_parser)

    performance_parser = subparsers.add_parser(
        "performance",
        help="inspect larger-session performance expectations",
        description="Inspect repository-owned larger-session performance budgets.",
    )
    performance_subparsers = performance_parser.add_subparsers(
        dest="performance_command",
        required=True,
    )

    performance_subparsers.add_parser(
        "budgets",
        help="print performance budgets and mitigation guidance",
        description=(
            "Print explicit performance budgets and operator mitigation guidance "
            "for larger local workspaces."
        ),
    )

    projection_parser = subparsers.add_parser(
        "projection",
        help="inspect or rebuild derived projections",
        description=(
            "Inspect projection health or rebuild projection tables from "
            "canonical persisted events."
        ),
    )
    projection_subparsers = projection_parser.add_subparsers(
        dest="projection_command",
        required=True,
    )

    projection_check_parser = projection_subparsers.add_parser(
        "check",
        help="inspect projection health without rebuilding",
        description="Inspect projection health without rebuilding derived tables.",
    )
    projection_check_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    projection_check_parser.add_argument(
        "--all",
        action="store_true",
        help="check projections for all sessions in the database",
    )
    _add_runtime_location_arguments(projection_check_parser)

    projection_rebuild_parser = projection_subparsers.add_parser(
        "rebuild",
        help="rebuild derived projections",
        description="Rebuild projection tables from canonical persisted events.",
    )
    projection_rebuild_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    projection_rebuild_parser.add_argument(
        "--all",
        action="store_true",
        help="rebuild projections for all sessions in the database",
    )
    _add_runtime_location_arguments(projection_rebuild_parser)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="work with the browser dashboard",
        description="Start the browser dashboard for the selected workspace.",
    )
    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_command",
        required=True,
    )

    serve_parser = dashboard_subparsers.add_parser(
        "serve",
        help="start the dashboard server",
        description=(
            "Start the web dashboard server for the selected workspace database."
        ),
    )
    _add_runtime_location_arguments(serve_parser)
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the server to",
    )
    serve_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help="port to bind the server to",
    )

    daemon_parser = subparsers.add_parser(
        "daemon",
        help="manage the workspace background runtime owner",
        description=(
            "Start, inspect, or stop the persistent background runtime owner "
            "for the selected workspace."
        ),
    )
    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command",
        metavar="{start,stop,status}",
        required=True,
    )

    daemon_start_parser = daemon_subparsers.add_parser(
        "start",
        help="start the workspace daemon",
        description="Start the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_start_parser)
    daemon_start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the daemon dashboard to",
    )
    daemon_start_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help="port to bind the daemon dashboard to",
    )

    daemon_stop_parser = daemon_subparsers.add_parser(
        "stop",
        help="stop the workspace daemon",
        description="Stop the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_stop_parser)

    daemon_status_parser = daemon_subparsers.add_parser(
        "status",
        help="inspect the workspace daemon",
        description="Inspect the persistent workspace runtime owner.",
    )
    _add_runtime_location_arguments(daemon_status_parser)
    daemon_status_parser.add_argument(
        "--json",
        action="store_true",
        help="print daemon discovery and health details as JSON",
    )

    daemon_run_owner_parser = daemon_subparsers.add_parser(
        "run-owner",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    _hide_subparser_from_help(daemon_subparsers, "run-owner")
    _add_runtime_location_arguments(daemon_run_owner_parser)
    daemon_run_owner_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=argparse.SUPPRESS,
    )
    daemon_run_owner_parser.add_argument(
        "--port",
        type=_parse_port,
        default=8765,
        help=argparse.SUPPRESS,
    )


def _hide_subparser_from_help(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    command_name: str,
) -> None:
    subparsers._choices_actions = [
        action
        for action in subparsers._choices_actions
        if getattr(action, "dest", None) != command_name
    ]


def _add_artifact_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    artifacts_parser = subparsers.add_parser(
        "artifacts",
        help="inspect and clean managed artifact files",
        description=(
            "Inspect managed Glassbox artifact files and remove stale derived "
            "outputs without touching canonical event data."
        ),
    )
    artifacts_subparsers = artifacts_parser.add_subparsers(
        dest="artifacts_command",
        required=True,
    )

    inspect_parser = artifacts_subparsers.add_parser(
        "inspect",
        help="inspect managed artifact state",
        description=(
            "Inspect managed .glassbox artifacts without deleting files. "
            "Event-referenced session artifacts and source-controlled eval "
            "bundles are protected."
        ),
    )
    _add_runtime_location_arguments(inspect_parser)
    inspect_parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="age threshold for managed .glassbox/evals artifacts",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the artifact inspection report as JSON",
    )

    prune_parser = artifacts_subparsers.add_parser(
        "prune",
        help="prune stale managed artifacts",
        description=(
            "Report or remove stale .glassbox artifacts. Event-referenced "
            "session artifacts and source-controlled eval bundles are protected."
        ),
    )
    _add_runtime_location_arguments(prune_parser)
    prune_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report cleanup actions without deleting files",
    )
    prune_parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="age threshold for managed .glassbox/evals artifacts",
    )
    prune_parser.add_argument(
        "--json",
        action="store_true",
        help="print the artifact retention report as JSON",
    )


def _add_backup_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    backup_parser = subparsers.add_parser(
        "backup",
        help="create, inspect, or restore workspace state backups",
        description=(
            "Create, inspect, or restore workspace-local Glassbox backups. "
            "Backups include the canonical SQLite database and event-referenced "
            ".glassbox artifacts, not portable replay or eval baseline bundles."
        ),
    )
    backup_subparsers = backup_parser.add_subparsers(
        dest="backup_command",
        required=True,
    )

    create_parser = backup_subparsers.add_parser(
        "create",
        help="create a workspace backup archive",
        description=(
            "Create an inspectable zip archive containing the canonical SQLite "
            "database and event-referenced workspace artifacts."
        ),
    )
    create_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the backup archive",
    )
    create_parser.add_argument(
        "--json",
        action="store_true",
        help="print the backup report as JSON",
    )
    _add_runtime_location_arguments(create_parser)

    inspect_parser = backup_subparsers.add_parser(
        "inspect",
        help="inspect a workspace backup archive",
        description=(
            "Inspect and validate a Glassbox workspace backup archive without "
            "restoring it."
        ),
    )
    inspect_parser.add_argument("archive", help="backup archive to inspect")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the inspection report as JSON",
    )
    _add_runtime_location_arguments(inspect_parser)

    restore_parser = backup_subparsers.add_parser(
        "restore",
        help="restore a workspace backup archive",
        description=(
            "Restore a Glassbox workspace backup into the selected workspace. "
            "The archive manifest and file hashes are validated before writing."
        ),
    )
    restore_parser.add_argument("archive", help="backup archive to restore")
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing restored files in the target workspace",
    )
    restore_parser.add_argument(
        "--json",
        action="store_true",
        help="print the restore report as JSON",
    )
    _add_runtime_location_arguments(restore_parser)


def _add_runtime_location_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cwd",
        default=".",
        help="workspace directory associated with the session database",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="override the SQLite database path",
    )


def _add_session_start_default_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model-name",
        default=None,
        help=(
            "model identifier recorded in the session metadata; overrides "
            "glassbox.profile.json"
        ),
    )
    parser.add_argument(
        "--approval-mode",
        default=None,
        choices=_APPROVAL_MODE_CHOICES,
        help=("approval mode for risky tool actions; overrides glassbox.profile.json"),
    )


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID: {value}") from exc


def _parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value}") from exc
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError(f"invalid port: {value}")
    return port
