"""CLI command handlers for branch-search inspection."""

import argparse
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.branch_search import BranchSearchRepository


def _branch_search_command(args: argparse.Namespace) -> int:
    command = getattr(args, "branch_search_command", None)
    if command == "list":
        return _branch_search_list_command(args)
    if command == "show":
        return _branch_search_show_command(args)
    raise ValueError("specify a branch-search subcommand")


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


__all__ = ["_branch_search_command"]
