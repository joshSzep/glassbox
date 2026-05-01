"""Background-job creation projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import BackgroundJobCreated
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobState
from glassbox.store.sqlite_projection_background_job_common import _datetime_text
from glassbox.store.sqlite_projection_background_job_common import _optional_text


def _apply_background_job_creation_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if not isinstance(payload, BackgroundJobCreated):
        return False

    connection.execute(
        """
        insert or replace into background_jobs (
            job_id,
            session_id,
            state,
            kind,
            job_type,
            title,
            requested_by,
            payload_json,
            priority,
            task_id,
            parent_job_id,
            retryable,
            created_at,
            updated_at,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.job_id),
            str(event.session_id),
            BackgroundJobState.QUEUED.value,
            payload.kind.value,
            payload.job_type,
            payload.title,
            payload.requested_by,
            json.dumps(payload.payload, sort_keys=True),
            payload.priority,
            _optional_text(payload.task_id),
            _optional_text(payload.parent_job_id),
            0,
            _datetime_text(event.created_at),
            _datetime_text(event.created_at),
            event.sequence,
        ),
    )
    return True


__all__ = ["_apply_background_job_creation_projection"]
