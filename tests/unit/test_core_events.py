"""Unit tests for Glassbox core event models."""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from glassbox.core import ApprovalDecision
from glassbox.core import ApprovalRequested
from glassbox.core import ApprovalResolved
from glassbox.core import AssistantMessageCompleted
from glassbox.core import CancellationAcknowledged
from glassbox.core import CancellationFailed
from glassbox.core import CancellationRequested
from glassbox.core import ErrorRecorded
from glassbox.core import EventEnvelope
from glassbox.core import EventPayloadType
from glassbox.core import MessagePart
from glassbox.core import SessionStarted
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskCreated
from glassbox.core import TaskPaused
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepCompleted
from glassbox.core import TaskStepFailed
from glassbox.core import TaskStepStarted
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationStarted
from glassbox.core import ToolOutputChunk
from glassbox.core import TranscriptMessageImported
from glassbox.core import TurnCancelled
from glassbox.core import TurnStatus
from glassbox.core import TurnStatusChanged
from glassbox.core import UserMessageReceived
from glassbox.core import new_approval_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id


def test_event_envelope_round_trip() -> None:
    payload = SessionStarted(
        cwd="/tmp/glassbox",
        dashboard_url="http://127.0.0.1:8765",
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=7,
        branch_label="alt-branch",
    )
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=1,
        payload=payload,
    )

    restored = EventEnvelope.model_validate(envelope.model_dump(mode="python"))

    assert restored == envelope
    assert restored.event_type == "SessionStarted"
    assert restored.event_version == 1


def test_session_started_payload_remains_backward_compatible_without_lineage() -> None:
    payload = SessionStarted.model_validate(
        {
            "event_type": "SessionStarted",
            "cwd": "/tmp/glassbox",
            "model_name": "openai:gpt-5.4",
            "approval_mode": "confirm",
        }
    )

    assert payload.parent_session_id is None
    assert payload.forked_from_turn_id is None
    assert payload.forked_from_sequence is None
    assert payload.branch_label is None


def test_event_envelope_populates_event_type_from_payload() -> None:
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=2,
        payload=UserMessageReceived(
            message_id=new_message_id(),
            text="Inspect the repository",
        ),
    )

    assert envelope.event_type == "UserMessageReceived"
    assert envelope.message_id is not None


def test_event_envelope_rejects_mismatched_event_type() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {
                "session_id": new_session_id(),
                "sequence": 3,
                "event_type": "SessionCompleted",
                "payload": {
                    "event_type": "SessionStarted",
                    "cwd": "/tmp/glassbox",
                    "model_name": "openai:gpt-5.4",
                    "approval_mode": "confirm",
                },
            }
        )


def test_event_payload_union_validates_representative_payloads() -> None:
    adapter = TypeAdapter(EventPayloadType)

    tool_chunk = adapter.validate_python(
        {
            "event_type": "ToolOutputChunk",
            "turn_id": new_turn_id(),
            "tool_call_id": new_tool_call_id(),
            "stream": "stdout",
            "chunk": "hello\n",
        }
    )
    approval_resolved = adapter.validate_python(
        {
            "event_type": "ApprovalResolved",
            "approval_id": new_approval_id(),
            "decision": "approved",
            "decided_by": "user",
        }
    )

    assert isinstance(tool_chunk, ToolOutputChunk)
    assert isinstance(approval_resolved, ApprovalResolved)
    assert approval_resolved.decision == ApprovalDecision.APPROVED


def test_event_payload_union_rejects_unknown_event_type() -> None:
    adapter = TypeAdapter(EventPayloadType)

    with pytest.raises(ValidationError):
        adapter.validate_python({"event_type": "UnknownEvent"})


def test_turn_status_changed_uses_shared_turn_status_type() -> None:
    payload = TurnStatusChanged(
        turn_id=new_turn_id(),
        status=TurnStatus.EXECUTING_TOOL,
    )

    assert payload.status == TurnStatus.EXECUTING_TOOL


def test_cancellation_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()

    requested = adapter.validate_python(
        {
            "event_type": "CancellationRequested",
            "turn_id": turn_id,
            "requested_by": "terminal",
            "reason": "operator pressed Ctrl+C",
        }
    )
    acknowledged = adapter.validate_python(
        {
            "event_type": "CancellationAcknowledged",
            "turn_id": turn_id,
            "repeated": True,
        }
    )
    turn_cancelled = adapter.validate_python(
        {
            "event_type": "TurnCancelled",
            "turn_id": turn_id,
            "reason": "operator requested cancellation",
            "stage": "model_call",
        }
    )
    tool_cancelled = adapter.validate_python(
        {
            "event_type": "ToolExecutionCancelled",
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "summary": "cancelled by operator",
        }
    )
    failed = adapter.validate_python(
        {
            "event_type": "CancellationFailed",
            "turn_id": turn_id,
            "reason": "turn already completed",
        }
    )

    assert isinstance(requested, CancellationRequested)
    assert isinstance(acknowledged, CancellationAcknowledged)
    assert isinstance(turn_cancelled, TurnCancelled)
    assert tool_cancelled.tool_call_id == tool_call_id
    assert isinstance(failed, CancellationFailed)


