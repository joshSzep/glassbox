"""Inspection summaries for durable tool-attempt recovery."""

from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.tool_attempt_recovery_artifacts import artifact_reference
from glassbox.runtime.tool_attempt_recovery_common import correlated_attempt_events
from glassbox.runtime.tool_attempt_recovery_common import decode_arguments_json
from glassbox.runtime.tool_attempt_recovery_common import require_attempt
from glassbox.runtime.tool_attempt_recovery_common import source_tool_call_payload
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptArtifactReference
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptInspection
from glassbox.services import SessionRepository


def inspect_tool_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> ToolAttemptInspection:
    """Return one attempt with retained source arguments and output evidence."""

    attempt = require_attempt(repository, session_id, tool_attempt_id)
    source_payload = source_tool_call_payload(repository, session_id, attempt)
    source_arguments = (
        decode_arguments_json(source_payload.arguments_json)
        if source_payload is not None
        else None
    )
    artifact = artifact_reference(repository, session_id, attempt.output_artifact_id)
    correlated_events = correlated_attempt_events(repository, session_id, attempt)
    return ToolAttemptInspection(
        attempt=attempt,
        source_tool_call_id=attempt.tool_call_id,
        source_arguments=source_arguments,
        output_artifact=artifact,
        correlated_event_count=len(correlated_events),
        recovery_actions=recovery_actions(attempt, artifact),
    )


def recovery_actions(
    attempt: ToolAttemptRecord,
    artifact: ToolAttemptArtifactReference | None,
) -> list[str]:
    """Return operator actions currently available for one attempt posture."""

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


__all__ = ["inspect_tool_attempt", "recovery_actions"]
