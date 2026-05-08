"""Commit and handoff readiness changeset CLI command handlers."""

import argparse
import asyncio
from pathlib import Path
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_commit_message_suggestion
from glassbox.cli.changeset_command_formatters import _print_commit_prep
from glassbox.cli.changeset_command_formatters import _print_handoff_readiness
from glassbox.cli.changeset_command_payloads import _precommit_evidence_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.commit_messages import ChangesetCommitMessageSuggestionService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.precommit_evidence import ChangesetPreCommitEvidenceService


def _changeset_commit_message_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        suggestion = asyncio.run(
            ChangesetCommitMessageSuggestionService(
                cast(ChangesetRepository, runtime_context.repositories.sessions),
                runtime_context.repositories.artifacts,
            ).suggest(
                args.changeset_id,
                cwd,
                style=args.style,
            )
        )

    if args.json:
        print_json_output(suggestion.model_dump(mode="json"))
    else:
        _print_commit_message_suggestion(suggestion)
    return 0


def _changeset_record_precommit_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    summary_path = Path(args.summary)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = asyncio.run(
            ChangesetPreCommitEvidenceService(
                cast(ChangesetRepository, runtime_context.repositories.sessions),
                runtime_context.repositories.artifacts,
            ).record_summary(
                args.changeset_id,
                summary_path,
                cwd,
                evidence_kind=args.kind,
                state=args.state,
                recorded_by=args.actor,
            )
        )

    if args.json:
        print_json_output(_precommit_evidence_payload(result))
    else:
        print(f"Recorded {result.evidence.evidence_kind} evidence")
        print(f"Changeset: {result.changeset_id}")
        print(f"State: {result.evidence.state}")
        print(f"Summary: {result.evidence.summary}")
        print(f"Artifact: {result.artifact.relative_path.as_posix()}")
        print(f"Commit readiness: {result.commit_readiness.state.value}")
    return 0


def _changeset_commit_prep_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        artifacts = runtime_context.repositories.artifacts
        readiness = asyncio.run(
            ChangesetCommitReadinessService(repository, artifacts).preview(
                args.changeset_id,
                cwd,
            )
        )
        suggestion = asyncio.run(
            ChangesetCommitMessageSuggestionService(repository, artifacts).suggest(
                args.changeset_id,
                cwd,
                style=args.style,
            )
        )
        handoff_readiness = preview_handoff_readiness(
            ChangesetHandoffReadinessService(repository, artifacts),
            args.changeset_id,
            cwd,
        )

    payload = {
        "changeset_id": str(args.changeset_id),
        "commit_readiness": readiness.model_dump(mode="json"),
        "commit_message": suggestion.model_dump(mode="json"),
        "handoff_readiness": handoff_readiness.model_dump(mode="json"),
        "safe_copy": (
            "Glassbox prepared local commit guidance only; it did not stage, "
            "commit, push, or open a PR."
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        _print_commit_prep(readiness, suggestion, handoff_readiness)
    return 0


def _changeset_handoff_readiness_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        readiness = preview_handoff_readiness(
            ChangesetHandoffReadinessService(
                cast(ChangesetRepository, runtime_context.repositories.sessions),
                runtime_context.repositories.artifacts,
            ),
            args.changeset_id,
            cwd,
        )

    if args.json:
        print_json_output(readiness.model_dump(mode="json"))
    else:
        _print_handoff_readiness(readiness)
    return 0
