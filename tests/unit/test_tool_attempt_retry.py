"""Tests for durable tool-attempt retry classification."""

from pathlib import Path

from glassbox.core import CommandPurpose
from glassbox.core import CommandReviewRelevance
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core.models import PolicyDecision
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.tool_attempts import classify_tool_attempt_retry
from glassbox.runtime.turn_tool_attempt_heartbeats import build_tool_attempt_heartbeat
from glassbox.tools import PreparedToolExecution
from glassbox.tools.command import RunCommandArgs
from glassbox.tools.command import RunCommandResult
from glassbox.tools.command import RunCommandTool
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec

RUN_COMMAND_SPEC = ToolSpec(
    name="run_command",
    description="Run a command.",
    input_model=RunCommandArgs,
    output_model=RunCommandResult,
    risk_level=ToolRiskLevel.COMMAND,
    command_argument_name="command",
)


def _policy_decision(*, requires_approval: bool = True) -> PolicyDecision:
    return PolicyDecision(
        allowed=True,
        requires_approval=requires_approval,
        reason="command retry requires confirmation",
        outcome="approve" if requires_approval else "allow",
        risk_level="command",
        source_kind="default",
        source_label="command",
    )


def test_running_attempt_is_already_running_and_not_retryable() -> None:
    assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.RUNNING,
        tool_name="run_command",
        tool_spec=RUN_COMMAND_SPEC,
        arguments=RunCommandArgs(command="uv run pytest", cwd="."),
        policy_decision=_policy_decision(),
    )

    assert assessment.classification == ToolAttemptRetryClassification.ALREADY_RUNNING
    assert assessment.safe_to_retry is False
    assert assessment.requires_approval is False
    assert "still active" in assessment.reason


def test_failed_pytest_command_is_idempotent_but_approval_gated() -> None:
    assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.FAILED,
        tool_name="run_command",
        tool_spec=RUN_COMMAND_SPEC,
        arguments=RunCommandArgs(command="uv run pytest tests/unit", cwd="."),
        output_payload={"failure_category": "execution_error"},
        policy_decision=_policy_decision(),
    )

    assert assessment.classification == ToolAttemptRetryClassification.IDEMPOTENT
    assert assessment.safe_to_retry is True
    assert assessment.requires_approval is True
    assert assessment.policy_reason == "command retry requires confirmation"
    assert "pytest command is verification-only" in assessment.reason


def test_unknown_failed_command_requires_approval_without_claiming_safety() -> None:
    assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.FAILED,
        tool_name="run_command",
        tool_spec=RUN_COMMAND_SPEC,
        arguments=RunCommandArgs(command="python scripts/custom_migration.py", cwd="."),
        output_payload={"failure_category": "execution_error"},
        policy_decision=_policy_decision(requires_approval=False),
    )

    assert assessment.classification == ToolAttemptRetryClassification.UNKNOWN
    assert assessment.safe_to_retry is None
    assert assessment.requires_approval is True
    assert "side effects are unknown" in assessment.reason


def test_destructive_command_is_unsafe_to_retry() -> None:
    assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.STALE,
        tool_name="run_command",
        tool_spec=RUN_COMMAND_SPEC,
        arguments=RunCommandArgs(command="rm -rf build", cwd="."),
        policy_decision=_policy_decision(),
    )

    assert assessment.classification == ToolAttemptRetryClassification.UNSAFE_TO_RETRY
    assert assessment.safe_to_retry is False
    assert assessment.requires_approval is False
    assert "can mutate" in assessment.reason


def test_read_only_tool_failure_is_retryable_without_approval() -> None:
    spec = ToolSpec(
        name="read_file",
        description="Read a file.",
        input_model=RunCommandArgs,
        output_model=RunCommandResult,
        risk_level=ToolRiskLevel.READ_ONLY,
    )

    assessment = classify_tool_attempt_retry(
        status=ToolAttemptStatus.FAILED,
        tool_name="read_file",
        tool_spec=spec,
        arguments=RunCommandArgs(command="ignored", cwd=str(Path("."))),
    )

    assert assessment.classification == ToolAttemptRetryClassification.RETRYABLE
    assert assessment.safe_to_retry is True
    assert assessment.requires_approval is False


def test_tool_attempt_heartbeat_records_command_purpose() -> None:
    command_tool = RunCommandTool(Path("."))
    prepared = PreparedToolExecution(
        event_tool_call_id=new_tool_call_id(),
        provider_tool_call_id="provider-call",
        tool_name="run_command",
        tool=command_tool,
        validated_arguments=RunCommandArgs(command="uv run pytest", cwd="."),
        policy_decision=_policy_decision(),
    )

    heartbeat = build_tool_attempt_heartbeat(
        tool_attempt_id=new_tool_attempt_id(),
        status=ToolAttemptStatus.FAILED,
        turn_id=new_turn_id(),
        prepared_tool_call=prepared,
        message="pytest failed",
    )

    assert heartbeat.command_purpose == CommandPurpose.TEST
    assert heartbeat.command_review_relevance == CommandReviewRelevance.VERIFICATION
    assert heartbeat.command_supports_verification is True
    assert heartbeat.command_purpose_reason is not None
    assert heartbeat.command_environment is not None
    assert heartbeat.command_environment.command_purpose == CommandPurpose.TEST
