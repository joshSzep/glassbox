"""Context compaction projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime
from typing import Any
from uuid import UUID

from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import ContextCompactionRecord
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope


def get_context_compaction(
    connection: sqlite3.Connection,
    session_id: SessionId,
    compaction_id: ContextCompactionId,
) -> ContextCompactionRecord | None:
    """Read one projected context compaction by id."""

    row = connection.execute(
        """
        select *
        from context_compactions
        where session_id = ? and compaction_id = ?
        """,
        (str(session_id), str(compaction_id)),
    ).fetchone()
    return None if row is None else _compaction_record_from_row(row)


def list_context_compactions(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    task_id: TaskId | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[ContextCompactionRecord]:
    """Read context compaction history newest-first."""

    query = """
        select *
        from context_compactions
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
    return [_compaction_record_from_row(row) for row in rows]


def _compaction_record_from_row(row: sqlite3.Row) -> ContextCompactionRecord:
    return ContextCompactionRecord(
        compaction_id=row["compaction_id"],
        session_id=row["session_id"],
        scope=ContextCompactionScope(row["scope"]),
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        checkpoint_id=row["checkpoint_id"],
        artifact_id=row["artifact_id"],
        artifact_schema_version=row["artifact_schema_version"],
        source_start_sequence=row["source_start_sequence"],
        source_end_sequence=row["source_end_sequence"],
        summary=row["summary"],
        freshness=ContextCompactionFreshness(row["freshness"]),
        limitations=_json_list(row["limitations_json"]),
        source_artifact_ids=[
            UUID(value) for value in _json_list(row["source_artifact_ids_json"])
        ],
        decision_count=row["decision_count"],
        unresolved_question_count=row["unresolved_question_count"],
        accepted_risk_count=row["accepted_risk_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["last_sequence"],
    )


def _json_list(raw_json: str) -> list[str]:
    value: Any = json.loads(raw_json)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = ["get_context_compaction", "list_context_compactions"]
