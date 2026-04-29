"""Workspace-memory methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_workspace_memory as workspace_memory_store
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState


class _SQLiteWorkspaceMemoryMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_workspace_memory(
        self,
        *,
        state: WorkspaceMemoryState | None = None,
        kind: WorkspaceMemoryKind | None = None,
        query_text: str | None = None,
        include_pruned: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[WorkspaceMemoryEntry]:
        return workspace_memory_store.list_workspace_memory(
            self._connection,
            state=state,
            kind=kind,
            query_text=query_text,
            include_pruned=include_pruned,
            limit=limit,
            offset=offset,
        )

    def get_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
    ) -> WorkspaceMemoryEntry | None:
        return workspace_memory_store.get_workspace_memory(self._connection, memory_id)

    def confirm_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
        *,
        confirmed_by: str = "operator",
        reason: str | None = None,
    ) -> WorkspaceMemoryEntry:
        return workspace_memory_store.confirm_workspace_memory(
            self._connection,
            memory_id,
            confirmed_by=confirmed_by,
            reason=reason,
        )

    def invalidate_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
        *,
        invalidated_by: str = "operator",
        reason: str,
    ) -> WorkspaceMemoryEntry:
        return workspace_memory_store.invalidate_workspace_memory(
            self._connection,
            memory_id,
            invalidated_by=invalidated_by,
            reason=reason,
        )

    def prune_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
        *,
        pruned_by: str = "operator",
        reason: str,
    ) -> WorkspaceMemoryEntry:
        return workspace_memory_store.prune_workspace_memory(
            self._connection,
            memory_id,
            pruned_by=pruned_by,
            reason=reason,
        )


__all__ = ["_SQLiteWorkspaceMemoryMethods"]
