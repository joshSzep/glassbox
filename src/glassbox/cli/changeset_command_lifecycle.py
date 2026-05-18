"""Lifecycle-oriented changeset CLI command handlers."""

import argparse
import asyncio
from pathlib import Path
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_adoption_preview
from glassbox.cli.changeset_command_formatters import _print_changeset_detail
from glassbox.cli.changeset_command_formatters import _print_changeset_list
from glassbox.cli.changeset_command_formatters import _print_guided_workup
from glassbox.cli.changeset_command_formatters import _print_limitations
from glassbox.cli.changeset_command_formatters import _print_path_verification_plan
from glassbox.cli.changeset_command_formatters import _print_verification_disposition
from glassbox.cli.changeset_command_formatters import _print_verification_execution
from glassbox.cli.changeset_command_formatters import _print_verification_plan
from glassbox.cli.changeset_command_formatters import _print_workup_preview
from glassbox.cli.changeset_command_formatters import (
    changeset_next_action_record_payloads,
)
from glassbox.cli.changeset_command_payloads import _adoption_result_payload
from glassbox.cli.changeset_command_payloads import _review_brief_payload
from glassbox.cli.handoff_preview_output import print_handoff_redaction_preview
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import HandoffIntent
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionRepository
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionService
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changeset_export import inspect_changeset_export_package
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.changesets import ChangesetWorkupPreviewService
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import claim_support
from glassbox.runtime.evidence_graph import evidence_neighborhood
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.handoff_redaction_preview import build_changeset_redaction_preview
from glassbox.tools.workflow import DiffSummaryScope


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


def _changeset_workup_preview_command(args: argparse.Namespace) -> int:
    if args.max_files < 1:
        raise ValueError("--max-files must be greater than zero")
    cwd, _db_path = resolve_runtime_location(args)
    preview = ChangesetWorkupPreviewService().preview_sync(
        cwd,
        paths=args.paths,
        scope=DiffSummaryScope(args.scope),
        session_id=str(args.session_id) if args.session_id is not None else None,
        max_files=args.max_files,
    )
    if args.json:
        print_json_output(preview.model_dump(mode="json"))
    else:
        _print_workup_preview(preview)
    return 0


