"""Projected record, guidance, and custody decision handoff CLI handlers."""

import argparse
from typing import Any
from typing import cast

from glassbox.cli.handoff_command_formatters import print_decision_result
from glassbox.cli.handoff_command_formatters import print_handoff_guidance
from glassbox.cli.handoff_command_formatters import print_handoff_record
from glassbox.cli.handoff_command_formatters import print_handoff_records
from glassbox.cli.handoff_command_formatters import record_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import SessionId
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.runtime.handoff_guidance import load_handoff_guidance


def handoff_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        records = repository.list_handoffs(
            session_id=args.session_id,
            include_archived=args.include_archived,
            limit=args.limit,
        )
    if args.json:
        print_json_output([record_payload(record) for record in records])
    else:
        print_handoff_records(records)
    return 0


def handoff_show_command(args: argparse.Namespace) -> int:
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
        print_json_output(record_payload(record))
    else:
        print_handoff_record(record)
    return 0


def handoff_guidance_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        guidance = load_handoff_guidance(
            repository,
            args.session_id,
            args.package_id,
        )
    if args.json:
        print_json_output(guidance.model_dump(mode="json"))
    else:
        print_handoff_guidance(guidance)
    return 0


def handoff_accept_command(args: argparse.Namespace) -> int:
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
        record = require_handoff_for_actions(
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
    return print_decision_result(result, json_output=args.json)


def handoff_reject_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="record a handoff custody decision locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        record = require_handoff_for_actions(
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
    return print_decision_result(result, json_output=args.json)


def handoff_archive_command(args: argparse.Namespace) -> int:
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
    return print_decision_result(result, json_output=args.json)


def require_handoff_for_actions(
    repository: HandoffDecisionRepository,
    session_id: SessionId,
    package_id: str,
) -> HandoffProjectionRecord:
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {session_id}: {package_id}"
        )
    return record


__all__ = [
    "handoff_accept_command",
    "handoff_archive_command",
    "handoff_guidance_command",
    "handoff_list_command",
    "handoff_reject_command",
    "handoff_show_command",
    "require_handoff_for_actions",
]
