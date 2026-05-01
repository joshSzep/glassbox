"""Manifest and reference helpers for portable session export packages."""

from collections.abc import Sequence
from typing import cast

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.session_export_models import SessionExportArtifactReference
from glassbox.runtime.session_export_models import SessionExportBranchSearchSummary
from glassbox.runtime.session_export_models import SessionExportCheckpointEventReference
from glassbox.runtime.session_export_models import SessionExportEventSummary
from glassbox.runtime.session_export_models import SessionExportPolicyDecision
from glassbox.runtime.session_export_models import SessionExportTaskEventReference
from glassbox.runtime.session_export_models import SessionExportTaskStepSummary
from glassbox.runtime.session_export_models import SessionExportTaskSummary
from glassbox.runtime.session_export_models import SessionExportTaskVerificationSummary
from glassbox.runtime.session_export_models import SessionExportTranscriptMessage
from glassbox.runtime.session_export_redaction import RedactionContext
from glassbox.runtime.session_export_redaction import portable_artifact_path
from glassbox.runtime.session_export_redaction import redact_json_value
from glassbox.runtime.session_export_redaction import redact_optional_text
from glassbox.runtime.session_export_redaction import redact_text
from glassbox.runtime.session_export_utils import stringify_optional
from glassbox.runtime.task_queries import TaskDetailView


def export_transcript(
    transcript: Sequence[TranscriptMessage],
    redaction_context: RedactionContext,
) -> list[SessionExportTranscriptMessage]:
    return [
        SessionExportTranscriptMessage(
            message_id=str(message.message_id),
            role=message.role,
            parts=[
                MessagePart(
                    kind=part.kind,
                    text=redact_text(part.text, redaction_context),
                )
                for part in message.parts
            ],
            created_at=message.created_at,
        )
        for message in transcript
    ]


def artifact_references(
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
) -> list[SessionExportArtifactReference]:
    references: list[SessionExportArtifactReference] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, ToolArtifactRecorded | ReplayArtifactRecorded):
            continue
        references.append(
            SessionExportArtifactReference(
                sequence=event.sequence,
                event_type=event.event_type,
                turn_id=stringify_optional(payload.turn_id),
                tool_call_id=stringify_optional(payload.tool_call_id),
                artifact_kind=payload.artifact_kind,
                path=portable_artifact_path(payload.path, redaction_context),
                content_sha256=payload.content_sha256,
                size_bytes=payload.size_bytes,
            )
        )
    return references


def policy_decisions(
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
) -> list[SessionExportPolicyDecision]:
    decisions: list[SessionExportPolicyDecision] = []
    for event in events:
        payload = event.payload
        if not isinstance(
            payload,
            ModelToolCallRequested | ToolExecutionStarted | ApprovalRequested,
        ):
            continue
        trace = policy_trace(payload)
        if trace is None:
            continue
        decisions.append(
            SessionExportPolicyDecision(
                sequence=event.sequence,
                event_type=event.event_type,
                turn_id=stringify_optional(payload.turn_id),
                tool_call_id=stringify_optional(getattr(payload, "tool_call_id", None)),
                approval_id=stringify_optional(getattr(payload, "approval_id", None)),
                tool_name=redact_optional_text(
                    getattr(payload, "tool_name", None),
                    redaction_context,
                ),
                subject=redact_optional_text(
                    getattr(payload, "subject", None),
                    redaction_context,
                ),
                trace=trace.model_copy(
                    update={
                        "source_label": redact_text(
                            trace.source_label,
                            redaction_context,
                        ),
                        "reason": redact_text(trace.reason, redaction_context),
                    }
                ),
            )
        )
    return decisions


def policy_trace(
    payload: ModelToolCallRequested | ToolExecutionStarted | ApprovalRequested,
) -> PolicyDecisionTrace | None:
    if payload.policy_trace is not None:
        return payload.policy_trace

    reason = (
        payload.reason
        if isinstance(payload, ApprovalRequested)
        else payload.policy_reason
    )
    if (
        payload.policy_outcome is None
        or payload.policy_risk_level is None
        or payload.policy_source_kind is None
        or payload.policy_source_label is None
        or reason is None
    ):
        return None

    return PolicyDecisionTrace(
        outcome=payload.policy_outcome,
        risk_level=payload.policy_risk_level,
        source_kind=payload.policy_source_kind,
        source_label=payload.policy_source_label,
        reason=reason,
    )


