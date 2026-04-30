"""Context compaction projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import ContextCompactionCreated
from glassbox.core.events import EventEnvelope


def _apply_context_compaction_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if not isinstance(payload, ContextCompactionCreated):
        return

    connection.execute(
        """
        insert or replace into context_compactions (
            compaction_id,
            session_id,
            scope,
            task_id,
            turn_id,
            checkpoint_id,
            artifact_id,
            artifact_schema_version,
            source_start_sequence,
            source_end_sequence,
            summary,
            freshness,
            limitations_json,
            source_artifact_ids_json,
            decision_count,
            unresolved_question_count,
            accepted_risk_count,
            created_at,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.compaction_id),
            str(event.session_id),
            payload.scope.value,
            _optional_text(payload.task_id),
            _optional_text(payload.turn_id),
            _optional_text(payload.checkpoint_id),
            str(payload.artifact_id),
            payload.artifact_schema_version,
            payload.source_start_sequence,
            payload.source_end_sequence,
            payload.summary,
            payload.freshness.value,
            json.dumps(payload.limitations),
            json.dumps(
                [str(artifact_id) for artifact_id in payload.source_artifact_ids]
            ),
            payload.decision_count,
            payload.unresolved_question_count,
            payload.accepted_risk_count,
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["_apply_context_compaction_projection"]
