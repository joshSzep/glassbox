"""Session workflow argument parser construction."""

import argparse

from glassbox.cli.parser_common import _SESSION_STATUS_CHOICES
from glassbox.cli.parser_common import _add_autonomy_selection_arguments
from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _add_session_start_default_arguments
from glassbox.cli.parser_common import _parse_port
from glassbox.cli.parser_common import _parse_uuid
from glassbox.cli.parser_session_launch import add_interactive_launch_arguments


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
    add_interactive_launch_arguments(session_chat_parser)
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
    add_interactive_launch_arguments(attach_parser)

    message_parser = session_subparsers.add_parser(
        "message",
        help="submit a new prompt to an existing session",
        description="Submit a new user message into an existing session.",
    )
    message_parser.add_argument("session_id", type=_parse_uuid)
    message_parser.add_argument("prompt", help="user prompt to submit")
    _add_runtime_location_arguments(message_parser)
    _add_autonomy_selection_arguments(message_parser)

    cancel_parser = session_subparsers.add_parser(
        "cancel",
        help="request cancellation of an active turn",
        description=(
            "Request cancellation of the active live turn in an existing session."
        ),
    )
    cancel_parser.add_argument("session_id", type=_parse_uuid)
    cancel_parser.add_argument(
        "--turn",
        dest="turn_id",
        type=_parse_uuid,
        default=None,
        help="optional active turn identifier to cancel",
    )
    cancel_parser.add_argument(
        "--reason",
        default=None,
        help="optional cancellation reason recorded with the request",
    )
    _add_runtime_location_arguments(cancel_parser)

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
    _add_autonomy_selection_arguments(resume_parser)

    compact_parser = session_subparsers.add_parser(
        "compact",
        help="create a context compaction",
        description=(
            "Create a deterministic artifact-backed context compaction for a "
            "persisted session."
        ),
    )
    compact_parser.add_argument("session_id", type=_parse_uuid)
    compact_parser.add_argument(
        "--scope",
        choices=(
            "transcript",
            "task",
            "runtime_context",
            "verification",
            "tool_output",
        ),
        default="transcript",
        help="compaction scope to record",
    )
    compact_parser.add_argument("--task-id", type=_parse_uuid, default=None)
    compact_parser.add_argument("--source-start-sequence", type=int, default=None)
    compact_parser.add_argument("--source-end-sequence", type=int, default=None)
    compact_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(compact_parser)

    compactions_parser = session_subparsers.add_parser(
        "compactions",
        help="list context compactions",
        description="List context compactions recorded for a persisted session.",
    )
    compactions_parser.add_argument("session_id", type=_parse_uuid)
    compactions_parser.add_argument("--task-id", type=_parse_uuid, default=None)
    compactions_parser.add_argument("--limit", type=int, default=20)
    compactions_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(compactions_parser)

    compaction_refresh_parser = session_subparsers.add_parser(
        "compaction-refresh",
        help="refresh a stale context compaction",
        description=(
            "Create a replacement context compaction covering current source "
            "events and mark the original as stale."
        ),
    )
    compaction_refresh_parser.add_argument("session_id", type=_parse_uuid)
    compaction_refresh_parser.add_argument("compaction_id", type=_parse_uuid)
    compaction_refresh_parser.add_argument("--reason", default=None)
    compaction_refresh_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the mutating refresh operation",
    )
    compaction_refresh_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(compaction_refresh_parser)

    compaction_invalidate_parser = session_subparsers.add_parser(
        "compaction-invalidate",
        help="invalidate a context compaction",
        description=(
            "Record that a context compaction artifact remains audit evidence "
            "but must not feed active prompt context."
        ),
    )
    compaction_invalidate_parser.add_argument("session_id", type=_parse_uuid)
    compaction_invalidate_parser.add_argument("compaction_id", type=_parse_uuid)
    compaction_invalidate_parser.add_argument(
        "--reason",
        required=True,
        help="operator-visible reason for invalidating the compaction",
    )
    compaction_invalidate_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the mutating invalidation operation",
    )
    compaction_invalidate_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(compaction_invalidate_parser)

    tool_attempts_parser = session_subparsers.add_parser(
        "tool-attempts",
        help="list durable tool attempts",
        description="List durable tool-attempt heartbeats for a persisted session.",
    )
    tool_attempts_parser.add_argument("session_id", type=_parse_uuid)
    tool_attempts_parser.add_argument(
        "--status",
        choices=(
            "started",
            "running",
            "waiting",
            "succeeded",
            "failed",
            "cancelled",
            "stale",
            "retried",
            "abandoned",
        ),
        default=None,
    )
    tool_attempts_parser.add_argument("--limit", type=int, default=20)
    tool_attempts_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(tool_attempts_parser)

    tool_attempt_parser = session_subparsers.add_parser(
        "tool-attempt",
        help="recover a durable tool attempt",
        description=(
            "Inspect, retry, abandon, or read retained output for one durable "
            "tool attempt."
        ),
    )
    tool_attempt_subparsers = tool_attempt_parser.add_subparsers(
        dest="tool_attempt_command",
        required=True,
    )

    tool_attempt_inspect_parser = tool_attempt_subparsers.add_parser(
        "inspect",
        help="inspect one durable tool attempt",
    )
    tool_attempt_inspect_parser.add_argument("session_id", type=_parse_uuid)
    tool_attempt_inspect_parser.add_argument("tool_attempt_id", type=_parse_uuid)
    tool_attempt_inspect_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(tool_attempt_inspect_parser)

    tool_attempt_retry_parser = tool_attempt_subparsers.add_parser(
        "retry",
        help="retry one stale or failed tool attempt",
    )
    tool_attempt_retry_parser.add_argument("session_id", type=_parse_uuid)
    tool_attempt_retry_parser.add_argument("tool_attempt_id", type=_parse_uuid)
    tool_attempt_retry_parser.add_argument("--reason", default=None)
    tool_attempt_retry_parser.add_argument("--requested-by", default="operator")
    tool_attempt_retry_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the mutating retry operation",
    )
    tool_attempt_retry_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(tool_attempt_retry_parser)

    tool_attempt_abandon_parser = tool_attempt_subparsers.add_parser(
        "abandon",
        help="abandon one stale or failed tool attempt",
    )
    tool_attempt_abandon_parser.add_argument("session_id", type=_parse_uuid)
    tool_attempt_abandon_parser.add_argument("tool_attempt_id", type=_parse_uuid)
    tool_attempt_abandon_parser.add_argument(
        "--reason",
        required=True,
        help="operator-visible reason for abandoning recovery",
    )
    tool_attempt_abandon_parser.add_argument("--abandoned-by", default="operator")
    tool_attempt_abandon_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the mutating abandon operation",
    )
    tool_attempt_abandon_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(tool_attempt_abandon_parser)

    tool_attempt_output_parser = tool_attempt_subparsers.add_parser(
        "output",
        help="print retained output for one tool attempt",
    )
    tool_attempt_output_parser.add_argument("session_id", type=_parse_uuid)
    tool_attempt_output_parser.add_argument("tool_attempt_id", type=_parse_uuid)
    tool_attempt_output_parser.add_argument("--tail", type=int, default=None)
    tool_attempt_output_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(tool_attempt_output_parser)

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


def _add_autonomy_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    autonomy_parser = subparsers.add_parser(
        "autonomy",
        help="inspect autonomy modes and budget presets",
        description="Inspect effective bounded-autonomy profiles for a workspace.",
    )
    autonomy_subparsers = autonomy_parser.add_subparsers(
        dest="autonomy_command",
        required=True,
    )

    profile_parser = autonomy_subparsers.add_parser(
        "profile",
        help="inspect autonomy profile defaults",
        description="List or show autonomy modes and resolved budget presets.",
    )
    profile_subparsers = profile_parser.add_subparsers(
        dest="autonomy_profile_command",
        required=True,
    )

    list_parser = profile_subparsers.add_parser(
        "list",
        help="list built-in autonomy modes and workspace presets",
    )
    _add_runtime_location_arguments(list_parser)
    list_parser.add_argument("--json", action="store_true")

    show_parser = profile_subparsers.add_parser(
        "show",
        help="show one effective autonomy profile",
    )
    show_parser.add_argument(
        "preset",
        nargs="?",
        help="built-in mode or workspace budget preset to show",
    )
    _add_runtime_location_arguments(show_parser)
    show_parser.add_argument("--json", action="store_true")
