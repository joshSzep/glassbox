"""Changeset CLI command handlers."""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_adoption_preview
from glassbox.cli.changeset_command_formatters import _print_changeset_detail
from glassbox.cli.changeset_command_formatters import _print_changeset_list
from glassbox.cli.changeset_command_formatters import _print_commit_message_suggestion
from glassbox.cli.changeset_command_formatters import _print_commit_prep
from glassbox.cli.changeset_command_formatters import _print_feedback_detail
from glassbox.cli.changeset_command_formatters import _print_feedback_list
from glassbox.cli.changeset_command_formatters import _print_feedback_result
from glassbox.cli.changeset_command_formatters import _print_fixup_inventory_result
from glassbox.cli.changeset_command_formatters import _print_handoff_readiness
from glassbox.cli.changeset_command_formatters import _print_limitations
from glassbox.cli.changeset_command_formatters import _print_manual_evidence_list
from glassbox.cli.changeset_command_formatters import _print_manual_evidence_result
from glassbox.cli.changeset_command_formatters import _print_review_response_summary
from glassbox.cli.changeset_command_formatters import _print_verification_plan
from glassbox.cli.changeset_command_payloads import _adoption_result_payload
from glassbox.cli.changeset_command_payloads import _feedback_payload
from glassbox.cli.changeset_command_payloads import _precommit_evidence_payload
from glassbox.cli.changeset_command_payloads import _review_brief_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionRepository
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionService
from glassbox.runtime.changeset_export import export_changeset_package
from glassbox.runtime.changesets import AccessibilityEvidenceActionService
from glassbox.runtime.changesets import BrowserEvidenceActionService
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.changesets import ManualEvidenceActionService
from glassbox.runtime.changesets import ReviewFeedbackActionService
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryService
from glassbox.runtime.commit_messages import ChangesetCommitMessageSuggestionService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.handoff_readiness import ChangesetHandoffReadinessService
from glassbox.runtime.handoff_readiness import preview_handoff_readiness
from glassbox.runtime.precommit_evidence import ChangesetPreCommitEvidenceService


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
        print_json_output(payload)
    else:
        _print_changeset_detail(
            detail,
            verification_plan=verification_plan,
            handoff_readiness=handoff_readiness,
        )
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


def _changeset_evidence_command(args: argparse.Namespace) -> int:
    command = getattr(args, "evidence_command", None)
    if command == "attach":
        return _evidence_attach_command(args)
    if command in {"browser", "dashboard"}:
        return _evidence_browser_dashboard_command(args)
    if command == "accessibility":
        return _evidence_accessibility_command(args)
    if command == "list":
        return _evidence_list_command(args)
    raise ValueError("specify an evidence subcommand")


def _evidence_attach_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ManualEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            evidence_kind=ManualEvidenceKind(args.kind),
            summary=args.summary,
            source_label=args.source_label,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            note=args.note,
            command_text=args.command_text,
            external_url_label=args.external_url_label,
            local_file_label=args.local_file_label,
            local_file_path_hint=args.local_file,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_browser_dashboard_command(args: argparse.Namespace) -> int:
    width, height = args.viewport
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = BrowserEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            capture_kind=args.evidence_capture_kind,
            summary=args.summary,
            source_label=args.source_label,
            route_label=args.route_label,
            environment=args.environment,
            browser=args.browser,
            viewport_width=width,
            viewport_height=height,
            observed_at=_parse_optional_datetime(args.observed_at),
            input_method=args.input_method,
            console_checked=args.console_checked,
            screenshot_path_hint=args.screenshot_path_hint,
            screenshot_label=args.screenshot_label,
            screenshot_media_type=args.screenshot_media_type,
            screenshot_size_bytes=args.screenshot_size_bytes,
            screenshot_width=args.screenshot_width,
            screenshot_height=args.screenshot_height,
            skipped_cases=args.skipped_case,
            limitations=args.limitation,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_accessibility_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = AccessibilityEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            observation_kind=args.observation_kind,
            summary=args.summary,
            source_label=args.source_label,
            environment=args.environment,
            observed_issue=args.observed_issue,
            tool=args.tool,
            route_label=args.route_label,
            reviewer_label=args.reviewer_label,
            severity=args.severity,
            disposition=args.disposition,
            follow_up=args.follow_up,
            paired_tool_output_label=args.paired_tool_output_label,
            skipped_cases=args.skipped_case,
            limitations=args.limitation,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        evidence = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).list_manual_evidence(
            session_id=args.session_id,
            changeset_id=args.changeset_id,
            state=ManualEvidenceState(args.state) if args.state is not None else None,
            include_archived=args.include_archived,
            include_rejected=args.include_rejected,
            include_superseded=args.include_superseded,
            limit=args.limit,
        )
    if args.json:
        print_json_output([item.model_dump(mode="json") for item in evidence])
    else:
        _print_manual_evidence_list(evidence)
    return 0


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.removesuffix("Z")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("--observed-at must be an ISO-8601 datetime") from exc


