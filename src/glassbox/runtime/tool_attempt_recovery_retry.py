"""Retry execution helpers for durable tool-attempt recovery."""

import json
from typing import cast

from glassbox.core import ApprovalMode
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import ToolOutputStream
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.tool_attempt_recovery_artifacts import (
    record_retry_output_artifact,
)
from glassbox.runtime.tool_attempt_recovery_common import decode_arguments_json
from glassbox.runtime.tool_attempt_recovery_common import require_attempt
from glassbox.runtime.tool_attempt_recovery_common import source_tool_call_payload
from glassbox.runtime.tool_attempt_recovery_models import RecoveredToolCallRequest
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryError
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryResult
from glassbox.runtime.tool_attempts import classify_tool_attempt_retry
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import build_ask_user_tool_registry
from glassbox.tools.policy import ToolPolicyContext
from glassbox.tools.policy import ToolPolicyEngine
from glassbox.tools.policy_config import load_tool_policy_manifest
from glassbox.tools.runtime import PreparedToolExecution
from glassbox.tools.runtime import ToolCallRequest
from glassbox.tools.runtime import ToolRuntime


async def retry_tool_attempt(
    repository: SessionRepository,
    artifact_repository: ArtifactRepository | None,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
    *,
    confirmed: bool = False,
    requested_by: str = "operator",
    reason: str | None = None,
) -> ToolAttemptRecoveryResult:
    """Retry a stale or failed attempt using retained model tool-call arguments."""

    original = require_attempt(repository, session_id, tool_attempt_id)
    ensure_retry_allowed(original, confirmed=confirmed)
    source_payload = source_tool_call_payload(repository, session_id, original)
    if source_payload is None:
        raise ToolAttemptRecoveryError(
            "tool attempt cannot be retried because its source tool-call arguments "
            "were not retained"
        )
    arguments = decode_arguments_json(source_payload.arguments_json)
    if arguments is None:
        raise ToolAttemptRecoveryError(
            "tool attempt cannot be retried because its source arguments are invalid"
        )
    session = repository.get_session(session_id)
    if session is None:
        raise ToolAttemptRecoveryError(f"session {session_id} not found")

    tool_runtime = ToolRuntime(
        build_ask_user_tool_registry(session.cwd),
        ToolPolicyEngine(),
        ToolPolicyContext(
            workspace_root=session.cwd,
            approval_mode=ApprovalMode(session.approval_mode),
            policy_manifest=load_tool_policy_manifest(session.cwd),
        ),
    )
    prepared = tool_runtime.prepare_tool_call(
        cast(
            ToolCallRequest,
            RecoveredToolCallRequest(
                tool_name=source_payload.tool_name,
                arguments=arguments,
                tool_call_id=f"retry:{original.tool_attempt_id}",
            ),
        )
    )
    if not prepared.policy_decision.allowed:
        raise ToolAttemptRecoveryError(prepared.policy_decision.reason)
    if prepared.policy_decision.requires_approval and not confirmed:
        raise ToolAttemptRecoveryError(
            f"retry requires explicit confirmation: {prepared.policy_decision.reason}"
        )

    retry_attempt_id = new_tool_attempt_id()
    record_retry_requested(
        repository,
        session_id,
        original,
        retry_attempt_id=retry_attempt_id,
        requested_by=requested_by,
        reason=reason,
    )
    retry_attempt = await execute_retry_attempt(
        repository,
        artifact_repository,
        session_id,
        original,
        retry_attempt_id=retry_attempt_id,
        prepared=prepared,
        tool_runtime=tool_runtime,
        confirmed=confirmed,
    )
    refreshed_original = repository.get_tool_attempt(session_id, tool_attempt_id)
    if refreshed_original is None:
        raise ToolAttemptRecoveryError("original attempt projection disappeared")
    return ToolAttemptRecoveryResult(
        message=(
            f"retried {original.tool_attempt_id} as {retry_attempt.tool_attempt_id}; "
            f"new status is {retry_attempt.status.value}"
        ),
        original_attempt=refreshed_original,
        retry_attempt=retry_attempt,
    )


