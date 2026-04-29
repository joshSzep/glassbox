"""Background job queue helpers for SQLite-backed projections."""

import json
import sqlite3
from datetime import UTC
from datetime import datetime

from glassbox.core.events import BackgroundJobCancellationRequested
from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobClaimed
from glassbox.core.events import BackgroundJobCompleted
from glassbox.core.events import BackgroundJobCreated
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobHeartbeat
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_background_job_id
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobState
from glassbox.store.sqlite_events import append_event

_TERMINAL_STATES = {
    BackgroundJobState.COMPLETED,
    BackgroundJobState.CANCELLED,
}
_ACTIVE_STATES = {
    BackgroundJobState.CLAIMED,
    BackgroundJobState.RUNNING,
}


def enqueue_background_job(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    kind: BackgroundJobKind,
    job_type: str,
    title: str,
    payload: dict[str, object] | None = None,
    requested_by: str = "operator",
    priority: int = 0,
    task_id: TaskId | None = None,
    parent_job_id: BackgroundJobId | None = None,
    job_id: BackgroundJobId | None = None,
) -> BackgroundJobRecord:
    created = BackgroundJobCreated(
        job_id=job_id or new_background_job_id(),
        kind=kind,
        job_type=job_type,
        title=title,
        requested_by=requested_by,
        payload=payload or {},
        priority=priority,
        task_id=task_id,
        parent_job_id=parent_job_id,
    )
    append_event(
        connection,
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=created,
        ),
    )
    record = get_background_job(connection, created.job_id)
    if record is None:
        raise ValueError(f"background job projection missing for {created.job_id}")
    return record


