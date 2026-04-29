"""Unit tests for Glassbox core Pydantic models."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from glassbox.core import AutonomyBudget
from glassbox.core import ForkedSession
from glassbox.core import InheritedTranscriptMessage
from glassbox.core import MessagePart
from glassbox.core import PolicyDecision
from glassbox.core import ResolvedForkPoint
from glassbox.core import SessionConfig
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import TaskStepRecord
from glassbox.core import TaskStepStatus
from glassbox.core import TaskVerificationRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import ToolCallRecord
from glassbox.core import ToolExecutionStatus
from glassbox.core import TranscriptMessage
from glassbox.core import new_approval_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id


def test_session_config_round_trip() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config
    assert restored.approval_mode == "confirm"
    assert restored.dashboard_url is None


def test_session_config_round_trip_preserves_dashboard_url() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
        dashboard_url="http://127.0.0.1:8765/",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config
    assert restored.dashboard_url == "http://127.0.0.1:8765/"


def test_session_config_round_trip_preserves_lineage_metadata() -> None:
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=12,
        branch_label="investigate-alt-path",
    )

    restored = SessionConfig.model_validate(config.model_dump(mode="python"))

    assert restored == config


def test_session_record_round_trip_preserves_lineage_metadata() -> None:
    record = SessionRecord(
        session_id=new_session_id(),
        status=SessionStatus.RUNNING,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
        updated_at=datetime(2026, 4, 16, 0, 5, tzinfo=UTC),
        cwd=Path("/tmp/glassbox"),
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        last_sequence=4,
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=3,
        branch_label="alt-branch",
    )

    restored = SessionRecord.model_validate(record.model_dump(mode="python"))

    assert restored == record


def test_session_state_round_trip() -> None:
    state = SessionState(
        session_id=new_session_id(),
        status=SessionStatus.RUNNING,
        current_turn_id=new_turn_id(),
        last_sequence=5,
        pending_approval_id=new_approval_id(),
    )

    restored = SessionState.model_validate(state.model_dump(mode="python"))

    assert restored == state


def test_transcript_message_round_trip() -> None:
    message = TranscriptMessage(
        message_id=new_message_id(),
        role="assistant",
        parts=[MessagePart(kind="text", text="hello")],
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    restored = TranscriptMessage.model_validate(message.model_dump(mode="python"))

    assert restored == message


def test_resolved_fork_point_round_trip() -> None:
    fork_point = ResolvedForkPoint(
        parent_session_id=new_session_id(),
        turn_id=new_turn_id(),
        sequence=8,
        inherited_messages=[
            InheritedTranscriptMessage(
                source_message_id=new_message_id(),
                source_turn_id=new_turn_id(),
                role="assistant",
                parts=[MessagePart(kind="text", text="prior answer")],
                created_at=datetime(2026, 4, 16, 12, 4, tzinfo=UTC),
            )
        ],
    )

    restored = ResolvedForkPoint.model_validate(fork_point.model_dump(mode="python"))

    assert restored == fork_point


def test_forked_session_round_trip() -> None:
    forked_session = ForkedSession(
        child_session_id=new_session_id(),
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=11,
        branch_label="alt-branch",
        inherited_message_count=2,
        last_sequence=3,
    )

    restored = ForkedSession.model_validate(forked_session.model_dump(mode="python"))

    assert restored == forked_session


def test_tool_call_record_round_trip() -> None:
    record = ToolCallRecord(
        tool_call_id=new_tool_call_id(),
        turn_id=new_turn_id(),
        tool_name="read_file",
        status=ToolExecutionStatus.REQUESTED,
        summary="Queued for execution",
    )

    restored = ToolCallRecord.model_validate(record.model_dump(mode="python"))

    assert restored == record


def test_policy_decision_round_trip() -> None:
    decision = PolicyDecision(
        allowed=True,
        requires_approval=False,
        reason="Read-only operation within workspace",
        outcome="allow",
        risk_level="read_only",
        source_kind="default",
        source_label="read_only",
    )

    restored = PolicyDecision.model_validate(decision.model_dump(mode="python"))

    assert restored == decision


def test_autonomy_budget_rejects_contradictory_risk_limits() -> None:
    with pytest.raises(ValidationError):
        AutonomyBudget(
            max_steps=4,
            max_tool_calls=10,
            max_write_operations=1,
            max_command_operations=0,
            max_wall_clock_seconds=300,
            max_verification_attempts=1,
            max_branch_attempts=0,
            max_artifact_bytes=1000,
            allowed_risk_buckets=["read_only"],
        )

    with pytest.raises(ValidationError):
        AutonomyBudget(
            max_steps=4,
            max_tool_calls=10,
            max_write_operations=0,
            max_command_operations=0,
            max_wall_clock_seconds=300,
            max_verification_attempts=1,
            max_branch_attempts=0,
            max_artifact_bytes=1000,
            allowed_risk_buckets=["read_only", "command"],
        )


def test_task_plan_snapshot_round_trip() -> None:
    task_id = new_task_id()
    step_id = new_task_step_id()
    plan = TaskPlanSnapshot(
        task_id=task_id,
        title="Add task models",
        goal="Make task plans durable",
        steps=[
            TaskStepProposal(
                step_id=step_id,
                title="Define event payloads",
                description="Add core task-plan event payloads",
                order=0,
            )
        ],
    )

    restored = TaskPlanSnapshot.model_validate(plan.model_dump(mode="python"))

    assert restored == plan
    assert restored.status == "proposed"


def test_task_query_records_round_trip() -> None:
    task_id = new_task_id()
    step_id = new_task_step_id()
    step = TaskStepRecord(
        task_id=task_id,
        step_id=step_id,
        title="Define projection",
        order=1,
        status=TaskStepStatus.PENDING,
        blocked_reason=TaskBlockedReason.AWAITING_APPROVAL,
    )
    verification = TaskVerificationRecord(
        task_id=task_id,
        verification_id=new_task_verification_id(),
        step_id=step_id,
        status=TaskVerificationStatus.PLANNED,
        check_name="pytest",
    )

    assert TaskStepRecord.model_validate(step.model_dump(mode="python")) == step
    assert (
        TaskVerificationRecord.model_validate(verification.model_dump(mode="python"))
        == verification
    )


def test_task_step_proposal_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        TaskStepProposal(
            step_id=new_task_step_id(),
            title="",
            order=0,
        )


def test_session_state_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        SessionState.model_validate(
            {
                "session_id": new_session_id(),
                "status": "paused",
            }
        )


def test_session_state_rejects_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        SessionState(
            session_id=new_session_id(),
            status=SessionStatus.IDLE,
            last_sequence=-1,
        )


def test_message_part_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        MessagePart.model_validate({"kind": "markdown", "text": "hello"})


def test_transcript_message_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        TranscriptMessage.model_validate(
            {
                "message_id": new_message_id(),
                "role": "tool",
                "parts": [{"kind": "text", "text": "hello"}],
                "created_at": datetime(2026, 4, 16, tzinfo=UTC),
            }
        )


def test_session_config_rejects_invalid_approval_mode() -> None:
    with pytest.raises(ValidationError):
        SessionConfig(
            model_name="openai:gpt-5.4",
            cwd=Path("/tmp/glassbox"),
            approval_mode="invalid-mode",
        )


def test_session_config_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SessionConfig.model_validate(
            {
                "model_name": "openai:gpt-5.4",
                "cwd": "/tmp/glassbox",
                "approval_mode": "confirm",
                "unexpected": True,
            }
        )
