"""Task checkpoint projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskCheckpointCreated


def _apply_task_checkpoint_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if not isinstance(payload, TaskCheckpointCreated):
        return

    connection.execute(
        """
        insert or replace into task_checkpoints (
            checkpoint_id,
            session_id,
            task_id,
            turn_id,
            tool_attempt_id,
            compaction_id,
            artifact_id,
            objective,
            current_phase,
            completed_step,
            next_action,
            blockers_json,
            touched_files_json,
            verification_status,
            budget_status,
            recovery_guidance,
            source_start_sequence,
            source_end_sequence,
            created_at,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.checkpoint_id),
            str(event.session_id),
            _optional_text(payload.task_id),
            _optional_text(payload.turn_id),
            _optional_text(payload.tool_attempt_id),
            _optional_text(payload.compaction_id),
            _optional_text(payload.artifact_id),
            payload.objective,
            _optional_enum_value(payload.current_phase),
            payload.completed_step,
            payload.next_action,
            json.dumps(payload.blockers),
            json.dumps(payload.touched_files),
            payload.verification_status,
            payload.budget_status,
            payload.recovery_guidance,
            payload.source_start_sequence,
            payload.source_end_sequence,
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


def _optional_enum_value(value: object | None) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


__all__ = ["_apply_task_checkpoint_projection"]
