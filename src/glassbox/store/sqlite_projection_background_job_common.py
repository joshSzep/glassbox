"""Shared background-job projection SQL helpers for SQLite."""

import sqlite3
from datetime import UTC
from datetime import datetime

from glassbox.core.events import EventEnvelope


def _update_job(
    connection: sqlite3.Connection,
    job_id,
    event: EventEnvelope,
    **fields,
) -> None:
    assignments = ["updated_at = ?", "last_sequence = ?"]
    values: list[object] = [_datetime_text(event.created_at), event.sequence]
    for name, value in fields.items():
        assignments.append(f"{name} = ?")
        values.append(value)
    values.append(str(job_id))
    connection.execute(
        f"""
        update background_jobs
        set {", ".join(assignments)}
        where job_id = ?
        """,
        values,
    )


def _datetime_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _optional_text(value) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["_datetime_text", "_optional_text", "_update_job"]
