"""CLI command handlers for branch-search inspection."""

import argparse
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import BranchCandidateNeedsReview
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateRejected
from glassbox.core import BranchCandidateSelected
from glassbox.core import BranchSearchStarted
from glassbox.core import EventEnvelope
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.branch_search import BranchSearchRepository


def _branch_search_command(args: argparse.Namespace) -> int:
    command = getattr(args, "branch_search_command", None)
    if command == "start":
        return _branch_search_start_command(args)
    if command == "list":
        return _branch_search_list_command(args)
    if command == "show":
        return _branch_search_show_command(args)
    if command in {"select", "reject", "needs-review"}:
        return _branch_search_mark_candidate_command(args, command)
    raise ValueError("specify a branch-search subcommand")


def _branch_search_start_command(args: argparse.Namespace) -> int:
    if args.max_candidates < 1:
        raise ValueError("--max-candidates must be greater than zero")
    strategies = list(args.strategies)[: args.max_candidates]
    if not strategies:
        raise ValueError("at least one --strategy is required")
    cwd, db_path = resolve_runtime_location(args)
    search_id = new_branch_search_id()
    candidate_ids = [new_branch_candidate_id() for _strategy in strategies]
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        if repository.get_session(args.parent_session_id) is None:
            raise ValueError(f"unknown parent session: {args.parent_session_id}")
        repository.append_event(
            EventEnvelope(
                session_id=args.parent_session_id,
                sequence=0,
                payload=BranchSearchStarted(
                    search_id=search_id,
                    parent_session_id=args.parent_session_id,
                    objective=args.objective,
                    max_candidates=args.max_candidates,
                ),
            )
        )
        for candidate_id, strategy in zip(candidate_ids, strategies, strict=True):
            repository.append_event(
                EventEnvelope(
                    session_id=args.parent_session_id,
                    sequence=0,
                    payload=BranchCandidatePlanned(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        strategy_label=strategy,
                    ),
                )
            )
    payload = {
        "search_id": str(search_id),
        "parent_session_id": str(args.parent_session_id),
        "candidate_ids": [str(candidate_id) for candidate_id in candidate_ids],
        "objective": args.objective,
    }
    if args.json:
        print_json_output(payload)
    else:
        print(f"Started branch search {search_id}")
        print(f"Candidates: {len(candidate_ids)}")
    return 0


def _branch_search_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = BranchSearchQueryService(
            cast(BranchSearchRepository, runtime_context.repositories.sessions)
        )
        searches = service.list_searches(
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.json:
        print_json_output([search.model_dump(mode="json") for search in searches])
    else:
        if not searches:
            print("No branch searches found")
            return 0
        print(f"Branch searches: {len(searches)}")
        for search in searches:
            print(f"{search.search_id}  {search.status}  {search.objective}")
            print(f"  Candidates: {search.candidate_count}")
    return 0


def _branch_search_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = BranchSearchQueryService(
            cast(BranchSearchRepository, runtime_context.repositories.sessions)
        )
        detail = service.get_detail(args.search_id)
    if args.json:
        print_json_output(detail.model_dump(mode="json"))
    else:
        search = detail.search
        print(f"Branch search {search.search_id}")
        print(f"Status: {search.status}")
        print(f"Objective: {search.objective}")
        if search.selected_candidate_id is not None:
            print(f"Selected: {search.selected_candidate_id}")
        print(f"Candidates: {len(detail.candidates)}")
        for candidate in detail.candidates:
            print(
                f"  {candidate.candidate_id}  {candidate.status}  "
                f"{candidate.verification_status}  {candidate.strategy_label}"
            )
            if candidate.candidate_session_id is not None:
                print(f"    Session: {candidate.candidate_session_id}")
            if candidate.verification_summary:
                print(f"    Verification: {candidate.verification_summary}")
    return 0


def _branch_search_mark_candidate_command(
    args: argparse.Namespace,
    command: str,
) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = BranchSearchQueryService(
            cast(BranchSearchRepository, runtime_context.repositories.sessions)
        )
        detail = service.get_detail(args.search_id)
        if not any(
            candidate.candidate_id == args.candidate_id
            for candidate in detail.candidates
        ):
            raise ValueError(f"unknown branch-search candidate: {args.candidate_id}")
        payload = _candidate_mark_event(args, command)
        runtime_context.repositories.sessions.append_event(
            EventEnvelope(
                session_id=detail.search.session_id,
                sequence=0,
                payload=payload,
            )
        )
    result = {
        "search_id": str(args.search_id),
        "candidate_id": str(args.candidate_id),
        "state": command,
    }
    if args.json:
        print_json_output(result)
    else:
        print(
            f"Marked candidate {args.candidate_id} as {command} "
            f"for branch search {args.search_id}"
        )
    return 0


def _candidate_mark_event(args: argparse.Namespace, command: str):
    if command == "select":
        return BranchCandidateSelected(
            search_id=args.search_id,
            candidate_id=args.candidate_id,
            selected_by=args.actor,
            reason=args.reason,
        )
    if command == "reject":
        return BranchCandidateRejected(
            search_id=args.search_id,
            candidate_id=args.candidate_id,
            rejected_by=args.actor,
            reason=args.reason,
        )
    return BranchCandidateNeedsReview(
        search_id=args.search_id,
        candidate_id=args.candidate_id,
        marked_by=args.actor,
        reason=args.reason,
    )


__all__ = ["_branch_search_command"]
