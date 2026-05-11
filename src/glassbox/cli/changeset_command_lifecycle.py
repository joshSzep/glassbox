"""Lifecycle-oriented changeset CLI command handlers."""

import argparse
import asyncio
from pathlib import Path
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_adoption_preview
from glassbox.cli.changeset_command_formatters import _print_changeset_detail
from glassbox.cli.changeset_command_formatters import _print_changeset_list
from glassbox.cli.changeset_command_formatters import _print_limitations
from glassbox.cli.changeset_command_formatters import _print_verification_plan
from glassbox.cli.changeset_command_formatters import (
    changeset_next_action_record_payloads,
)
from glassbox.cli.changeset_command_payloads import _adoption_result_payload
from glassbox.cli.changeset_command_payloads import _review_brief_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionRepository
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionService
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import claim_support
from glassbox.runtime.evidence_graph import evidence_neighborhood
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness


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


def _changeset_adoption_preview_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        preview = BranchCandidateAdoptionService(
            cast(
                BranchCandidateAdoptionRepository,
                runtime_context.repositories.sessions,
            )
        ).preview(
            args.branch_search_id,
            args.candidate_id,
            workspace_root=cwd,
            worktree_id=args.worktree_id,
        )

    if args.json:
        print_json_output(preview.model_dump(mode="json"))
    else:
        _print_adoption_preview(preview)
    return 0


def _changeset_adopt_candidate_command(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError(
            "adopt-candidate requires --confirm after inspecting "
            "`glassbox changeset adoption-preview`"
        )
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = BranchCandidateAdoptionService(
            cast(
                BranchCandidateAdoptionRepository,
                runtime_context.repositories.sessions,
            )
        ).adopt(
            args.branch_search_id,
            args.candidate_id,
            workspace_root=cwd,
            worktree_id=args.worktree_id,
            objective=args.objective,
        )

    if args.json:
        print_json_output(_adoption_result_payload(result))
    else:
        print(
            f"Adopted branch candidate into changeset {result.changeset.changeset_id}"
        )
        print("Workspace mutation performed: false")
        _print_adoption_preview(result.preview)
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
        artifacts = runtime_context.repositories.artifacts
        service = ChangesetQueryService(repository)
        detail = service.get_detail(args.changeset_id, workspace_root=cwd)
        verification_plan = ChangesetVerificationService(
            repository,
            artifacts,
        ).preview_plan(args.changeset_id, cwd)
        handoff_readiness = preview_handoff_readiness(
            ChangesetHandoffReadinessService(repository, artifacts),
            args.changeset_id,
            cwd,
        )

    if args.json:
        payload = detail.model_dump(mode="json")
        payload["verification_plan"] = verification_plan.model_dump(mode="json")
        payload["handoff_readiness"] = handoff_readiness.model_dump(mode="json")
        payload["next_action_records"] = changeset_next_action_record_payloads(detail)
        print_json_output(payload)
    else:
        _print_changeset_detail(
            detail,
            verification_plan=verification_plan,
            handoff_readiness=handoff_readiness,
        )
    return 0


def _changeset_evidence_graph_command(args: argparse.Namespace) -> int:
    if args.depth < 0:
        raise ValueError("--depth must be non-negative")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        artifacts = runtime_context.repositories.artifacts
        detail = ChangesetQueryService(repository).get_detail(
            args.changeset_id,
            workspace_root=cwd,
        )
        verification_plan = ChangesetVerificationService(
            repository,
            artifacts,
        ).preview_plan(args.changeset_id, cwd)
        graph = build_changeset_evidence_graph(
            detail,
            verification_plan=verification_plan,
        )

    if args.reviewer_safe:
        graph = reviewer_safe_graph_slice(graph)
    payload = graph
    if args.claim_id:
        support = claim_support(graph, args.claim_id)
        if support is None:
            raise ValueError(f"unknown evidence graph claim: {args.claim_id}")
        if args.json:
            print_json_output(support.model_dump(mode="json"))
        else:
            print(f"Claim: {support.title}")
            print(f"State: {support.state.value}")
            print(f"Summary: {support.summary}")
            _print_limitations(support.limitations)
        return 0
    if args.node_id:
        payload = evidence_neighborhood(graph, args.node_id, depth=args.depth)
    if args.summary:
        summary = summarize_evidence_graph(payload)
        if args.json:
            print_json_output(summary.model_dump(mode="json"))
        else:
            print(f"Evidence graph: {summary.graph_id}")
            print(f"Target: {summary.target_kind.value} {summary.target_id or ''}")
            print(
                "Counts: "
                f"{summary.node_count} nodes, "
                f"{summary.edge_count} edges, "
                f"{summary.claim_count} claims"
            )
            print(
                "Claim posture: "
                f"{summary.stale_claim_count} stale, "
                f"{summary.missing_claim_count} missing, "
                f"{summary.contradicted_claim_count} contradicted, "
                f"{summary.manual_only_claim_count} manual-only, "
                f"{summary.accepted_risk_claim_count} accepted risk"
            )
        return 0
    if args.json:
        print_json_output(payload.model_dump(mode="json"))
    else:
        summary = summarize_evidence_graph(payload)
        print(f"Evidence graph: {summary.graph_id}")
        print(f"Nodes: {summary.node_count}")
        print(f"Edges: {summary.edge_count}")
        print("Claims:")
        for item in payload.claims[:10]:
            print(f"  - {item.state.value}: {item.title} ({item.claim_id})")
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
        if result.limitation_summary is not None:
            print(
                "Limitations summarized: "
                f"{result.limitation_summary.overflow_count} overflow item(s) "
                f"of {result.limitation_summary.total_count} retained limitation(s)"
            )
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


def _create_changeset_from_args(
    service: ChangesetDerivationService,
    args: argparse.Namespace,
    cwd: Path,
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
