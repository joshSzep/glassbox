"""CLI handlers for local handoff custody decisions."""

import argparse
from typing import Any
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision


def _handoff_command(args: argparse.Namespace) -> int:
    if args.handoff_command == "list":
        return _handoff_list_command(args)
    if args.handoff_command == "show":
        return _handoff_show_command(args)
    if args.handoff_command == "accept":
        return _handoff_accept_command(args)
    if args.handoff_command == "reject":
        return _handoff_reject_command(args)
    if args.handoff_command == "archive":
        return _handoff_archive_command(args)
    raise ValueError("specify a handoff subcommand")


def _handoff_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        records = repository.list_handoffs(
            session_id=args.session_id,
            include_archived=args.include_archived,
            limit=args.limit,
        )
    if args.json:
        print_json_output([_record_payload(record) for record in records])
    else:
        _print_handoff_records(records)
    return 0


def _handoff_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        record = repository.get_handoff(
            args.session_id,
            args.package_id,
        )
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {args.session_id}: {args.package_id}"
        )
    if args.json:
        print_json_output(_record_payload(record))
    else:
        _print_handoff_record(record)
    return 0


def _handoff_accept_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="record a handoff custody decision locally",
    )
    follow_up_intent = (
        HandoffIntent(args.follow_up_intent)
        if args.follow_up_intent is not None
        else None
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        record = _require_handoff_for_actions(
            repository,
            args.session_id,
            args.package_id,
        )
        result = accept_handoff_custody(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            accepted_by=args.accepted_by,
            reason=args.reason,
            follow_up_intent=follow_up_intent,
            safe_next_actions=safe_next_actions_for_decision(record),
        )
    return _print_decision_result(result, json_output=args.json)


def _handoff_reject_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="record a handoff custody decision locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        record = _require_handoff_for_actions(
            repository,
            args.session_id,
            args.package_id,
        )
        result = reject_handoff_custody(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            rejected_by=args.rejected_by,
            reason=args.reason,
            safe_next_actions=safe_next_actions_for_decision(record),
        )
    return _print_decision_result(result, json_output=args.json)


def _handoff_archive_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="archive a handoff record locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        result = archive_handoff(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            archived_by=args.archived_by,
            reason=args.reason,
        )
    return _print_decision_result(result, json_output=args.json)


def _require_handoff_for_actions(repository, session_id, package_id):
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {session_id}: {package_id}"
        )
    return record


def _print_decision_result(
    result: HandoffDecisionResult,
    *,
    json_output: bool,
) -> int:
    if json_output:
        print_json_output(_decision_payload(result))
    else:
        print(f"Recorded {result.event_type} for {result.record.package_id}")
        _print_handoff_record(result.record)
    return 0


def _print_handoff_records(records: list[HandoffProjectionRecord]) -> None:
    if not records:
        print("No handoff records found")
        return
    print(f"Handoff records: {len(records)}")
    for record in records:
        _print_handoff_record(record)


def _print_handoff_record(record: HandoffProjectionRecord) -> None:
    print(
        f"{record.package_id}  {record.custody_state.value}  "
        f"updated {record.updated_at.isoformat()}"
    )
    print(f"  Session: {record.session_id}")
    print(f"  Source: {record.source_kind.value} {record.source_id or ''}".rstrip())
    print(f"  Action state: {custody_action_state(record)}")
    if record.decision_reason:
        print(f"  Reason: {record.decision_reason}")
    if record.follow_up_intent is not None:
        print(f"  Follow-up intent: {record.follow_up_intent.value}")
    if record.safe_next_actions:
        print("  Safe next actions:")
        for action in record.safe_next_actions:
            print(f"    - {action}")


def _decision_payload(result: HandoffDecisionResult) -> dict[str, object]:
    return {
        "event_type": result.event_type,
        "record": _record_payload(result.record),
        "non_claims": result.non_claims,
    }


def _record_payload(record: HandoffProjectionRecord) -> dict[str, object]:
    payload = record.model_dump(mode="json")
    payload["action_state"] = custody_action_state(record)
    return payload


__all__ = ["_handoff_command"]
