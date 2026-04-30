"""CLI commands for durable tool-attempt inspection."""

import argparse
import asyncio
import json

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.tool_attempt_recovery import ToolAttemptRecoveryError
from glassbox.runtime.tool_attempt_recovery import abandon_tool_attempt
from glassbox.runtime.tool_attempt_recovery import inspect_tool_attempt
from glassbox.runtime.tool_attempt_recovery import read_tool_attempt_output
from glassbox.runtime.tool_attempt_recovery import retry_tool_attempt


def _session_tool_attempts_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    status = ToolAttemptStatus(args.status) if args.status is not None else None
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        rows = runtime_context.repositories.sessions.list_tool_attempts(
            args.session_id,
            status=status,
            limit=args.limit,
        )

    if args.json:
        print_json_output([row.model_dump(mode="json") for row in rows])
        return 0

    if not rows:
        print("No tool attempts found")
        return 0

    print(f"Tool attempts: {len(rows)}")
    for row in rows:
        print(
            f"{row.tool_attempt_id}  {row.tool_name}  {row.status.value}  "
            f"turn {row.turn_id}"
        )
        if row.tool_call_id is not None:
            print(f"  Tool call: {row.tool_call_id}")
        if row.message:
            print(f"  Message: {row.message}")
        if row.heartbeat_expires_at is not None:
            print(f"  Heartbeat expires: {row.heartbeat_expires_at.isoformat()}")
        if row.retry_classification is not None:
            print(f"  Retry classification: {row.retry_classification.value}")
        if row.safe_to_retry is not None:
            print(f"  Safe to retry: {str(row.safe_to_retry).lower()}")
        if row.retry_requires_approval is not None:
            print(
                f"  Retry requires approval: {str(row.retry_requires_approval).lower()}"
            )
        if row.retry_reason:
            print(f"  Retry reason: {row.retry_reason}")
        if row.retry_policy_reason:
            print(f"  Retry policy reason: {row.retry_policy_reason}")
    return 0


def _session_tool_attempt_inspect_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        inspection = inspect_tool_attempt(
            runtime_context.repositories.sessions,
            args.session_id,
            args.tool_attempt_id,
        )

    if args.json:
        print_json_output(inspection.model_dump(mode="json"))
        return 0

    row = inspection.attempt
    print(f"Tool attempt: {row.tool_attempt_id}")
    print(f"Status: {row.status.value}")
    print(f"Tool: {row.tool_name}")
    print(f"Turn: {row.turn_id}")
    if row.tool_call_id is not None:
        print(f"Tool call: {row.tool_call_id}")
    if row.message:
        print(f"Message: {row.message}")
    if row.retry_classification is not None:
        print(f"Retry classification: {row.retry_classification.value}")
    if row.retry_reason:
        print(f"Retry reason: {row.retry_reason}")
    if row.retry_requires_approval is not None:
        print(f"Retry requires approval: {str(row.retry_requires_approval).lower()}")
    if inspection.source_arguments is not None:
        print(
            "Source arguments: "
            f"{json.dumps(inspection.source_arguments, sort_keys=True)}"
        )
    if inspection.output_artifact is not None:
        artifact = inspection.output_artifact
        print(f"Output artifact: {artifact.artifact_id} ({artifact.artifact_kind})")
        if artifact.path:
            print(f"Output path: {artifact.path}")
    print(f"Correlated events: {inspection.correlated_event_count}")
    print(f"Recovery actions: {', '.join(inspection.recovery_actions)}")
    return 0


def _session_tool_attempt_retry_command(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "Retrying a tool attempt replays retained tool-call arguments and "
            "records new recovery evidence. Re-run with --yes to confirm."
        )
        return 2

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="retry a tool attempt locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        try:
            result = asyncio.run(
                retry_tool_attempt(
                    runtime_context.repositories.sessions,
                    runtime_context.repositories.artifacts,
                    args.session_id,
                    args.tool_attempt_id,
                    confirmed=args.yes,
                    requested_by=args.requested_by,
                    reason=args.reason,
                )
            )
        except ToolAttemptRecoveryError as exc:
            raise ValueError(str(exc)) from exc

    if args.json:
        print_json_output(result.model_dump(mode="json"))
        return 0

    print(result.message)
    if result.retry_attempt is not None:
        print(f"Retry attempt: {result.retry_attempt.tool_attempt_id}")
        print(f"Retry status: {result.retry_attempt.status.value}")
        if result.retry_attempt.message:
            print(f"Retry message: {result.retry_attempt.message}")
    return 0


def _session_tool_attempt_abandon_command(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "Abandoning a tool attempt records terminal recovery evidence while "
            "keeping retained artifacts for audit. Re-run with --yes to confirm."
        )
        return 2

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="abandon a tool attempt locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        try:
            result = abandon_tool_attempt(
                runtime_context.repositories.sessions,
                args.session_id,
                args.tool_attempt_id,
                reason=args.reason,
                abandoned_by=args.abandoned_by,
            )
        except ToolAttemptRecoveryError as exc:
            raise ValueError(str(exc)) from exc

    if args.json:
        print_json_output(result.model_dump(mode="json"))
        return 0

    print(result.message)
    print(f"Status: {result.original_attempt.status.value}")
    return 0


def _session_tool_attempt_output_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        try:
            artifact, content = read_tool_attempt_output(
                runtime_context.repositories.sessions,
                runtime_context.repositories.artifacts,
                args.session_id,
                args.tool_attempt_id,
            )
        except ToolAttemptRecoveryError as exc:
            raise ValueError(str(exc)) from exc

    if args.json:
        print_json_output(
            {
                "artifact": artifact.model_dump(mode="json"),
                "content": _tail_content(content, args.tail),
            }
        )
        return 0

    if artifact.path:
        print(f"Output artifact: {artifact.path}")
    print(_tail_content(content, args.tail), end="" if content.endswith("\n") else "\n")
    return 0


def _tail_content(content: str, tail: int | None) -> str:
    if tail is None:
        return content
    if tail < 1:
        raise ValueError("--tail must be greater than zero")
    lines = content.splitlines(keepends=True)
    return "".join(lines[-tail:])


__all__ = [
    "_session_tool_attempt_abandon_command",
    "_session_tool_attempt_inspect_command",
    "_session_tool_attempt_output_command",
    "_session_tool_attempt_retry_command",
    "_session_tool_attempts_command",
]
