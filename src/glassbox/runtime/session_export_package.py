"""Portable session export package assembly."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from glassbox.core.ids import SessionId
from glassbox.core.types_handoff import HandoffIntent
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.branch_search import BranchSearchRepository
from glassbox.runtime.knowledge_posture import build_workspace_knowledge_posture
from glassbox.runtime.session_export_handoff import build_export_handoff
from glassbox.runtime.session_export_handoff import build_handoff_summary
from glassbox.runtime.session_export_manifest import artifact_references
from glassbox.runtime.session_export_manifest import branch_search_summaries
from glassbox.runtime.session_export_manifest import checkpoint_event_references
from glassbox.runtime.session_export_manifest import event_summary
from glassbox.runtime.session_export_manifest import export_transcript
from glassbox.runtime.session_export_manifest import policy_decisions
from glassbox.runtime.session_export_manifest import task_event_references
from glassbox.runtime.session_export_manifest import task_step_summaries
from glassbox.runtime.session_export_manifest import task_summaries
from glassbox.runtime.session_export_manifest import task_verification_summaries
from glassbox.runtime.session_export_models import SessionExportLineage
from glassbox.runtime.session_export_models import SessionExportMetadata
from glassbox.runtime.session_export_models import SessionExportPayload
from glassbox.runtime.session_export_models import SessionExportWorkspace
from glassbox.runtime.session_export_profile import attach_session_handoff_metadata
from glassbox.runtime.session_export_redaction import RedactionContext
from glassbox.runtime.session_export_redaction import redact_branchable_turns
from glassbox.runtime.session_export_redaction import redact_checkpoints
from glassbox.runtime.session_export_redaction import redact_child_sessions
from glassbox.runtime.session_export_redaction import redact_optional_text
from glassbox.runtime.session_export_redaction import redact_pending_approvals
from glassbox.runtime.session_export_redaction import redact_text
from glassbox.runtime.session_export_utils import stringify_optional
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def export_session_package(
    session_id: SessionId,
    output_path: Path,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    recipient: str | None = None,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
    output_format: str = "json",
) -> Path:
    package = build_session_export_payload(
        session_id,
        session_repository=session_repository,
        artifact_repository=artifact_repository,
        workspace_root=workspace_root,
        intent=intent,
        recipient=recipient,
        exported_by=exported_by,
        expected_custodian=expected_custodian,
        note=note,
        output_format=output_format,
    )
    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    serialized_package = json.dumps(
        package.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )
    resolved_output.write_text(f"{serialized_package}\n", encoding="utf-8")
    return resolved_output


def build_session_export_payload(
    session_id: SessionId,
    *,
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    workspace_root: Path,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    recipient: str | None = None,
    exported_by: str | None = None,
    expected_custodian: str | None = None,
    note: str | None = None,
    output_format: str = "json",
) -> SessionExportPayload:
    query_service = SessionQueryService(session_repository, artifact_repository)
    task_query_service = TaskQueryService(
        cast(TaskPlanRepository, session_repository),
        workspace_root=workspace_root,
    )
    branch_search_service = BranchSearchQueryService(
        cast(BranchSearchRepository, session_repository)
    )
    snapshot = query_service.get_session_snapshot(session_id, turn_metrics_limit=25)
    events = session_repository.read_session_events(session_id)
    redaction_context = RedactionContext(workspace_root=workspace_root.resolve())
    checkpoint_history = redact_checkpoints(
        session_repository.list_task_checkpoints(session_id),
        redaction_context,
    )
    task_details = [
        task_query_service.get_task_detail(task.task_id)
        for task in task_query_service.list_task_summaries(session_id=session_id)
    ]
    compactions = session_repository.list_context_compactions(session_id, limit=None)
    search_summaries = branch_search_summaries(
        branch_search_service,
        session_id,
    )
    knowledge_posture = build_workspace_knowledge_posture(
        workspace_root,
        session_repository,
    )

    payload = SessionExportPayload(
        exported_at=datetime.now(UTC),
        metadata=build_export_metadata(
            snapshot,
            workspace_root=workspace_root,
            redaction_context=redaction_context,
        ),
        lineage=build_export_lineage(snapshot, redaction_context),
        handoff=build_export_handoff(
            snapshot,
            events,
            redaction_context,
            latest_checkpoint=checkpoint_history[0] if checkpoint_history else None,
            intent=intent,
            recipient=recipient,
            exported_by=exported_by,
            expected_custodian=expected_custodian,
            note=note,
            summary=build_handoff_summary(
                snapshot=snapshot,
                task_details=task_details,
                compactions=compactions,
                branch_search_summaries=search_summaries,
                knowledge_posture=knowledge_posture,
                redaction_context=redaction_context,
            ),
        ),
        autonomy_budget_posture=snapshot.budget_posture,
        transcript=export_transcript(snapshot.transcript, redaction_context),
        active_tool_calls=snapshot.active_tool_calls,
        pending_approvals=redact_pending_approvals(
            snapshot.pending_approvals,
            redaction_context,
        ),
        turn_metrics=snapshot.turn_metrics,
        artifact_references=artifact_references(events, redaction_context),
        policy_decisions=policy_decisions(events, redaction_context),
        task_summaries=task_summaries(task_details, redaction_context),
        task_step_summaries=task_step_summaries(task_details, redaction_context),
        task_verification_summaries=task_verification_summaries(
            task_details,
            redaction_context,
        ),
        task_event_references=task_event_references(events, redaction_context),
        checkpoint_history=checkpoint_history,
        checkpoint_event_references=checkpoint_event_references(
            events,
            redaction_context,
        ),
        branch_search_summaries=search_summaries,
        event_count=len(events),
        events=[event_summary(event) for event in events],
    )
    return attach_session_handoff_metadata(
        payload,
        intent=intent,
        output_format=output_format,
    )


def build_export_metadata(
    snapshot: SessionSnapshotView,
    *,
    workspace_root: Path,
    redaction_context: RedactionContext,
) -> SessionExportMetadata:
    return SessionExportMetadata(
        session_id=snapshot.session_id,
        status=snapshot.status,
        model_name=redact_text(snapshot.model_name, redaction_context),
        approval_mode=snapshot.approval_mode,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        last_sequence=snapshot.last_sequence,
        workspace=SessionExportWorkspace(label=workspace_root.resolve().name),
    )


def build_export_lineage(
    snapshot: SessionSnapshotView,
    redaction_context: RedactionContext,
) -> SessionExportLineage:
    return SessionExportLineage(
        parent_session_id=snapshot.parent_session_id,
        forked_from_turn_id=stringify_optional(snapshot.forked_from_turn_id),
        forked_from_sequence=snapshot.forked_from_sequence,
        branch_label=redact_optional_text(snapshot.branch_label, redaction_context),
        child_sessions=redact_child_sessions(
            snapshot.child_sessions,
            redaction_context,
        ),
        branchable_turns=redact_branchable_turns(
            snapshot.branchable_turns,
            redaction_context,
        ),
        can_fork=snapshot.can_fork,
        latest_fork_point_turn_id=stringify_optional(
            snapshot.latest_fork_point_turn_id
        ),
        latest_fork_point_sequence=snapshot.latest_fork_point_sequence,
        fork_blocked_reason=redact_optional_text(
            snapshot.fork_blocked_reason,
            redaction_context,
        ),
    )