async def execute_retry_attempt(
    repository: SessionRepository,
    artifact_repository: ArtifactRepository | None,
    session_id: SessionId,
    original: ToolAttemptRecord,
    *,
    retry_attempt_id: ToolAttemptId,
    prepared: PreparedToolExecution,
    tool_runtime: ToolRuntime,
    confirmed: bool,
) -> ToolAttemptRecord:
    """Run the prepared retry and persist the same durable evidence as a tool turn."""

    started_retry = classify_tool_attempt_retry(
        status=ToolAttemptStatus.STARTED,
        tool_name=prepared.tool_name,
        tool_spec=prepared.tool.spec,
        arguments=prepared.validated_arguments,
        policy_decision=prepared.policy_decision,
    )
    running_retry = classify_tool_attempt_retry(
        status=ToolAttemptStatus.RUNNING,
        tool_name=prepared.tool_name,
        tool_spec=prepared.tool.spec,
        arguments=prepared.validated_arguments,
        policy_decision=prepared.policy_decision,
    )
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ModelToolCallRequested(
                    turn_id=original.turn_id,
                    tool_call_id=prepared.event_tool_call_id,
                    tool_name=prepared.tool_name,
                    arguments_json=json.dumps(
                        prepared.validated_arguments.model_dump(mode="json"),
                        sort_keys=True,
                    ),
                    policy_outcome=prepared.policy_decision.outcome,
                    policy_risk_level=prepared.policy_decision.risk_level,
                    policy_source_kind=prepared.policy_decision.source_kind,
                    policy_source_label=prepared.policy_decision.source_label,
                    policy_reason=prepared.policy_decision.reason,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolExecutionStarted(
                    turn_id=original.turn_id,
                    tool_call_id=prepared.event_tool_call_id,
                    tool_name=prepared.tool_name,
                    policy_outcome=prepared.policy_decision.outcome,
                    policy_risk_level=prepared.policy_decision.risk_level,
                    policy_source_kind=prepared.policy_decision.source_kind,
                    policy_source_label=prepared.policy_decision.source_label,
                    policy_reason=prepared.policy_decision.reason,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=retry_attempt_id,
                    status=ToolAttemptStatus.STARTED,
                    turn_id=original.turn_id,
                    tool_call_id=prepared.event_tool_call_id,
                    task_id=original.task_id,
                    tool_name=prepared.tool_name,
                    message=f"Retry started for {original.tool_attempt_id}.",
                    safe_to_retry=started_retry.safe_to_retry,
                    retry_classification=started_retry.classification,
                    retry_requires_approval=started_retry.requires_approval,
                    retry_reason=started_retry.reason,
                    retry_policy_reason=started_retry.policy_reason,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=retry_attempt_id,
                    status=ToolAttemptStatus.RUNNING,
                    turn_id=original.turn_id,
                    tool_call_id=prepared.event_tool_call_id,
                    task_id=original.task_id,
                    tool_name=prepared.tool_name,
                    message=f"Retry running for {original.tool_attempt_id}.",
                    safe_to_retry=running_retry.safe_to_retry,
                    retry_classification=running_retry.classification,
                    retry_requires_approval=running_retry.requires_approval,
                    retry_reason=running_retry.reason,
                    retry_policy_reason=running_retry.policy_reason,
                ),
            ),
        ]
    )

    def record_chunk(stream: str, chunk: str) -> None:
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolOutputChunk(
                    turn_id=original.turn_id,
                    tool_call_id=prepared.event_tool_call_id,
                    stream=cast(ToolOutputStream, stream),
                    chunk=chunk,
                ),
            )
        )

    try:
        if prepared.policy_decision.requires_approval or confirmed:
            execution_result = await tool_runtime.execute_approved(
                prepared,
                on_output_chunk=record_chunk,
            )
        else:
            execution_result = await tool_runtime.execute(
                prepared,
                on_output_chunk=record_chunk,
            )
    except Exception as exc:
        failure_retry = classify_tool_attempt_retry(
            status=ToolAttemptStatus.FAILED,
            tool_name=prepared.tool_name,
            tool_spec=prepared.tool.spec,
            arguments=prepared.validated_arguments,
            policy_decision=prepared.policy_decision,
        )
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolAttemptHeartbeat(
                        tool_attempt_id=retry_attempt_id,
                        status=ToolAttemptStatus.FAILED,
                        turn_id=original.turn_id,
                        tool_call_id=prepared.event_tool_call_id,
                        task_id=original.task_id,
                        tool_name=prepared.tool_name,
                        message=str(exc),
                        safe_to_retry=failure_retry.safe_to_retry,
                        retry_classification=failure_retry.classification,
                        retry_requires_approval=failure_retry.requires_approval,
                        retry_reason=failure_retry.reason,
                        retry_policy_reason=failure_retry.policy_reason,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=original.turn_id,
                        tool_call_id=prepared.event_tool_call_id,
                        success=False,
                        summary=str(exc),
                    ),
                ),
            ]
        )
        failed_attempt = repository.get_tool_attempt(session_id, retry_attempt_id)
        if failed_attempt is None:
            raise ToolAttemptRecoveryError(
                "failed retry projection is unavailable"
            ) from exc
        return failed_attempt

    output_artifact_id = record_retry_output_artifact(
        artifact_repository,
        session_id,
        original,
        execution_result.event_tool_call_id,
        prepared.tool_name,
        execution_result.output_payload,
    )
    final_status = (
        ToolAttemptStatus.SUCCEEDED
        if execution_result.success
        else ToolAttemptStatus.FAILED
    )
    final_retry = classify_tool_attempt_retry(
        status=final_status,
        tool_name=prepared.tool_name,
        tool_spec=prepared.tool.spec,
        arguments=prepared.validated_arguments,
        output_payload=execution_result.output_payload,
        policy_decision=prepared.policy_decision,
    )
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=retry_attempt_id,
                    status=final_status,
                    turn_id=original.turn_id,
                    tool_call_id=execution_result.event_tool_call_id,
                    task_id=original.task_id,
                    tool_name=prepared.tool_name,
                    message=execution_result.summary,
                    output_artifact_id=output_artifact_id,
                    safe_to_retry=final_retry.safe_to_retry,
                    retry_classification=final_retry.classification,
                    retry_requires_approval=final_retry.requires_approval,
                    retry_reason=final_retry.reason,
                    retry_policy_reason=final_retry.policy_reason,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolExecutionCompleted(
                    turn_id=original.turn_id,
                    tool_call_id=execution_result.event_tool_call_id,
                    success=execution_result.success,
                    exit_code=execution_result.exit_code,
                    summary=execution_result.summary,
                ),
            ),
        ]
    )
    retry_attempt = repository.get_tool_attempt(session_id, retry_attempt_id)
    if retry_attempt is None:
        raise ToolAttemptRecoveryError("retry attempt projection is unavailable")
    return retry_attempt


