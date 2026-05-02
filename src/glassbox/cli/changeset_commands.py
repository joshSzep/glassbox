"""CLI command handlers for changeset inspection."""

import argparse
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import ChangesetRecord
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository


def _changeset_command(args: argparse.Namespace) -> int:
    command = getattr(args, "changeset_command", None)
    if command == "create":
        return _changeset_create_command(args)
    if command == "list":
        return _changeset_list_command(args)
    if command == "show":
        return _changeset_show_command(args)
    if command == "refresh":
        return _changeset_refresh_command(args)
    if command == "archive":
        return _changeset_archive_command(args)
    raise ValueError("specify a changeset subcommand")


def _changeset_create_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetDerivationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        )
        result = _create_changeset_from_args(service, args, cwd)

    payload = {
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "limitations": result.limitations,
        "event_count": len(result.stored_events),
    }
    if args.json:
        print_json_output(payload)
    else:
        print(f"Created changeset {result.changeset_id}")
        print(f"Session: {result.session_id}")
        _print_limitations(result.limitations)
    return 0


def _changeset_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        )
        changesets = service.list_changesets(
            session_id=args.session_id,
            include_archived=args.include_archived,
            limit=args.limit,
        )

    if args.json:
        print_json_output([item.model_dump(mode="json") for item in changesets])
    else:
        _print_changeset_list(changesets)
    return 0


def _changeset_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        )
        detail = service.get_detail(args.changeset_id)

    if args.json:
        print_json_output(detail.model_dump(mode="json"))
    else:
        _print_changeset_detail(detail)
    return 0


def _changeset_refresh_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        )
        event = service.refresh_source_evidence(
            args.changeset_id,
            cwd,
            refreshed_by=args.actor,
        )

    payload = event.model_dump(mode="json")
    if args.json:
        print_json_output(payload)
    else:
        print(f"Refreshed basic source evidence for changeset {args.changeset_id}")
        print(f"Event sequence: {event.sequence}")
    return 0


def _changeset_archive_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        )
        event = service.archive_changeset(
            args.changeset_id,
            reason=args.reason,
            archived_by=args.actor,
            replacement_changeset_id=args.replacement_changeset_id,
        )

    if args.json:
        print_json_output(event.model_dump(mode="json"))
    else:
        print(f"Archived changeset {args.changeset_id}")
        print(f"Reason: {args.reason}")
    return 0


def _create_changeset_from_args(
    service: ChangesetDerivationService,
    args: argparse.Namespace,
    cwd,
) -> ChangesetDerivationResult:
    source_kind = args.source_kind
    if source_kind == "session":
        if args.session_id is None:
            raise ValueError("--session is required for --from session")
        return service.create_from_session(args.session_id, objective=args.objective)
    if source_kind == "task":
        if args.task_id is None:
            raise ValueError("--task is required for --from task")
        return service.create_from_task(args.task_id, objective=args.objective)
    if source_kind == "branch-candidate":
        if args.branch_search_id is None or args.candidate_id is None:
            raise ValueError(
                "--branch-search and --candidate are required for "
                "--from branch-candidate"
            )
        return service.create_from_branch_candidate(
            args.branch_search_id,
            args.candidate_id,
            objective=args.objective,
        )
    if args.session_id is None:
        raise ValueError("--session is required for --from workspace-diff")
    return service.create_from_workspace_diff(
        args.session_id,
        cwd,
        objective=args.objective,
    )


def _print_changeset_list(changesets: list[ChangesetRecord]) -> None:
    if not changesets:
        print("No changesets found")
        return
    print(f"Changesets: {len(changesets)}")
    for changeset in changesets:
        print(
            f"{changeset.changeset_id}  {changeset.status}  "
            f"risk {changeset.risk_level.value}  "
            f"updated {changeset.updated_at.isoformat()}"
        )
        print(f"  Session: {changeset.session_id}")
        print(f"  Objective: {changeset.objective}")
        if changeset.risk_summary is not None:
            print(f"  Risk: {changeset.risk_summary}")
        if changeset.task_id is not None:
            print(f"  Task: {changeset.task_id}")
        if changeset.branch_search_id is not None:
            print(f"  Branch search: {changeset.branch_search_id}")


def _print_changeset_detail(detail: ChangesetDetailView) -> None:
    changeset = detail.changeset
    print(f"Changeset {changeset.changeset_id}")
    print(f"Status: {changeset.status}")
    print(f"Session: {changeset.session_id}")
    print(f"Objective: {changeset.objective}")
    if changeset.summary:
        print(f"Summary: {changeset.summary}")
    print(
        "Risk: "
        f"{changeset.risk_level.value} "
        f"({changeset.unresolved_risk_count} unresolved, "
        f"{changeset.accepted_risk_count} accepted)"
    )
    if changeset.risk_summary is not None:
        print(f"Risk summary: {changeset.risk_summary}")
    print(f"Sources: {len(detail.sources)}")
    for source in detail.sources:
        print(f"  {source.source_kind.value}: {source.reason}")
        if source.limitation:
            print(f"    Limitation: {source.limitation}")
    if detail.inventory is None:
        print("Inventory: none attached yet")
    else:
        print(
            "Inventory: "
            f"{detail.inventory.changed_path_count} paths "
            f"[{detail.inventory.freshness.value}]"
        )
    if detail.verification_posture is None:
        print("Verification posture: none attached yet")
    else:
        posture = detail.verification_posture
        print(f"Verification posture: {posture.state.value} - {posture.summary}")
    print(f"Review briefs: {len(detail.review_briefs)}")
    print(f"Readiness decisions: {len(detail.readiness)}")
    _print_limitations(detail.limitations)
    print("Safe next actions:")
    for action in detail.safe_next_actions:
        print(f"  - {action}")


def _print_limitations(limitations: list[str]) -> None:
    if not limitations:
        return
    print("Limitations:")
    for limitation in limitations:
        print(f"  - {limitation}")


__all__ = ["_changeset_command"]
