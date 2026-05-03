"""Tool-attempt heartbeat construction for turn tool execution."""

from datetime import datetime

from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.command_evidence import classify_command_purpose
from glassbox.runtime.tool_attempts import classify_tool_attempt_retry
from glassbox.tools import PreparedToolExecution
from glassbox.tools.policy_command_risk import command_text


def build_tool_attempt_heartbeat(
    *,
    tool_attempt_id: ToolAttemptId,
    status: ToolAttemptStatus,
    turn_id: TurnId,
    prepared_tool_call: PreparedToolExecution,
    message: str,
    tool_call_id: ToolCallId | None = None,
    heartbeat_expires_at: datetime | None = None,
    output_artifact_id: ArtifactId | None = None,
    output_payload: dict[str, object] | None = None,
) -> ToolAttemptHeartbeat:
    """Build a classified heartbeat for one prepared tool execution state."""

    retry_assessment = classify_tool_attempt_retry(
        status=status,
        tool_name=prepared_tool_call.tool_name,
        tool_spec=prepared_tool_call.tool.spec,
        arguments=prepared_tool_call.validated_arguments,
        output_payload=output_payload,
        policy_decision=prepared_tool_call.policy_decision,
    )
    command_assessment = None
    command = command_text(
        prepared_tool_call.tool.spec,
        prepared_tool_call.validated_arguments.model_dump(mode="python"),
    )
    if command is not None:
        command_assessment = classify_command_purpose(command)
    return ToolAttemptHeartbeat(
        tool_attempt_id=tool_attempt_id,
        status=status,
        turn_id=turn_id,
        tool_call_id=tool_call_id or prepared_tool_call.event_tool_call_id,
        tool_name=prepared_tool_call.tool_name,
        message=message,
        heartbeat_expires_at=heartbeat_expires_at,
        output_artifact_id=output_artifact_id,
        safe_to_retry=retry_assessment.safe_to_retry,
        retry_classification=retry_assessment.classification,
        retry_requires_approval=retry_assessment.requires_approval,
        retry_reason=retry_assessment.reason,
        retry_policy_reason=retry_assessment.policy_reason,
        command_purpose=(
            command_assessment.purpose if command_assessment is not None else None
        ),
        command_review_relevance=(
            command_assessment.review_relevance
            if command_assessment is not None
            else None
        ),
        command_supports_verification=(
            command_assessment.supports_verification
            if command_assessment is not None
            else None
        ),
        command_purpose_reason=(
            command_assessment.reason if command_assessment is not None else None
        ),
    )


__all__ = ["build_tool_attempt_heartbeat"]
