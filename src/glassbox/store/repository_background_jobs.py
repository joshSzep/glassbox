"""Background-job methods for SQLite repositories."""

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

import glassbox.store.sqlite_background_jobs as background_job_store
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobState


class _SQLiteBackgroundJobMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def enqueue_background_job(
        self,
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
        return background_job_store.enqueue_background_job(
            self._connection,
            session_id,
            kind=kind,
            job_type=job_type,
            title=title,
            payload=payload,
            requested_by=requested_by,
            priority=priority,
            task_id=task_id,
            parent_job_id=parent_job_id,
            job_id=job_id,
        )

    def claim_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        worker_id: str,
        claim_token: str,
        lease_expires_at: datetime,
        now: datetime | None = None,
    ) -> BackgroundJobRecord:
        return background_job_store.claim_background_job(
            self._connection,
            job_id,
            worker_id=worker_id,
            claim_token=claim_token,
            lease_expires_at=lease_expires_at,
            now=now,
        )

    def heartbeat_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        worker_id: str,
        claim_token: str,
        lease_expires_at: datetime,
        message: str | None = None,
    ) -> BackgroundJobRecord:
        return background_job_store.heartbeat_background_job(
            self._connection,
            job_id,
            worker_id=worker_id,
            claim_token=claim_token,
            lease_expires_at=lease_expires_at,
            message=message,
        )

    def complete_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        summary: str,
    ) -> BackgroundJobRecord:
        return background_job_store.complete_background_job(
            self._connection,
            job_id,
            summary=summary,
        )

    def fail_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        failure_kind: BackgroundJobFailureKind,
        message: str,
        retryable: bool = False,
        next_retry_at: datetime | None = None,
        attempt: int | None = None,
    ) -> BackgroundJobRecord:
        return background_job_store.fail_background_job(
            self._connection,
            job_id,
            failure_kind=failure_kind,
            message=message,
            retryable=retryable,
            next_retry_at=next_retry_at,
            attempt=attempt,
        )

    def cancel_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        requested_by: str = "operator",
        reason: str | None = None,
    ) -> BackgroundJobRecord:
        return background_job_store.request_background_job_cancellation(
            self._connection,
            job_id,
            requested_by=requested_by,
            reason=reason,
        )

    def retry_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        requested_by: str = "operator",
        reason: str | None = None,
        retry_budget: int = 3,
    ) -> BackgroundJobRecord:
        return background_job_store.retry_background_job(
            self._connection,
            job_id,
            requested_by=requested_by,
            reason=reason,
            retry_budget=retry_budget,
        )

    def abandon_background_job(
        self,
        job_id: BackgroundJobId,
        *,
        abandoned_by: str = "operator",
        reason: str,
    ) -> BackgroundJobRecord:
        return background_job_store.abandon_background_job(
            self._connection,
            job_id,
            abandoned_by=abandoned_by,
            reason=reason,
        )

    def list_background_jobs(
        self,
        *,
        state: BackgroundJobState | None = None,
        limit: int | None = None,
    ) -> list[BackgroundJobRecord]:
        return background_job_store.list_background_jobs(
            self._connection,
            state=state,
            limit=limit,
        )

    def get_background_job(
        self,
        job_id: BackgroundJobId,
    ) -> BackgroundJobRecord | None:
        return background_job_store.get_background_job(self._connection, job_id)

    def count_background_jobs_by_state(self) -> dict[str, int]:
        return background_job_store.count_background_jobs_by_state(self._connection)

    def latest_failed_background_job(self) -> BackgroundJobRecord | None:
        return background_job_store.latest_failed_background_job(self._connection)


__all__ = ["_SQLiteBackgroundJobMethods"]
