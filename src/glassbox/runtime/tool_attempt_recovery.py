"""Durable recovery actions for v10 tool attempts."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import BaseModel

from glassbox.core import ApprovalMode
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import ToolOutputStream
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.tool_attempts import classify_tool_attempt_retry
from glassbox.runtime.turn_event_recorder import _tool_output_artifact_content
from glassbox.runtime.turn_event_recorder import _tool_output_artifact_kind
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import build_ask_user_tool_registry
from glassbox.tools.policy import ToolPolicyContext
from glassbox.tools.policy import ToolPolicyEngine
from glassbox.tools.policy_config import load_tool_policy_manifest
from glassbox.tools.runtime import PreparedToolExecution
from glassbox.tools.runtime import ToolCallRequest
from glassbox.tools.runtime import ToolRuntime


class ToolAttemptRecoveryError(ValueError):
    """Raised when a tool-attempt recovery action is unsafe or impossible."""


class ToolAttemptArtifactReference(BaseModel):
    """Operator-facing pointer to retained output evidence."""

    artifact_id: ArtifactId
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = None


class ToolAttemptInspection(BaseModel):
    """Inspect result for one durable tool attempt."""

    attempt: ToolAttemptRecord
    source_tool_call_id: ToolCallId | None = None
    source_arguments: dict[str, object] | None = None
    output_artifact: ToolAttemptArtifactReference | None = None
    correlated_event_count: int
    recovery_actions: list[str]


class ToolAttemptRecoveryResult(BaseModel):
    """Result returned by retry and abandon recovery actions."""

    message: str
    original_attempt: ToolAttemptRecord
    retry_attempt: ToolAttemptRecord | None = None


@dataclass(frozen=True, slots=True)
class _RecoveredToolCallRequest:
    tool_name: str
    arguments: dict[str, object]
    tool_call_id: str


def inspect_tool_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> ToolAttemptInspection:
    """Return one attempt with retained source arguments and output evidence."""

    attempt = _require_attempt(repository, session_id, tool_attempt_id)
    source_payload = _source_tool_call_payload(repository, session_id, attempt)
    source_arguments = (
        _decode_arguments_json(source_payload.arguments_json)
        if source_payload is not None
        else None
    )
    artifact = _artifact_reference(repository, session_id, attempt.output_artifact_id)
    correlated_events = _correlated_attempt_events(repository, session_id, attempt)
    return ToolAttemptInspection(
        attempt=attempt,
        source_tool_call_id=attempt.tool_call_id,
        source_arguments=source_arguments,
        output_artifact=artifact,
        correlated_event_count=len(correlated_events),
        recovery_actions=_recovery_actions(attempt, artifact),
    )


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

    original = _require_attempt(repository, session_id, tool_attempt_id)
    _ensure_retry_allowed(original, confirmed=confirmed)
    source_payload = _source_tool_call_payload(repository, session_id, original)
    if source_payload is None:
        raise ToolAttemptRecoveryError(
            "tool attempt cannot be retried because its source tool-call arguments "
            "were not retained"
        )
    arguments = _decode_arguments_json(source_payload.arguments_json)
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
            _RecoveredToolCallRequest(
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
    _record_retry_requested(
        repository,
        session_id,
        original,
        retry_attempt_id=retry_attempt_id,
        requested_by=requested_by,
        reason=reason,
    )
    retry_attempt = await _execute_retry_attempt(
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


def abandon_tool_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
    *,
    reason: str,
    abandoned_by: str = "operator",
) -> ToolAttemptRecoveryResult:
    """Mark a stale or failed attempt as intentionally abandoned."""

    attempt = _require_attempt(repository, session_id, tool_attempt_id)
    if attempt.status in {
        ToolAttemptStatus.SUCCEEDED,
        ToolAttemptStatus.ABANDONED,
        ToolAttemptStatus.RETRIED,
    }:
        raise ToolAttemptRecoveryError(
            f"attempt {tool_attempt_id} is {attempt.status.value} "
            "and cannot be abandoned"
        )
    if attempt.status in {
        ToolAttemptStatus.STARTED,
        ToolAttemptStatus.RUNNING,
        ToolAttemptStatus.WAITING,
    }:
        raise ToolAttemptRecoveryError(
            f"attempt {tool_attempt_id} is still active; inspect or cancel it before "
            "abandoning recovery"
        )

    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RecoveryDecisionRecorded(
                    recovery_decision_id=new_recovery_decision_id(),
                    decision=RecoveryDecision.ABANDON,
                    reason=reason,
                    safe_to_resume=False,
                    next_action=(
                        "inspect retained output evidence before starting "
                        "replacement work"
                    ),
                    turn_id=attempt.turn_id,
                    tool_attempt_id=attempt.tool_attempt_id,
                    decided_by=abandoned_by,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=attempt.tool_attempt_id,
                    status=ToolAttemptStatus.ABANDONED,
                    turn_id=attempt.turn_id,
                    tool_call_id=attempt.tool_call_id,
                    task_id=attempt.task_id,
                    tool_name=attempt.tool_name,
                    message=f"Attempt abandoned by {abandoned_by}: {reason}",
                    output_artifact_id=attempt.output_artifact_id,
                    safe_to_retry=False,
                    retry_classification=ToolAttemptRetryClassification.ABANDONED,
                    retry_requires_approval=False,
                    retry_reason=(
                        "attempt was abandoned; inspect retained evidence before "
                        "starting new work"
                    ),
                ),
            ),
        ]
    )
    refreshed = repository.get_tool_attempt(session_id, tool_attempt_id)
    if refreshed is None:
        raise ToolAttemptRecoveryError("abandoned attempt projection disappeared")
    return ToolAttemptRecoveryResult(
        message=f"abandoned {tool_attempt_id}: {reason}",
        original_attempt=refreshed,
    )


def read_tool_attempt_output(
    repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> tuple[ToolAttemptArtifactReference, str]:
    """Read retained output artifact content for one attempt."""

    attempt = _require_attempt(repository, session_id, tool_attempt_id)
    artifact = _artifact_reference(repository, session_id, attempt.output_artifact_id)
    if artifact is None or artifact.path is None:
        raise ToolAttemptRecoveryError(
            f"attempt {tool_attempt_id} has no retained output artifact"
        )
    return artifact, artifact_repository.read_text_artifact(Path(artifact.path))


async def _execute_retry_attempt(
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

    def _record_chunk(stream: str, chunk: str) -> None:
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
                on_output_chunk=_record_chunk,
            )
        else:
            execution_result = await tool_runtime.execute(
                prepared,
                on_output_chunk=_record_chunk,
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

    output_artifact_id = _record_retry_output_artifact(
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


def _record_retry_requested(
    repository: SessionRepository,
    session_id: SessionId,
    original: ToolAttemptRecord,
    *,
    retry_attempt_id: ToolAttemptId,
    requested_by: str,
    reason: str | None,
) -> None:
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


def _record_retry_output_artifact(
    artifact_repository: ArtifactRepository | None,
    session_id: SessionId,
    original: ToolAttemptRecord,
    tool_call_id: ToolCallId,
    tool_name: str,
    output_payload: dict[str, object],
) -> ArtifactId | None:
    if artifact_repository is None:
        return None
    artifact_content = _tool_output_artifact_content(tool_name, output_payload)
    if artifact_content is None:
        return None
    stored_artifact, _stored_event = artifact_repository.record_text_artifact(
        session_id,
        original.turn_id,
        tool_call_id,
        _tool_output_artifact_kind(artifact_content),
        json.dumps(artifact_content, indent=2, sort_keys=True) + "\n",
        suffix="log.json",
    )
    return stored_artifact.artifact_id


def _ensure_retry_allowed(
    attempt: ToolAttemptRecord,
    *,
    confirmed: bool,
) -> None:
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


def _require_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> ToolAttemptRecord:
    attempt = repository.get_tool_attempt(session_id, tool_attempt_id)
    if attempt is None:
        raise ToolAttemptRecoveryError(
            f"tool attempt {tool_attempt_id} not found in session {session_id}"
        )
    return attempt


def _source_tool_call_payload(
    repository: SessionRepository,
    session_id: SessionId,
    attempt: ToolAttemptRecord,
) -> ModelToolCallRequested | None:
    if attempt.tool_call_id is None:
        return None
    for event in repository.read_events_by_correlation_id(
        session_id,
        tool_call_id=attempt.tool_call_id,
    ):
        if isinstance(event.payload, ModelToolCallRequested):
            return event.payload
    return None


def _artifact_reference(
    repository: SessionRepository,
    session_id: SessionId,
    artifact_id: ArtifactId | None,
) -> ToolAttemptArtifactReference | None:
    if artifact_id is None:
        return None
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if (
            isinstance(payload, ToolArtifactRecorded)
            and payload.artifact_id == artifact_id
        ):
            return ToolAttemptArtifactReference(
                artifact_id=payload.artifact_id,
                artifact_kind=payload.artifact_kind,
                path=payload.path,
                content_sha256=payload.content_sha256,
                size_bytes=payload.size_bytes,
            )
    return ToolAttemptArtifactReference(
        artifact_id=artifact_id,
        artifact_kind="unknown",
    )


def _decode_arguments_json(value: str) -> dict[str, object] | None:
    try:
        decoded: Any = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return {str(key): value for key, value in decoded.items()}


def _recovery_actions(
    attempt: ToolAttemptRecord,
    artifact: ToolAttemptArtifactReference | None,
) -> list[str]:
    actions = ["inspect"]
    if artifact is not None:
        actions.append("attach-to-output")
    if (
        attempt.status
        in {
            ToolAttemptStatus.FAILED,
            ToolAttemptStatus.CANCELLED,
            ToolAttemptStatus.STALE,
        }
        and attempt.retry_classification
        is not ToolAttemptRetryClassification.UNSAFE_TO_RETRY
    ):
        actions.append("retry")
        actions.append("abandon")
    return actions


def _correlated_attempt_events(
    repository: SessionRepository,
    session_id: SessionId,
    attempt: ToolAttemptRecord,
) -> list[EventEnvelope]:
    events_by_id = {
        event.event_id: event
        for event in repository.read_events_by_correlation_id(
            session_id,
            tool_attempt_id=attempt.tool_attempt_id,
        )
    }
    if attempt.tool_call_id is not None:
        for event in repository.read_events_by_correlation_id(
            session_id,
            tool_call_id=attempt.tool_call_id,
        ):
            events_by_id[event.event_id] = event
    return sorted(events_by_id.values(), key=lambda event: event.sequence)


__all__ = [
    "ToolAttemptArtifactReference",
    "ToolAttemptInspection",
    "ToolAttemptRecoveryError",
    "ToolAttemptRecoveryResult",
    "abandon_tool_attempt",
    "inspect_tool_attempt",
    "read_tool_attempt_output",
    "retry_tool_attempt",
]