def record_retry_requested(
    repository: SessionRepository,
    session_id: SessionId,
    original: ToolAttemptRecord,
    *,
    retry_attempt_id: ToolAttemptId,
    requested_by: str,
    reason: str | None,
) -> None:
    """Mark the original attempt as retried before executing replacement work."""

    recovery_reason = reason or f"retry requested for {original.tool_attempt_id}"
    retry_assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.RETRIED,
        tool_name=original.tool_name,
    )
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RecoveryDecisionRecorded(
                    recovery_decision_id=new_recovery_decision_id(),
                    decision=RecoveryDecision.RETRY,
                    reason=recovery_reason,
                    safe_to_resume=True,
                    next_action=f"inspect retry attempt {retry_attempt_id}",
                    turn_id=original.turn_id,
                    tool_attempt_id=original.tool_attempt_id,
                    decided_by=requested_by,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=original.tool_attempt_id,
                    status=ToolAttemptStatus.RETRIED,
                    turn_id=original.turn_id,
                    tool_call_id=original.tool_call_id,
                    task_id=original.task_id,
                    tool_name=original.tool_name,
                    message=f"Retry requested by {requested_by}: {recovery_reason}",
                    output_artifact_id=original.output_artifact_id,
                    safe_to_retry=retry_assessment.safe_to_retry,
                    retry_classification=retry_assessment.classification,
                    retry_requires_approval=retry_assessment.requires_approval,
                    retry_reason=retry_assessment.reason,
                    retry_policy_reason=retry_assessment.policy_reason,
                ),
            ),
        ]
    )


def ensure_retry_allowed(
    attempt: ToolAttemptRecord,
    *,
    confirmed: bool,
) -> None:
    """Validate retry eligibility and operator confirmation posture."""

    if attempt.status in {
        ToolAttemptStatus.STARTED,
        ToolAttemptStatus.RUNNING,
        ToolAttemptStatus.WAITING,
    }:
        raise ToolAttemptRecoveryError(
            f"attempt {attempt.tool_attempt_id} is still active; inspect or wait "
            "before retrying"
        )
    if attempt.status in {
        ToolAttemptStatus.SUCCEEDED,
        ToolAttemptStatus.RETRIED,
        ToolAttemptStatus.ABANDONED,
    }:
        raise ToolAttemptRecoveryError(
            f"attempt {attempt.tool_attempt_id} is {attempt.status.value} and "
            "cannot be retried"
        )
    if attempt.retry_classification is ToolAttemptRetryClassification.UNSAFE_TO_RETRY:
        raise ToolAttemptRecoveryError(
            attempt.retry_reason
            or f"attempt {attempt.tool_attempt_id} is unsafe to retry"
        )
    if attempt.retry_requires_approval and not confirmed:
        raise ToolAttemptRecoveryError(
            "retry requires explicit confirmation; rerun with --yes after "
            "inspecting retained evidence"
        )


__all__ = [
    "ensure_retry_allowed",
    "execute_retry_attempt",
    "record_retry_requested",
    "retry_tool_attempt",
]
