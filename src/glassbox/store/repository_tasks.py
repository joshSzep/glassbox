"""Task projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationRecord


class _SQLiteTaskMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_tasks(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskRecord]:
        return query_store.list_tasks(
            self._connection,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

    def get_task(
        self,
        task_id: TaskId,
    ) -> TaskRecord | None:
        return query_store.get_task(self._connection, task_id)

    def list_task_steps(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskStepRecord]:
        return query_store.list_task_steps(self._connection, session_id, task_id)

    def list_task_verifications(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskVerificationRecord]:
        return query_store.list_task_verifications(
            self._connection,
            session_id,
            task_id,
        )

    def get_latest_task_checkpoint(
        self,
        session_id: SessionId,
        *,
        task_id: TaskId | None = None,
    ) -> TaskCheckpointRecord | None:
        return query_store.get_latest_task_checkpoint(
            self._connection,
            session_id,
            task_id=task_id,
        )

    def list_task_checkpoints(
        self,
        session_id: SessionId,
        *,
        task_id: TaskId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskCheckpointRecord]:
        return query_store.list_task_checkpoints(
            self._connection,
            session_id,
            task_id=task_id,
            limit=limit,
            offset=offset,
        )

    def list_open_blocked_tasks(
        self,
        session_id: SessionId,
    ) -> list[TaskRecord]:
        return query_store.list_open_blocked_tasks(self._connection, session_id)


__all__ = ["_SQLiteTaskMethods"]
