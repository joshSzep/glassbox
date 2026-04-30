"""Checkpoint projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.types import LongRunPhase


def get_latest_task_checkpoint(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    task_id: TaskId | None = None,
) -> TaskCheckpointRecord | None:
    """Read the newest checkpoint for a session or task."""

    records = list_task_checkpoints(
        connection,
        session_id,
        task_id=task_id,
        limit=1,
    )
    if not records:
        return None
    return records[0]


def list_task_checkpoints(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    task_id: TaskId | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TaskCheckpointRecord]:
    """Read checkpoint history newest-first."""

    query = """
        select
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
        from task_checkpoints
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if task_id is not None:
        query += " and task_id = ?"
        parameters.append(str(task_id))
    query += " order by last_sequence desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    elif offset:
        query += " limit -1"
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_checkpoint_record_from_row(row) for row in rows]


def _checkpoint_record_from_row(row: sqlite3.Row) -> TaskCheckpointRecord:
    return TaskCheckpointRecord(
        checkpoint_id=row["checkpoint_id"],
        session_id=row["session_id"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        tool_attempt_id=row["tool_attempt_id"],
        compaction_id=row["compaction_id"],
        artifact_id=row["artifact_id"],
        objective=row["objective"],
        current_phase=(
            LongRunPhase(row["current_phase"]) if row["current_phase"] else None
        ),
        completed_step=row["completed_step"],
        next_action=row["next_action"],
        blockers=_json_list(row["blockers_json"]),
        touched_files=_json_list(row["touched_files_json"]),
        verification_status=row["verification_status"],
        budget_status=row["budget_status"],
        recovery_guidance=row["recovery_guidance"],
        source_start_sequence=row["source_start_sequence"],
        source_end_sequence=row["source_end_sequence"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _json_list(raw_json: str) -> list[str]:
    value: Any = json.loads(raw_json)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = ["get_latest_task_checkpoint", "list_task_checkpoints"]
