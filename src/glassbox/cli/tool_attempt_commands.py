"""CLI commands for durable tool-attempt inspection."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.bootstrap import open_runtime_context


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


__all__ = ["_session_tool_attempts_command"]
