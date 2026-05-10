"""Memory-candidate command handlers for repository intelligence CLI."""

import argparse
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService


def _repo_memory_candidates_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        candidates = WorkspaceMemoryCaptureService(
            cast(
                WorkspaceMemoryCaptureRepository,
                runtime_context.repositories.sessions,
            )
        ).list_candidates(
            args.session_id,
            policy=MemoryExtractionPolicy(max_candidates=args.limit),
        )
    if args.json:
        print_json_output(
            [candidate.model_dump(mode="json") for candidate in candidates]
        )
    else:
        if not candidates:
            print("No repository memory candidates found.")
        else:
            print(f"Repository memory candidates: {len(candidates)}")
            for candidate in candidates:
                print(f"- {candidate.candidate_id}: {candidate.kind.value}")
                print(f"  {candidate.summary}")
                print(
                    "  Review: glassbox memory confirm-candidate "
                    f"{candidate.session_id} {candidate.candidate_id}"
                )
    return 0


__all__ = ["_repo_memory_candidates_command"]
