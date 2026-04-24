"""Unit tests for Glassbox core event models."""

from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from glassbox.core import (
    ApprovalDecision,
    ApprovalRequested,
    ApprovalResolved,
    AssistantMessageCompleted,
    ErrorRecorded,
    EventEnvelope,
    EventPayloadType,
    MessagePart,
    SessionStarted,
    ToolOutputChunk,
    TranscriptMessageImported,
    TurnStatus,
    TurnStatusChanged,
    UserMessageReceived,
    new_approval_id,
    new_message_id,
    new_session_id,
    new_tool_call_id,
    new_turn_id,
)


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
