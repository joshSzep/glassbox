"""Abandon decisions for durable tool-attempt recovery."""

from glassbox.core.events import EventEnvelope
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.tool_attempt_recovery_common import require_attempt
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryError
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryResult
from glassbox.services import SessionRepository


def abandon_tool_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
    *,
    reason: str,
    abandoned_by: str = "operator",
) -> ToolAttemptRecoveryResult:
    """Mark a stale or failed attempt as intentionally abandoned."""

    attempt = require_attempt(repository, session_id, tool_attempt_id)
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


__all__ = ["abandon_tool_attempt"]
