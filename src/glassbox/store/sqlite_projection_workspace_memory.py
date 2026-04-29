"""Workspace-memory projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryCreated
from glassbox.core.events import WorkspaceMemoryImported
from glassbox.core.events import WorkspaceMemoryInvalidated
from glassbox.core.events import WorkspaceMemoryPruned
from glassbox.core.events import WorkspaceMemoryUpdated
from glassbox.core.events import WorkspaceMemoryUsedInContext
from glassbox.core.types import WorkspaceMemoryState


def _apply_workspace_memory_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, WorkspaceMemoryCreated):
        connection.execute(
            """
            insert into workspace_memory (
                memory_id,
                session_id,
                kind,
                state,
                content,
                summary,
                provenance_json,
                created_by,
                created_at,
                updated_at,
                tags_json,
                redacted,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(memory_id) do update set
                session_id = excluded.session_id,
                kind = excluded.kind,
                state = excluded.state,
                content = excluded.content,
                summary = excluded.summary,
                provenance_json = excluded.provenance_json,
                created_by = excluded.created_by,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                confirmed_by = null,
                confirmed_at = null,
                invalidated_by = null,
                invalidated_at = null,
                invalidation_reason = null,
                last_used_at = null,
                use_count = 0,
                tags_json = excluded.tags_json,
                redacted = excluded.redacted,
                import_source = null,
                pruned_by = null,
                pruned_at = null,
                prune_reason = null,
                last_sequence = excluded.last_sequence
            """,
            (
                str(payload.memory_id),
                str(event.session_id),
                payload.kind.value,
                WorkspaceMemoryState.ACTIVE.value,
                payload.content,
                payload.summary,
                payload.provenance.model_dump_json(),
                payload.created_by,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                json.dumps(payload.tags),
                1 if payload.redacted else 0,
                event.sequence,
            ),
        )
        return
    if isinstance(payload, WorkspaceMemoryImported):
        connection.execute(
            """
            insert into workspace_memory (
                memory_id,
                session_id,
                kind,
                state,
                content,
                provenance_json,
                created_by,
                created_at,
                updated_at,
                tags_json,
                redacted,
                import_source,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(memory_id) do update set
                session_id = excluded.session_id,
                kind = excluded.kind,
                state = excluded.state,
                content = excluded.content,
                provenance_json = excluded.provenance_json,
                created_by = excluded.created_by,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                tags_json = excluded.tags_json,
                redacted = excluded.redacted,
                import_source = excluded.import_source,
                last_sequence = excluded.last_sequence
            """,
            (
                str(payload.memory_id),
                str(event.session_id),
                payload.kind.value,
                WorkspaceMemoryState.IMPORTED.value,
                payload.content,
                payload.provenance.model_dump_json(),
                payload.imported_by,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                "[]",
                1 if payload.redacted else 0,
                payload.import_source,
                event.sequence,
            ),
        )
        return
    if isinstance(payload, WorkspaceMemoryConfirmed):
        connection.execute(
            """
            update workspace_memory
            set state = ?, confirmed_by = ?, confirmed_at = ?, updated_at = ?,
                pruned_by = null, pruned_at = null, prune_reason = null,
                last_sequence = ?
            where memory_id = ?
            """,
            (
                WorkspaceMemoryState.ACTIVE.value,
                payload.confirmed_by,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
                str(payload.memory_id),
            ),
        )
        return
    if isinstance(payload, WorkspaceMemoryUpdated):
        connection.execute(
            """
            update workspace_memory
            set content = coalesce(?, content),
                summary = coalesce(?, summary),
                tags_json = coalesce(?, tags_json),
                updated_at = ?,
                last_sequence = ?
            where memory_id = ?
            """,
            (
                payload.content,
                payload.summary,
                json.dumps(payload.tags) if payload.tags is not None else None,
                event.created_at.isoformat(),
                event.sequence,
                str(payload.memory_id),
            ),
        )
        return
    if isinstance(payload, WorkspaceMemoryInvalidated):
        connection.execute(
            """
            update workspace_memory
            set state = ?, invalidated_by = ?, invalidated_at = ?,
                invalidation_reason = ?, updated_at = ?, last_sequence = ?
            where memory_id = ?
            """,
            (
                WorkspaceMemoryState.INVALIDATED.value,
                payload.invalidated_by,
                event.created_at.isoformat(),
                payload.reason,
                event.created_at.isoformat(),
                event.sequence,
                str(payload.memory_id),
            ),
        )
        return
    if isinstance(payload, WorkspaceMemoryUsedInContext):
        connection.execute(
            """
            update workspace_memory
            set last_used_at = ?, use_count = use_count + 1, last_sequence = ?
            where memory_id = ?
            """,
            (event.created_at.isoformat(), event.sequence, str(payload.memory_id)),
        )
        return
    if isinstance(payload, WorkspaceMemoryPruned):
        connection.execute(
            """
            update workspace_memory
            set state = ?, pruned_by = ?, pruned_at = ?, prune_reason = ?,
                updated_at = ?, last_sequence = ?
            where memory_id = ?
            """,
            (
                WorkspaceMemoryState.PRUNED.value,
                payload.pruned_by,
                event.created_at.isoformat(),
                payload.reason,
                event.created_at.isoformat(),
                event.sequence,
                str(payload.memory_id),
            ),
        )


__all__ = ["_apply_workspace_memory_projection"]