def test_turn_cancelled_rejects_unknown_stage() -> None:
    with pytest.raises(ValidationError):
        TurnCancelled.model_validate(
            {
                "event_type": "TurnCancelled",
                "turn_id": new_turn_id(),
                "reason": "operator requested cancellation",
                "stage": "approval_queue",
            }
        )


def test_assistant_message_completed_uses_message_parts() -> None:
    payload = AssistantMessageCompleted(
        message_id=new_message_id(),
        parts=[MessagePart(kind="text", text="done")],
    )

    assert payload.parts[0].kind == "text"


def test_event_envelope_exposes_correlation_fields() -> None:
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=4,
        payload=ApprovalRequested(
            approval_id=approval_id,
            turn_id=turn_id,
            reason="Command writes files",
            subject="apply_patch",
        ),
    )

    assert envelope.turn_id == turn_id
    assert envelope.approval_id == approval_id


def test_error_recorded_rejects_invalid_scope() -> None:
    with pytest.raises(ValidationError):
        ErrorRecorded.model_validate(
            {
                "event_type": "ErrorRecorded",
                "scope": "worker",
                "message": "bad scope",
            }
        )


def test_event_envelope_preserves_created_at() -> None:
    created_at = datetime(2026, 4, 16, tzinfo=UTC)
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=5,
        created_at=created_at,
        payload=UserMessageReceived(
            message_id=new_message_id(),
            text="hello",
        ),
    )

    assert envelope.created_at == created_at


def test_transcript_message_imported_round_trip() -> None:
    payload = TranscriptMessageImported(
        message_id=new_message_id(),
        source_session_id=new_session_id(),
        source_message_id=new_message_id(),
        source_turn_id=new_turn_id(),
        role="assistant",
        parts=[MessagePart(kind="text", text="imported answer")],
        source_created_at=datetime(2026, 4, 16, 12, 4, tzinfo=UTC),
    )
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=6,
        payload=payload,
    )

    restored = EventEnvelope.model_validate(envelope.model_dump(mode="python"))

    assert restored == envelope
    assert restored.message_id == payload.message_id


def test_task_plan_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    step_id = new_task_step_id()
    verification_id = new_task_verification_id()

    created = adapter.validate_python(
        {
            "event_type": "TaskCreated",
            "task_id": task_id,
            "title": "Implement task models",
            "goal": "Persist durable task-plan payloads",
            "source_turn_id": new_turn_id(),
        }
    )
    proposed = adapter.validate_python(
        {
            "event_type": "TaskPlanProposed",
            "task_id": task_id,
            "plan": {
                "task_id": task_id,
                "title": "Implement task models",
                "goal": "Persist durable task-plan payloads",
                "steps": [
                    {
                        "step_id": step_id,
                        "title": "Add core events",
                        "order": 0,
                    }
                ],
            },
        }
    )
    step_started = adapter.validate_python(
        {
            "event_type": "TaskStepStarted",
            "task_id": task_id,
            "step_id": step_id,
            "turn_id": new_turn_id(),
        }
    )
    step_completed = adapter.validate_python(
        {
            "event_type": "TaskStepCompleted",
            "task_id": task_id,
            "step_id": step_id,
            "summary": "Core events added",
        }
    )
    verification_started = adapter.validate_python(
        {
            "event_type": "TaskVerificationStarted",
            "task_id": task_id,
            "verification_id": verification_id,
            "step_id": step_id,
            "check_name": "pytest",
        }
    )
    verification_completed = adapter.validate_python(
        {
            "event_type": "TaskVerificationCompleted",
            "task_id": task_id,
            "verification_id": verification_id,
            "status": "passed",
            "summary": "Focused tests passed",
        }
    )

    assert isinstance(created, TaskCreated)
    assert isinstance(proposed, TaskPlanProposed)
    assert proposed.plan.steps[0].step_id == step_id
    assert isinstance(step_started, TaskStepStarted)
    assert isinstance(step_completed, TaskStepCompleted)
    assert isinstance(verification_started, TaskVerificationStarted)
    assert isinstance(verification_completed, TaskVerificationCompleted)


def test_task_plan_event_envelope_exposes_task_id() -> None:
    task_id = new_task_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=7,
        payload=TaskPaused(task_id=task_id, reason=TaskBlockedReason.MANUAL_PAUSE),
    )

    assert envelope.task_id == task_id


def test_task_plan_proposal_rejects_mismatched_task_id() -> None:
    with pytest.raises(ValidationError):
        TaskPlanProposed(
            task_id=new_task_id(),
            plan=TaskPlanSnapshot(
                task_id=new_task_id(),
                title="Mismatch",
                goal="Should be rejected",
                steps=[],
            ),
        )


def test_task_step_failure_rejects_unknown_blocked_reason() -> None:
    with pytest.raises(ValidationError):
        TaskStepFailed.model_validate(
            {
                "event_type": "TaskStepFailed",
                "task_id": new_task_id(),
                "step_id": new_task_step_id(),
                "reason": "blocked",
                "blocked_reason": "approval_queue",
            }
        )