def active_tool_calls_for_export(
    active_tool_calls: Sequence[ToolCallRecord],
) -> list[ToolCallRecord]:
    return list(active_tool_calls)


def task_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: RedactionContext,
) -> list[SessionExportTaskSummary]:
    return [
        SessionExportTaskSummary(
            task_id=detail.task.task_id,
            title=redact_text(detail.task.title, redaction_context),
            goal=redact_text(detail.task.goal, redaction_context),
            status=detail.task.status.value,
            updated_at=detail.task.updated_at,
            blocked_reason=(
                None
                if detail.task.blocked_reason is None
                else detail.task.blocked_reason.value
            ),
            blocked_detail=redact_optional_text(
                detail.task.blocked_detail,
                redaction_context,
            ),
            current_step_id=detail.task.current_step_id,
            step_count=detail.task.step_count,
            next_action_summary=redact_text(
                detail.task.next_action_summary,
                redaction_context,
            ),
        )
        for detail in task_details
    ]


def task_step_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: RedactionContext,
) -> list[SessionExportTaskStepSummary]:
    summaries: list[SessionExportTaskStepSummary] = []
    for detail in task_details:
        summaries.extend(
            SessionExportTaskStepSummary(
                task_id=detail.task.task_id,
                step_id=step.step_id,
                title=redact_text(step.title, redaction_context),
                order=step.order,
                status=step.status.value,
                description=redact_optional_text(
                    step.description,
                    redaction_context,
                ),
                blocked_reason=(
                    None if step.blocked_reason is None else step.blocked_reason.value
                ),
            )
            for step in detail.steps
        )
    return summaries


def task_verification_summaries(
    task_details: Sequence[TaskDetailView],
    redaction_context: RedactionContext,
) -> list[SessionExportTaskVerificationSummary]:
    summaries: list[SessionExportTaskVerificationSummary] = []
    for detail in task_details:
        summaries.extend(
            SessionExportTaskVerificationSummary(
                task_id=detail.task.task_id,
                verification_id=verification.verification_id,
                check_name=redact_text(verification.check_name, redaction_context),
                status=verification.status.value,
                step_id=verification.step_id,
                summary=redact_optional_text(
                    verification.summary,
                    redaction_context,
                ),
            )
            for verification in detail.verifications
        )
    return summaries


def task_event_references(
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
) -> list[SessionExportTaskEventReference]:
    references: list[SessionExportTaskEventReference] = []
    for event in events:
        if event.task_id is None:
            continue
        if isinstance(event.payload, TaskCheckpointCreated):
            continue
        references.append(
            SessionExportTaskEventReference(
                sequence=event.sequence,
                event_type=event.event_type,
                created_at=event.created_at,
                task_id=event.task_id,
                turn_id=stringify_optional(event.turn_id),
                payload=cast(
                    dict[str, object],
                    redact_json_value(
                        event.payload.model_dump(mode="json"),
                        redaction_context,
                    ),
                ),
            )
        )
    return references


def checkpoint_event_references(
    events: Sequence[EventEnvelope],
    redaction_context: RedactionContext,
) -> list[SessionExportCheckpointEventReference]:
    references: list[SessionExportCheckpointEventReference] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskCheckpointCreated):
            continue
        references.append(
            SessionExportCheckpointEventReference(
                sequence=event.sequence,
                event_type=event.event_type,
                created_at=event.created_at,
                checkpoint_id=payload.checkpoint_id,
                task_id=payload.task_id,
                turn_id=stringify_optional(payload.turn_id),
                payload=cast(
                    dict[str, object],
                    redact_json_value(
                        payload.model_dump(mode="json"),
                        redaction_context,
                    ),
                ),
            )
        )
    return references


def branch_search_summaries(
    branch_search_service: BranchSearchQueryService,
    session_id,
) -> list[SessionExportBranchSearchSummary]:
    summaries: list[SessionExportBranchSearchSummary] = []
    for search in branch_search_service.list_searches(session_id=session_id):
        detail = branch_search_service.get_detail(search.search_id)
        summaries.append(
            SessionExportBranchSearchSummary(
                search=detail.search,
                candidates=detail.candidates,
            )
        )
    return summaries


def event_summary(event: EventEnvelope) -> SessionExportEventSummary:
    return SessionExportEventSummary(
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        turn_id=stringify_optional(event.turn_id),
        message_id=stringify_optional(event.message_id),
        tool_call_id=stringify_optional(event.tool_call_id),
        approval_id=stringify_optional(event.approval_id),
    )
