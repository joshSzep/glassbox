"""CLI command handlers for changeset inspection."""

import argparse
import asyncio
from pathlib import Path
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import ChangesetRecord
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.commit_messages import ChangesetCommitMessageSuggestionService
from glassbox.runtime.commit_messages import CommitMessageSuggestion


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
    if command == "verification-plan":
        return _changeset_verification_plan_command(args)
    if command == "record-verification":
        return _changeset_record_verification_command(args)
    if command == "brief":
        return _changeset_brief_command(args)
    if command == "export":
        return _changeset_export_command(args)
    if command == "commit-message":
        return _changeset_commit_message_command(args)
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
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        service = ChangesetQueryService(repository)
        detail = service.get_detail(args.changeset_id, workspace_root=cwd)
        verification_plan = ChangesetVerificationService(
            repository,
            runtime_context.repositories.artifacts,
        ).preview_plan(args.changeset_id, cwd)

    if args.json:
        payload = detail.model_dump(mode="json")
        payload["verification_plan"] = verification_plan.model_dump(mode="json")
        print_json_output(payload)
    else:
        _print_changeset_detail(detail, verification_plan=verification_plan)
    return 0


def _changeset_refresh_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = asyncio.run(
            service.refresh_inventory(
                args.changeset_id,
                cwd,
                refreshed_by=args.actor,
            )
        )

    payload = {
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "artifact_id": str(result.artifact.artifact_id),
        "artifact_path": result.artifact.relative_path.as_posix(),
        "freshness": result.freshness.value,
        "source_digest": result.source_digest,
        "event": result.event.model_dump(mode="json"),
        "superseded_event": (
            result.superseded_event.model_dump(mode="json")
            if result.superseded_event is not None
            else None
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        print(f"Refreshed change inventory for changeset {args.changeset_id}")
        print(f"Inventory: {result.inventory.summary.changed_path_count} paths")
        print(f"Freshness: {result.freshness.value}")
        print(f"Artifact: {result.artifact.relative_path.as_posix()}")
        print(f"Event sequence: {result.event.sequence}")
    return 0


def _changeset_verification_plan_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        preview = service.preview_plan(args.changeset_id, cwd)

    if args.json:
        print_json_output(preview.model_dump(mode="json"))
    else:
        _print_verification_plan(preview)
    return 0


def _changeset_record_verification_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.record_existing_evidence(
            args.changeset_id,
            cwd,
            task_id=args.task_id,
            verification_id=args.verification_id,
        )

    if args.json:
        print_json_output(result.model_dump(mode="json"))
    else:
        print(f"Recorded verification posture for changeset {args.changeset_id}")
        print(f"State: {result.readiness.state.value}")
        print(f"Summary: {result.readiness.summary}")
        print(f"Event sequence: {result.event.sequence}")
        if result.retained_artifact_ids:
            print("Retained artifacts:")
            for artifact_id in result.retained_artifact_ids:
                print(f"  - {artifact_id}")
    return 0


def _changeset_brief_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ChangesetReviewBriefService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).generate(
            args.changeset_id,
            cwd,
            created_by=args.actor,
        )

    if args.json:
        print_json_output(_review_brief_payload(result))
    elif args.format == "markdown":
        print(result.markdown, end="")
    else:
        print(f"Generated review brief for changeset {args.changeset_id}")
        print(f"Artifact: {result.artifact.relative_path.as_posix()}")
        print(f"Event sequence: {result.event.sequence}")
        print(f"Review readiness sequence: {result.readiness_event.sequence}")
        _print_limitations(result.limitations)
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


def _changeset_export_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    output_path = Path(args.output_path)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        resolved_output = export_changeset_package(
            args.changeset_id,
            output_path,
            repository=cast(ChangesetRepository, runtime_context.repositories.sessions),
            artifact_repository=runtime_context.repositories.artifacts,
            workspace_root=cwd,
        )

    payload = {
        "changeset_id": str(args.changeset_id),
        "output_path": str(resolved_output),
        "status": "exported",
    }
    if args.json:
        print_json_output(payload)
    else:
        print(f"Exported changeset package for {args.changeset_id}")
        print(f"Output: {resolved_output}")
    return 0


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


def _print_changeset_detail(
    detail: ChangesetDetailView,
    *,
    verification_plan: ChangesetVerificationPlanPreview | None = None,
) -> None:
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
        if detail.inventory.previous_artifact_id is not None:
            print(f"  Previous artifact: {detail.inventory.previous_artifact_id}")
    if detail.inventory_status.reason is not None:
        print(
            "Inventory freshness: "
            f"{detail.inventory_status.freshness.value} - "
            f"{detail.inventory_status.reason}"
        )
    elif detail.inventory_status.current_source_digest is not None:
        print(f"Inventory freshness: {detail.inventory_status.freshness.value}")
    if detail.verification_posture is None:
        print("Verification posture: none attached yet")
    else:
        posture = detail.verification_posture
        print(f"Verification posture: {posture.state.value} - {posture.summary}")
    if verification_plan is not None:
        readiness = verification_plan.readiness
        print(f"Verification readiness: {readiness.state.value} - {readiness.summary}")
        print(
            "Verification counts: "
            f"{readiness.failed_count} failed, "
            f"{readiness.stale_count} stale, "
            f"{readiness.missing_count} missing, "
            f"{readiness.accepted_risk_count} accepted risk"
        )
        for requirement in readiness.requirements[:5]:
            print(
                f"  {requirement.state.value}: {requirement.check_name} - "
                f"{requirement.reason}"
            )
    print(f"Review briefs: {len(detail.review_briefs)}")
    print(f"Readiness decisions: {len(detail.readiness)}")
    _print_limitations(detail.limitations)
    print("Safe next actions:")
    for action in detail.safe_next_actions:
        print(f"  - {action}")


def _print_verification_plan(preview: ChangesetVerificationPlanPreview) -> None:
    print(f"Verification plan for changeset {preview.changeset_id}")
    print(f"Inventory: {preview.inventory_freshness.value}")
    print(f"Readiness: {preview.readiness.state.value} - {preview.readiness.summary}")
    if preview.changed_paths:
        print("Expected scope:")
        for path in preview.changed_paths[:20]:
            print(f"  - {path}")
    if preview.recommended_commands:
        print("Recommended commands:")
        for command in preview.recommended_commands:
            print(f"  - {command}")
    if preview.eval_profiles:
        print("Eval profiles:")
        for profile_id in preview.eval_profiles:
            print(f"  - {profile_id}")
    if preview.recipes:
        print("Recipes:")
        for recipe in preview.recipes:
            print(f"  - {recipe.title} ({recipe.recipe_id})")
            for command in recipe.commands:
                print(f"    command: {command}")
    if preview.retained_artifact_ids:
        print("Retained verification artifacts:")
        for artifact_id in preview.retained_artifact_ids:
            print(f"  - {artifact_id}")
    _print_limitations(preview.limitations)
    print("Safe next actions:")
    for action in preview.safe_next_actions:
        print(f"  - {action}")


def _print_commit_message_suggestion(
    suggestion: CommitMessageSuggestion,
) -> None:
    print("Commit message suggestion (not committed):")
    print(suggestion.message)
    if suggestion.limitations:
        _print_limitations(suggestion.limitations)
    print("Non-claims:")
    for non_claim in suggestion.non_claims:
        print(f"  - {non_claim}")


def _print_limitations(limitations: list[str]) -> None:
    if not limitations:
        return
    print("Limitations:")
    for limitation in limitations:
        print(f"  - {limitation}")


def _review_brief_payload(
    result: ChangesetReviewBriefGenerationResult,
) -> dict[str, object]:
    return {
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "artifact_id": str(result.artifact.artifact_id),
        "artifact_path": result.artifact.relative_path.as_posix(),
        "brief": result.brief.model_dump(mode="json"),
        "markdown": result.markdown,
        "event": result.event.model_dump(mode="json"),
        "readiness_event": result.readiness_event.model_dump(mode="json"),
        "limitations": result.limitations,
    }


__all__ = ["_changeset_command"]
