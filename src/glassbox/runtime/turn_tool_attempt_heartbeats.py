"""Tool-attempt heartbeat construction for turn tool execution."""

from datetime import datetime

from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.command_evidence import command_attempt_evidence
from glassbox.runtime.tool_attempts import classify_tool_attempt_retry
from glassbox.tools import PreparedToolExecution


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
    command_evidence = command_attempt_evidence(
        prepared_tool_call.tool.spec,
        prepared_tool_call.validated_arguments.model_dump(mode="python"),
    )
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
        command_purpose=command_evidence.purpose,
        command_review_relevance=command_evidence.review_relevance,
        command_supports_verification=command_evidence.supports_verification,
        command_purpose_reason=command_evidence.reason,
        command_environment=command_evidence.environment,
    )


__all__ = ["build_tool_attempt_heartbeat"]