def _changeset_workup_command(args: argparse.Namespace) -> int:
    if args.confirm_create and args.session_id is None and args.changeset_id is None:
        raise ValueError("--confirm-create requires --session")
    if args.skip_verification_ids and not args.skip_reason:
        raise ValueError("--skip-verification requires --skip-reason")
    if args.accept_risk_verification_ids and (
        not args.risk_reason or not args.residual_risks
    ):
        raise ValueError(
            "--accept-risk-verification requires --risk-reason and at least one --risk"
        )
    cwd, db_path = resolve_runtime_location(args)
    preview = ChangesetWorkupPreviewService().preview_sync(
        cwd,
        session_id=str(args.session_id) if args.session_id is not None else None,
    )
    steps: list[dict[str, object]] = [
        _guided_step(
            "preview",
            "completed",
            "Inspected workspace diff and verification plan without mutation.",
            durable_event_count=0,
        )
    ]
    changeset_id = args.changeset_id
    verification_plan = None
    handoff_readiness = None
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        artifacts = runtime_context.repositories.artifacts
        if changeset_id is None:
            if args.confirm_create:
                result = ChangesetDerivationService(
                    repository
                ).create_from_workspace_diff(
                    args.session_id,
                    cwd,
                    objective=args.objective,
                )
                changeset_id = result.changeset_id
                steps.append(
                    _guided_step(
                        "create_changeset",
                        "completed",
                        f"Created changeset {changeset_id}.",
                        durable_event_count=len(result.stored_events),
                        limitations=result.limitations,
                    )
                )
            else:
                steps.append(
                    _guided_step(
                        "create_changeset",
                        "awaiting_confirmation",
                        (
                            "Run with --confirm-create and --session SESSION_ID "
                            "to create local changeset evidence."
                        ),
                    )
                )
        if changeset_id is not None:
            action_service = ChangesetActionService(repository, artifacts)
            verification_service = ChangesetVerificationService(repository, artifacts)
            if args.confirm_refresh:
                result = asyncio.run(
                    action_service.refresh_inventory(
                        changeset_id,
                        cwd,
                        refreshed_by="operator",
                    )
                )
                steps.append(
                    _guided_step(
                        "refresh_inventory",
                        "completed",
                        f"Refreshed inventory artifact {result.artifact.artifact_id}.",
                        durable_event_count=1
                        + (1 if result.superseded_event is not None else 0),
                    )
                )
            else:
                steps.append(
                    _guided_step(
                        "refresh_inventory",
                        "awaiting_confirmation",
                        (
                            "Run with --confirm-refresh to record fresh inventory "
                            "evidence."
                        ),
                    )
                )
            verification_plan = verification_service.preview_plan(changeset_id, cwd)
            steps.append(
                _guided_step(
                    "verification_plan",
                    "completed",
                    (
                        f"Previewed {len(verification_plan.plan_entries)} plan "
                        "entry(s); no commands were run."
                    ),
                    durable_event_count=0,
                    limitations=verification_plan.limitations,
                )
            )
            for verification_id in args.select_verification_ids or []:
                result = verification_service.select_plan_entry(
                    changeset_id,
                    cwd,
                    verification_id=verification_id,
                )
                steps.append(
                    _guided_step(
                        "select_verification",
                        "completed",
                        f"Selected verification {verification_id}.",
                        durable_event_count=len(result.events),
                    )
                )
            for verification_id in args.skip_verification_ids or []:
                result = verification_service.skip_plan_entry(
                    changeset_id,
                    cwd,
                    verification_id=verification_id,
                    reason=args.skip_reason,
                )
                steps.append(
                    _guided_step(
                        "skip_verification",
                        "completed",
                        f"Skipped verification {verification_id}.",
                        durable_event_count=len(result.events),
                        limitations=result.non_claims,
                    )
                )
            for verification_id in args.accept_risk_verification_ids or []:
                result = verification_service.accept_plan_entry_risk(
                    changeset_id,
                    cwd,
                    verification_id=verification_id,
                    reason=args.risk_reason,
                    residual_risks=args.residual_risks,
                )
                steps.append(
                    _guided_step(
                        "accept_verification_risk",
                        "completed",
                        f"Accepted residual risk for verification {verification_id}.",
                        durable_event_count=len(result.events),
                        limitations=result.non_claims,
                    )
                )
            if args.confirm_brief:
                result = ChangesetReviewBriefService(repository, artifacts).generate(
                    changeset_id,
                    cwd,
                    created_by="operator",
                )
                steps.append(
                    _guided_step(
                        "review_brief",
                        "completed",
                        (
                            "Generated review brief artifact "
                            f"{result.artifact.artifact_id}."
                        ),
                        durable_event_count=2,
                        limitations=result.limitations,
                    )
                )
            else:
                steps.append(
                    _guided_step(
                        "review_brief",
                        "awaiting_confirmation",
                        (
                            "Run with --confirm-brief to generate reviewer-safe "
                            "brief evidence."
                        ),
                    )
                )
            handoff_readiness = preview_handoff_readiness(
                ChangesetHandoffReadinessService(repository, artifacts),
                changeset_id,
                cwd,
            )
            steps.append(
                _guided_step(
                    "handoff_readiness",
                    "completed",
                    f"Handoff posture: {handoff_readiness.state}.",
                    durable_event_count=0,
                    limitations=handoff_readiness.limitations,
                )
            )
    payload = {
        "workflow": "changeset_workup",
        "changeset_id": str(changeset_id) if changeset_id is not None else None,
        "session_id": str(args.session_id) if args.session_id is not None else None,
        "steps": steps,
        "preview": preview.model_dump(mode="json"),
        "verification_plan": (
            verification_plan.model_dump(mode="json")
            if verification_plan is not None
            else None
        ),
        "handoff_readiness": (
            handoff_readiness.model_dump(mode="json")
            if handoff_readiness is not None
            else None
        ),
        "non_claims": [
            "guided workup does not stage, commit, push, publish, or open a PR",
            "verification planning does not run commands",
            "durable events are recorded only for explicitly confirmed steps",
        ],
    }
    if args.json:
        print_json_output(payload)
    else:
        _print_guided_workup(payload)
    return 0


def _guided_step(
    step: str,
    status: str,
    summary: str,
    *,
    durable_event_count: int = 0,
    limitations: list[str] | tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "step": step,
        "status": status,
        "summary": summary,
        "durable_event_count": durable_event_count,
        "limitations": list(limitations),
    }


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
        if args.changeset_id is None:
            if not args.paths:
                raise ValueError("changeset_id or at least one --path is required")
            path_preview = service.preview_paths(cwd, args.paths)
            if args.json:
                print_json_output(path_preview.model_dump(mode="json"))
            else:
                _print_path_verification_plan(path_preview)
            return 0
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


