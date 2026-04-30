"""Long-running lifecycle projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import EventEnvelope
from glassbox.core.events import LongRunPhaseChanged
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ResumeOutcomeRecorded
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolAttemptHeartbeat

_LONG_RUN_EVENT_TYPES = (
    LongRunPhaseChanged,
    TaskCheckpointCreated,
    ContextCompactionCreated,
    ToolAttemptHeartbeat,
    RecoveryDecisionRecorded,
    ResumeOutcomeRecorded,
)


def _apply_long_run_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if not isinstance(payload, _LONG_RUN_EVENT_TYPES):
        return

    connection.execute(
        """
        insert or replace into long_run_events (
            session_id,
            sequence,
            event_type,
            task_id,
            turn_id,
            tool_call_id,
            tool_attempt_id,
            checkpoint_id,
            compaction_id,
            recovery_decision_id,
            phase,
            status,
            summary,
            created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(event.session_id),
            event.sequence,
            event.event_type,
            _optional_text(event.task_id),
            _optional_text(event.turn_id),
            _optional_text(event.tool_call_id),
            _optional_text(event.tool_attempt_id),
            _optional_text(event.checkpoint_id),
            _optional_text(event.compaction_id),
            _optional_text(event.recovery_decision_id),
            _phase_for_payload(payload),
            _status_for_payload(payload),
            _summary_for_payload(payload),
            event.created_at.isoformat(),
        ),
    )


def _phase_for_payload(payload) -> str | None:
    phase = getattr(payload, "phase", None)
    return getattr(phase, "value", phase)


def _status_for_payload(payload) -> str | None:
    for attribute_name in ("state", "status", "freshness", "decision", "outcome"):
        value = getattr(payload, attribute_name, None)
        if value is not None:
            return getattr(value, "value", value)
    return None


def _summary_for_payload(payload) -> str | None:
    for attribute_name in (
        "summary",
        "message",
        "next_action",
        "recovery_guidance",
        "reason",
    ):
        value = getattr(payload, attribute_name, None)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["_apply_long_run_projection"]