def claim_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    worker_id: str,
    claim_token: str,
    lease_expires_at: datetime,
    now: datetime | None = None,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    _ensure_claimable(record, now=now)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobClaimed(
                job_id=job_id,
                worker_id=worker_id,
                claim_token=claim_token,
                attempt=record.attempt + 1,
                lease_expires_at=lease_expires_at,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def start_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    worker_id: str,
    claim_token: str,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobStarted(
                job_id=job_id,
                worker_id=worker_id,
                claim_token=claim_token,
                attempt=max(record.attempt, 1),
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def heartbeat_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    worker_id: str,
    claim_token: str,
    lease_expires_at: datetime,
    message: str | None = None,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobHeartbeat(
                job_id=job_id,
                worker_id=worker_id,
                claim_token=claim_token,
                lease_expires_at=lease_expires_at,
                message=message,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def record_background_job_progress(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    message: str,
    completed_units: int | None = None,
    total_units: int | None = None,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobProgressRecorded(
                job_id=job_id,
                message=message,
                completed_units=completed_units,
                total_units=total_units,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def complete_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    summary: str,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobCompleted(job_id=job_id, summary=summary),
        ),
    )
    return _require_background_job(connection, job_id)


def fail_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    failure_kind: BackgroundJobFailureKind,
    message: str,
    retryable: bool = False,
    next_retry_at: datetime | None = None,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobFailed(
                job_id=job_id,
                failure_kind=failure_kind,
                message=message,
                retryable=retryable,
                attempt=max(record.attempt, 1),
                next_retry_at=next_retry_at,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def request_background_job_cancellation(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    requested_by: str = "operator",
    reason: str | None = None,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    if record.state in {
        BackgroundJobState.CANCELLATION_REQUESTED,
        BackgroundJobState.CANCELLED,
    }:
        return record
    if record.state == BackgroundJobState.COMPLETED:
        raise ValueError(f"cannot cancel completed background job {job_id}")
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobCancellationRequested(
                job_id=job_id,
                requested_by=requested_by,
                reason=reason,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def cancel_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
    *,
    cancelled_by: str = "runtime",
    reason: str,
) -> BackgroundJobRecord:
    record = _require_background_job(connection, job_id)
    if record.state == BackgroundJobState.CANCELLED:
        return record
    append_event(
        connection,
        EventEnvelope(
            session_id=record.session_id,
            sequence=0,
            payload=BackgroundJobCancelled(
                job_id=job_id,
                cancelled_by=cancelled_by,
                reason=reason,
            ),
        ),
    )
    return _require_background_job(connection, job_id)


def list_background_jobs(
    connection: sqlite3.Connection,
    *,
    state: BackgroundJobState | None = None,
    limit: int | None = None,
) -> list[BackgroundJobRecord]:
    query = "select * from background_jobs"
    values: list[object] = []
    if state is not None:
        query += " where state = ?"
        values.append(state.value)
    query += " order by updated_at desc, priority desc"
    if limit is not None:
        query += " limit ?"
        values.append(limit)
    rows = connection.execute(query, values).fetchall()
    return [_record_from_row(row) for row in rows]


def get_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
) -> BackgroundJobRecord | None:
    row = connection.execute(
        "select * from background_jobs where job_id = ?",
        (str(job_id),),
    ).fetchone()
    if row is None:
        return None
    return _record_from_row(row)


def count_background_jobs_by_state(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    rows = connection.execute(
        "select state, count(*) as count from background_jobs group by state"
    ).fetchall()
    return {row["state"]: int(row["count"]) for row in rows}


def latest_failed_background_job(
    connection: sqlite3.Connection,
) -> BackgroundJobRecord | None:
    row = connection.execute(
        """
        select * from background_jobs
        where state = ?
        order by updated_at desc
        limit 1
        """,
        (BackgroundJobState.FAILED.value,),
    ).fetchone()
    if row is None:
        return None
    return _record_from_row(row)


def _require_background_job(
    connection: sqlite3.Connection,
    job_id: BackgroundJobId,
) -> BackgroundJobRecord:
    record = get_background_job(connection, job_id)
    if record is None:
        raise ValueError(f"unknown background job: {job_id}")
    return record


def _ensure_claimable(
    record: BackgroundJobRecord,
    *,
    now: datetime | None,
) -> None:
    if record.state in _TERMINAL_STATES:
        raise ValueError(
            f"cannot claim {record.state.value} background job {record.job_id}"
        )
    if record.state not in _ACTIVE_STATES or record.lease_expires_at is None:
        return
    current_time = now or datetime.now(UTC)
    lease_expires_at = record.lease_expires_at
    if lease_expires_at.tzinfo is None:
        lease_expires_at = lease_expires_at.replace(tzinfo=UTC)
    if lease_expires_at > current_time:
        raise ValueError(f"background job {record.job_id} is already claimed")


def _record_from_row(row: sqlite3.Row) -> BackgroundJobRecord:
    return BackgroundJobRecord(
        job_id=_uuid(row["job_id"]),
        session_id=_uuid(row["session_id"]),
        state=BackgroundJobState(row["state"]),
        kind=BackgroundJobKind(row["kind"]),
        job_type=row["job_type"],
        title=row["title"],
        requested_by=row["requested_by"],
        payload=json.loads(row["payload_json"]),
        priority=row["priority"],
        task_id=_optional_uuid(row["task_id"]),
        parent_job_id=_optional_uuid(row["parent_job_id"]),
        worker_id=row["worker_id"],
        claim_token=row["claim_token"],
        attempt=row["attempt"],
        lease_expires_at=_optional_datetime(row["lease_expires_at"]),
        last_heartbeat_at=_optional_datetime(row["last_heartbeat_at"]),
        progress_message=row["progress_message"],
        completed_units=row["completed_units"],
        total_units=row["total_units"],
        failure_kind=(
            None
            if row["failure_kind"] is None
            else BackgroundJobFailureKind(row["failure_kind"])
        ),
        failure_message=row["failure_message"],
        retryable=bool(row["retryable"]),
        next_retry_at=_optional_datetime(row["next_retry_at"]),
        cancellation_requested_by=row["cancellation_requested_by"],
        cancellation_reason=row["cancellation_reason"],
        cancelled_by=row["cancelled_by"],
        recovery_reason=row["recovery_reason"],
        recovery_detail=row["recovery_detail"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        started_at=_optional_datetime(row["started_at"]),
        completed_at=_optional_datetime(row["completed_at"]),
        last_sequence=row["last_sequence"],
    )


def _optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _optional_uuid(value: str | None):
    if value is None:
        return None
    return _uuid(value)


def _uuid(value: str):
    from uuid import UUID

    return UUID(value)


__all__ = [
    "cancel_background_job",
    "claim_background_job",
    "complete_background_job",
    "count_background_jobs_by_state",
    "enqueue_background_job",
    "fail_background_job",
    "get_background_job",
    "heartbeat_background_job",
    "latest_failed_background_job",
    "list_background_jobs",
    "record_background_job_progress",
    "request_background_job_cancellation",
    "start_background_job",
]