def _changeset_select_verification_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.select_plan_entry(
            args.changeset_id,
            cwd,
            verification_id=args.verification_id,
        )
    return _print_verification_disposition(result, as_json=args.json)


def _changeset_run_verification_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.run_selected_plan_entry(
            args.changeset_id,
            cwd,
            verification_id=args.verification_id,
            confirmed=args.confirm,
        )
    return _print_verification_execution(result, as_json=args.json)


def _changeset_skip_verification_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.skip_plan_entry(
            args.changeset_id,
            cwd,
            verification_id=args.verification_id,
            reason=args.reason,
        )
    return _print_verification_disposition(result, as_json=args.json)


def _changeset_accept_verification_risk_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.accept_plan_entry_risk(
            args.changeset_id,
            cwd,
            verification_id=args.verification_id,
            reason=args.reason,
            residual_risks=args.residual_risks,
            accepted_by=args.accepted_by,
        )
    return _print_verification_disposition(result, as_json=args.json)


def _changeset_supersede_verification_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = ChangesetVerificationService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        )
        result = service.supersede_plan_entry(
            args.changeset_id,
            cwd,
            verification_id=args.verification_id,
            replacement_verification_id=args.replacement_verification_id,
            reason=args.reason,
        )
    return _print_verification_disposition(result, as_json=args.json)


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
    output_format = args.format
    markdown_output_path = (
        Path(args.markdown_output_path)
        if getattr(args, "markdown_output_path", None)
        else None
    )
    if output_format == "json+markdown" and markdown_output_path is None:
        markdown_output_path = output_path.with_suffix(".md")
    intent = HandoffIntent(args.intent)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        if args.preview:
            preview = build_changeset_redaction_preview(
                args.changeset_id,
                repository=cast(
                    ChangesetRepository,
                    runtime_context.repositories.sessions,
                ),
                artifact_repository=runtime_context.repositories.artifacts,
                workspace_root=cwd,
                intent=intent,
                recipient=args.recipient,
                expected_custodian=args.expected_custodian,
                exported_by=args.exported_by,
                note=args.note,
                output_format=output_format,
            )
            if args.json:
                print_json_output(preview.model_dump(mode="json"))
            else:
                print_handoff_redaction_preview(preview)
            return 0
        resolved_output = export_changeset_package(
            args.changeset_id,
            output_path,
            repository=cast(ChangesetRepository, runtime_context.repositories.sessions),
            artifact_repository=runtime_context.repositories.artifacts,
            workspace_root=cwd,
            intent=intent,
            recipient=args.recipient,
            expected_custodian=args.expected_custodian,
            exported_by=args.exported_by,
            note=args.note,
            output_format=output_format,
            markdown_output_path=markdown_output_path,
        )

    payload = {
        "changeset_id": str(args.changeset_id),
        "output_path": str(resolved_output),
        "markdown_output_path": (
            str(markdown_output_path.resolve())
            if markdown_output_path is not None
            else None
        ),
        "status": "exported",
    }
    if args.json:
        print_json_output(payload)
    else:
        print(f"Exported changeset package for {args.changeset_id}")
        print(f"Output: {resolved_output}")
        if markdown_output_path is not None:
            print(f"Markdown: {markdown_output_path.resolve()}")
    return 0


def _changeset_export_inspect_command(args: argparse.Namespace) -> int:
    summary = inspect_changeset_export_package(Path(args.bundle_path))
    if args.json:
        print_json_output(summary)
    else:
        print(f"Changeset export bundle: {summary['bundle_path']}")
        print(
            f"Bundle: {summary['export_kind']} v{summary['schema_version']} "
            f"for {summary['changeset_id']}"
        )
        print(f"Status: {summary['status']}")
        if summary.get("profile_id"):
            print(f"Profile: {summary['profile_id']}")
        print(f"Verification: {summary['verification_state']}")
        print(f"Handoff: {summary['handoff_state']}")
        print(
            "Evidence graph: "
            f"{summary['evidence_graph_node_count']} node(s), "
            f"{summary['evidence_graph_claim_count']} claim(s)"
        )
        print(f"Feedback: {summary['feedback_count']}")
        print(f"Manual evidence: {summary['manual_evidence_count']}")
        print(f"Redaction rows: {summary['redaction_report_count']}")
        print("Safe inspection commands:")
        for command in summary["safe_inspection_commands"][:5]:
            print(f"  - {command}")
        print("Non-claims:")
        for claim in summary["non_claims"][:5]:
            print(f"  - {claim}")
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