def _changeset_feedback_command(args: argparse.Namespace) -> int:
    command = getattr(args, "feedback_command", None)
    if command == "add":
        return _feedback_add_command(args)
    if command == "list":
        return _feedback_list_command(args)
    if command == "show":
        return _feedback_show_command(args)
    if command == "status":
        return _feedback_status_command(args)
    if command == "resolve":
        return _feedback_resolve_command(args)
    if command == "fixup":
        return _feedback_fixup_command(args)
    if command == "reopen":
        return _feedback_reopen_command(args)
    if command == "archive":
        return _feedback_archive_command(args)
    if command == "accept-risk":
        return _feedback_accept_risk_command(args)
    raise ValueError("specify a feedback subcommand")


def _feedback_add_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).add_feedback(
            args.changeset_id,
            feedback_kind=ReviewFeedbackKind(args.kind),
            provenance=ReviewFeedbackProvenance(args.provenance),
            summary=args.summary,
            body=args.body,
            source_label=args.source_label,
            reviewer_label=args.reviewer_label,
            created_by=args.actor,
            scope_kind=ReviewFeedbackScopeKind(args.scope_kind),
            scope_reason=args.scope_reason,
            file_path=args.file,
            line_start=args.line_start,
            line_end=args.line_end,
        )
    return _print_feedback_result(result, args.json, "Recorded review feedback")


def _feedback_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        feedback = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).list_review_feedback(
            session_id=args.session_id,
            changeset_id=args.changeset_id,
            disposition=(
                ReviewFeedbackDisposition(args.disposition)
                if args.disposition is not None
                else None
            ),
            include_archived=args.include_archived,
            file_path=args.file,
            limit=args.limit,
        )
    if args.json:
        print_json_output([item.model_dump(mode="json") for item in feedback])
    else:
        _print_feedback_list(feedback)
    return 0


def _feedback_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        service = ChangesetQueryService(repository)
        feedback = service.get_review_feedback(args.feedback_id)
        if feedback is None:
            raise ValueError(f"unknown review feedback: {args.feedback_id}")
        scopes = service.list_review_feedback_scopes(
            feedback.session_id,
            feedback.feedback_id,
        )
        response_status = service.get_review_feedback_response_status(
            feedback.feedback_id,
            workspace_root=cwd,
        )
    payload = _feedback_payload(
        feedback,
        scopes=scopes,
        response_status=response_status,
    )
    if args.json:
        print_json_output(payload)
    else:
        _print_feedback_detail(feedback, scopes, response_status=response_status)
    return 0


def _feedback_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        summary = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).get_review_response_summary(args.changeset_id, workspace_root=cwd)
    if args.json:
        print_json_output(summary.model_dump(mode="json"))
    else:
        _print_review_response_summary(summary)
    return 0


def _feedback_resolve_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).resolve_feedback(
            args.feedback_id,
            resolution_summary=args.summary,
            residual_risk=args.residual_risk,
            resolved_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Resolved review feedback locally")


def _feedback_fixup_command(args: argparse.Namespace) -> int:
    if args.from_workspace and args.paths:
        raise ValueError("feedback fixup accepts either --from-workspace or --path")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        service = ReviewFeedbackFixupInventoryService(
            repository,
            runtime_context.repositories.artifacts,
        )
        if args.paths:
            result = service.record_explicit_paths(
                args.feedback_id,
                cwd,
                paths=args.paths,
                source_summary=args.source_summary,
                recorded_by=args.actor,
            )
        else:
            result = asyncio.run(
                service.record_workspace_inventory(
                    args.feedback_id,
                    cwd,
                    source_summary=args.source_summary,
                    recorded_by=args.actor,
                )
            )
        response_status = ChangesetQueryService(
            repository
        ).get_review_feedback_response_status(
            result.feedback_id,
            workspace_root=cwd,
        )
    return _print_fixup_inventory_result(
        result,
        response_status=response_status,
        as_json=args.json,
    )


def _feedback_reopen_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).reopen_feedback(
            args.feedback_id,
            reason=args.reason,
            reopened_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Reopened review feedback")


def _feedback_archive_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).archive_feedback(
            args.feedback_id,
            reason=args.reason,
            archived_by=args.actor,
            replacement_feedback_id=args.replacement_feedback_id,
        )
    return _print_feedback_result(result, args.json, "Archived review feedback")


def _feedback_accept_risk_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).accept_risk(
            args.feedback_id,
            risk_summary=args.risk_summary,
            acceptance_reason=args.reason,
            accepted_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Accepted review feedback risk")


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
