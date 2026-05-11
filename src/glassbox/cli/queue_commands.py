"""CLI command handlers for the unified operator queue."""

import argparse
from collections.abc import Sequence

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.operator_queue import operator_queue_counts
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.workspace_runtime_summary import build_workspace_runtime_summary

OPERATOR_QUEUE_SCHEMA_VERSION = "operator-queue.v1"


def _queue_command(args: argparse.Namespace) -> int:
    queue_command = getattr(args, "queue_command", None)
    if queue_command == "list":
        return _queue_list_command(args)
    raise ValueError(f"unsupported queue subcommand: {queue_command}")


def _queue_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = SessionQueryService(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        )
        aggregate = query_service.get_session_aggregate(
            runtime=build_workspace_runtime_summary(
                cwd,
                inspect_runtime_owner(runtime_context.infrastructure.artifacts_root),
                runtime_context.repositories.sessions,
            )
        )

    items = _filter_queue_items(
        aggregate.operator_queue,
        view=args.view,
        family=args.family,
        state=args.state,
        priority=args.priority,
    )
    if args.limit is not None:
        items = items[: args.limit]

    payload = {
        "schema_version": OPERATOR_QUEUE_SCHEMA_VERSION,
        "view": args.view,
        "filters": {
            "family": args.family,
            "state": args.state,
            "priority": args.priority,
            "limit": args.limit,
        },
        "counts": aggregate.operator_queue_counts.model_dump(mode="json"),
        "filtered_counts": operator_queue_counts(items).model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in items],
    }
    if args.json:
        print_json_output(payload)
    else:
        _print_queue_items(items)
    return 0


def _filter_queue_items(
    items: Sequence[OperatorQueueItem],
    *,
    view: str,
    family: str | None,
    state: str | None,
    priority: str | None,
) -> list[OperatorQueueItem]:
    filtered = [_view_matches(item, view) for item in items]
    result = [item for item, matches in zip(items, filtered, strict=True) if matches]
    if family is not None:
        result = [item for item in result if item.family.value == family]
    if state is not None:
        result = [item for item in result if item.state.value == state]
    if priority is not None:
        result = [item for item in result if item.priority.value == priority]
    return result


def _view_matches(item: OperatorQueueItem, view: str) -> bool:
    if view == "all":
        return True
    if view == "action-needed":
        return item.action_needed
    if view == "verification":
        return item.family == OperatorQueueFamily.VERIFICATION_BLOCKING
    if view == "review":
        return item.family == OperatorQueueFamily.REVIEW_BLOCKING
    if view == "maintenance":
        return item.family == OperatorQueueFamily.MAINTENANCE
    if view == "advisory":
        return item.family == OperatorQueueFamily.ADVISORY
    if view == "historical":
        return (
            item.state == OperatorQueueState.HISTORICAL
            or item.priority.value == "historical"
        )
    raise ValueError(f"unsupported queue view: {view}")


def _print_queue_items(items: Sequence[OperatorQueueItem]) -> None:
    if not items:
        print("Queue items: 0")
        return

    print(f"Queue items: {len(items)}")
    for item in items:
        target = item.target.label or item.target.target_id or item.target.kind.value
        print(
            f"{item.item_id}  {item.family.value}  {item.state.value}  "
            f"{item.priority.value}/{item.severity.value}"
        )
        print(f"  Target: {target}")
        print(f"  Next: {item.safe_next_action.title}")
        print(f"  Evidence: {item.evidence_summary.summary}")


__all__ = [
    "OPERATOR_QUEUE_SCHEMA_VERSION",
    "_queue_command",
]
