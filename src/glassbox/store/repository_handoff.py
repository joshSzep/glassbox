"""Handoff projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_query_handoff as handoff_store
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import HandoffProjectionRecord
from glassbox.core.types import HandoffSourceKind


class _SQLiteHandoffMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def get_handoff(
        self,
        session_id: SessionId,
        package_id: str,
    ) -> HandoffProjectionRecord | None:
        return handoff_store.get_handoff(self._connection, session_id, package_id)

    def list_handoffs(
        self,
        *,
        session_id: SessionId | None = None,
        task_id: TaskId | None = None,
        changeset_id: ChangesetId | None = None,
        source_kind: HandoffSourceKind | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[HandoffProjectionRecord]:
        return handoff_store.list_handoffs(
            self._connection,
            session_id=session_id,
            task_id=task_id,
            changeset_id=changeset_id,
            source_kind=source_kind,
            include_archived=include_archived,
            limit=limit,
        )


__all__ = ["_SQLiteHandoffMethods"]
