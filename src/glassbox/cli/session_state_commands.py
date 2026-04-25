"""CLI command handlers for session inspection and projection state commands."""

import argparse
from collections.abc import Sequence

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_optional_explicit_path
from glassbox.cli.path_helpers import resolve_optional_output_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.status_formatters import _print_session_status
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import SessionRecord
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.session_export import export_session_package
from glassbox.runtime.session_import import import_session_package
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSummaryView


def _session_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    status = None if args.status is None else SessionStatus(args.status)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = SessionQueryService(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        )
        summaries = query_service.list_session_summaries(
            status=status,
            limit=args.limit,
        )

    if args.json:
        print_json_output([summary.model_dump(mode="json") for summary in summaries])
    else:
        _print_session_summaries(summaries)
    return 0


def _status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = SessionQueryService(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        )
        _print_session_status(query_service.get_session_status_view(args.session_id))

    return 0


def _session_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _answer_command
    from glassbox.cli.interactive_commands import _attach_command
    from glassbox.cli.interactive_commands import _fork_command
    from glassbox.cli.interactive_commands import _message_command
    from glassbox.cli.interactive_commands import _resolve_approval_command
    from glassbox.cli.interactive_commands import _resume_command

    if args.session_command == "list":
        return _session_list_command(args)
    if args.session_command == "attach":
        return _attach_command(args)
    if args.session_command == "message":
        return _message_command(args)
    if args.session_command == "answer":
        return _answer_command(args)
    if args.session_command == "approve":
        return _resolve_approval_command(args, ApprovalDecision.APPROVED)
    if args.session_command == "deny":
        return _resolve_approval_command(args, ApprovalDecision.DENIED)
    if args.session_command == "resume":
        return _resume_command(args)
    if args.session_command == "fork":
        return _fork_command(args)
    if args.session_command == "status":
        return _status_command(args)
    if args.session_command == "export":
        return _session_export_command(args)
    if args.session_command == "import":
        return _session_import_command(args)
    raise ValueError("specify a session subcommand")


def _print_session_summaries(summaries: list[SessionSummaryView]) -> None:
    if not summaries:
        print("No sessions found")
        return

    print(f"Sessions: {len(summaries)}")
    for summary in summaries:
        print(
            f"{summary.session_id}  {summary.status}  "
            f"updated {summary.updated_at.isoformat()}"
        )
        print(f"  Next: {summary.next_action_summary}")
        if summary.latest_message_summary:
            print(f"  Latest: {summary.latest_message_summary}")
        if summary.branch_label is not None:
            print(f"  Branch: {summary.branch_label}")


def _session_export_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    output_path = resolve_optional_output_path(
        cwd,
        args.output,
        default_name=f"glassbox-session-{args.session_id}.json",
    )

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        exported_path = export_session_package(
            args.session_id,
            output_path,
            session_repository=runtime_context.repositories.sessions,
            artifact_repository=runtime_context.repositories.artifacts,
            workspace_root=cwd,
            exported_by=args.exported_by,
            expected_custodian=args.expected_custodian,
            note=args.note,
        )

    if args.json:
        print_json_output(
            {
                "session_id": str(args.session_id),
                "path": str(exported_path),
            }
        )
    else:
        print(
            f"Exported session handoff package for {args.session_id}: {exported_path}"
        )
    return 0


def _session_import_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="import a session handoff package locally",
    )
    package_path = resolve_optional_explicit_path(cwd, args.package)
    assert package_path is not None

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = import_session_package(
            package_path,
            session_repository=runtime_context.repositories.sessions,
            workspace_root=cwd,
            mode=args.mode,
        )

    if args.json:
        print_json_output(result.model_dump(mode="json"))
    else:
        print(
            "Imported session handoff package "
            f"{result.source_session_id} as {result.imported_session_id} "
            f"({result.import_mode}, {result.imported_status})"
        )
        print("Resumable: no")
    return 0


def _projection_command(args: argparse.Namespace) -> int:
    if args.projection_command == "check":
        args.check = True
        return _projection_rebuild_command(args)
    if args.projection_command == "rebuild":
        args.check = False
        return _projection_rebuild_command(args)
    raise ValueError("specify a projection subcommand")


def _projection_rebuild_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="rebuild projections locally",
    )

    if args.all == (args.session_id is not None):
        raise ValueError("specify exactly one of session_id or --all")

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        sessions = _rebuild_target_sessions(repository, args)

        if not sessions:
            print("No sessions found to rebuild")
            return 0

        if args.check:
            _print_projection_health_report(repository, sessions)
            return 0

        if args.all:
            _rebuild_all_session_projections(repository, sessions)
            return 0

        _rebuild_session_projections(repository, sessions[0])
        return 0


def _rebuild_target_sessions(
    repository, args: argparse.Namespace
) -> list[SessionRecord]:
    if args.all:
        return repository.list_sessions()

    session_id = args.session_id
    assert session_id is not None
    session = repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    return [session]


def _print_projection_health_report(
    repository,
    sessions: Sequence[SessionRecord],
) -> None:
    degraded_count = 0
    for session in sessions:
        health = repository.inspect_session_projection_health(session.session_id)
        if health.degraded:
            degraded_count += 1
        print(
            f"Session {session.session_id}: {_format_projection_health_summary(health)}"
        )
    ok_count = len(sessions) - degraded_count
    print(f"Projection health: {ok_count} ok, {degraded_count} degraded")


def _rebuild_session_projections(repository, session: SessionRecord) -> str:
    before = repository.inspect_session_projection_health(session.session_id)
    repository.rebuild_session_projections(session.session_id)
    after = repository.inspect_session_projection_health(session.session_id)
    print(f"Rebuilt projections for session {session.session_id}")
    print(f"  Before: {_format_projection_health_summary(before)}")
    print(f"  After: {_format_projection_health_summary(after)}")
    return after.state


def _rebuild_all_session_projections(
    repository,
    sessions: Sequence[SessionRecord],
) -> None:
    degraded_after_rebuild = 0
    for session in sessions:
        if _rebuild_session_projections(repository, session) != "ok":
            degraded_after_rebuild += 1
    print(
        f"Rebuilt projections for {len(sessions)} session(s); "
        f"{degraded_after_rebuild} degraded"
    )


def _format_projection_health_summary(health: ProjectionHealth) -> str:
    projected_sequence = (
        "none"
        if health.projected_last_sequence is None
        else str(health.projected_last_sequence)
    )
    summary = (
        f"{health.state}; canonical sequence {health.canonical_last_sequence}; "
        f"projected sequence {projected_sequence}; lag {health.lag}"
    )
    if health.detail is not None:
        summary += f" ({health.detail})"
    return summary
