"""Workspace-memory projection queries and event appends."""

import json
import sqlite3
from datetime import datetime
from uuid import UUID

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorkspaceMemoryConfirmed
from glassbox.core.events import WorkspaceMemoryInvalidated
from glassbox.core.events import WorkspaceMemoryPruned
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.store.sqlite_events import append_event
from glassbox.store.sqlite_utils import _parse_optional_datetime


def list_workspace_memory(
    connection: sqlite3.Connection,
    *,
    state: WorkspaceMemoryState | None = None,
    kind: WorkspaceMemoryKind | None = None,
    query_text: str | None = None,
    include_pruned: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[WorkspaceMemoryEntry]:
    """Read projected workspace memory entries by recent update."""

    query = _memory_select_sql() + " where 1 = 1"
    parameters: list[object] = []
    if state is not None:
        query += " and state = ?"
        parameters.append(state.value)
    elif not include_pruned:
        query += " and state != ?"
        parameters.append(WorkspaceMemoryState.PRUNED.value)
    if kind is not None:
        query += " and kind = ?"
        parameters.append(kind.value)
    if query_text is not None:
        normalized_query = query_text.strip().lower()
        if normalized_query:
            query += """
                and (
                    lower(content) like ?
                    or lower(coalesce(summary, '')) like ?
                    or lower(tags_json) like ?
                )
            """
            pattern = f"%{normalized_query}%"
            parameters.extend([pattern, pattern, pattern])
    query += " order by updated_at desc, memory_id asc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_memory_from_row(row) for row in rows]


def get_workspace_memory(
    connection: sqlite3.Connection,
    memory_id: WorkspaceMemoryId,
) -> WorkspaceMemoryEntry | None:
    """Read one projected workspace memory entry by ID."""

    row = connection.execute(
        _memory_select_sql() + " where memory_id = ?",
        (str(memory_id),),
    ).fetchone()
    if row is None:
        return None
    return _memory_from_row(row)


def confirm_workspace_memory(
    connection: sqlite3.Connection,
    memory_id: WorkspaceMemoryId,
    *,
    confirmed_by: str = "operator",
    reason: str | None = None,
) -> WorkspaceMemoryEntry:
    """Append a confirmation event and return the updated projection."""

    entry = _require_workspace_memory(connection, memory_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=entry.session_id,
            sequence=0,
            payload=WorkspaceMemoryConfirmed(
                memory_id=memory_id,
                confirmed_by=confirmed_by,
                reason=reason,
            ),
        ),
    )
    return _require_workspace_memory(connection, memory_id)


def invalidate_workspace_memory(
    connection: sqlite3.Connection,
    memory_id: WorkspaceMemoryId,
    *,
    invalidated_by: str = "operator",
    reason: str,
) -> WorkspaceMemoryEntry:
    """Append an invalidation event and return the updated projection."""

    entry = _require_workspace_memory(connection, memory_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=entry.session_id,
            sequence=0,
            payload=WorkspaceMemoryInvalidated(
                memory_id=memory_id,
                invalidated_by=invalidated_by,
                reason=reason,
            ),
        ),
    )
    return _require_workspace_memory(connection, memory_id)


def prune_workspace_memory(
    connection: sqlite3.Connection,
    memory_id: WorkspaceMemoryId,
    *,
    pruned_by: str = "operator",
    reason: str,
) -> WorkspaceMemoryEntry:
    """Append a prune event and return the updated projection."""

    entry = _require_workspace_memory(connection, memory_id)
    append_event(
        connection,
        EventEnvelope(
            session_id=entry.session_id,
            sequence=0,
            payload=WorkspaceMemoryPruned(
                memory_id=memory_id,
                pruned_by=pruned_by,
                reason=reason,
            ),
        ),
    )
    return _require_workspace_memory(connection, memory_id)


def _require_workspace_memory(
    connection: sqlite3.Connection,
    memory_id: WorkspaceMemoryId,
) -> WorkspaceMemoryEntry:
    entry = get_workspace_memory(connection, memory_id)
    if entry is None:
        raise ValueError(f"unknown workspace memory: {memory_id}")
    return entry


def _memory_select_sql() -> str:
    return """
        select
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
            confirmed_by,
            confirmed_at,
            invalidated_by,
            invalidated_at,
            invalidation_reason,
            last_used_at,
            use_count,
            tags_json,
            redacted,
            import_source,
            pruned_by,
            pruned_at,
            prune_reason,
            last_sequence
        from workspace_memory
    """


def _memory_from_row(row: sqlite3.Row) -> WorkspaceMemoryEntry:
    return WorkspaceMemoryEntry(
        memory_id=UUID(row["memory_id"]),
        session_id=UUID(row["session_id"]),
        kind=WorkspaceMemoryKind(row["kind"]),
        state=WorkspaceMemoryState(row["state"]),
        content=row["content"],
        summary=row["summary"],
        provenance=WorkspaceMemoryProvenance.model_validate_json(
            row["provenance_json"]
        ),
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        confirmed_by=row["confirmed_by"],
        confirmed_at=_parse_optional_datetime(row["confirmed_at"]),
        invalidated_by=row["invalidated_by"],
        invalidated_at=_parse_optional_datetime(row["invalidated_at"]),
        invalidation_reason=row["invalidation_reason"],
        last_used_at=_parse_optional_datetime(row["last_used_at"]),
        use_count=row["use_count"],
        tags=json.loads(row["tags_json"]),
        redacted=bool(row["redacted"]),
        import_source=row["import_source"],
        pruned_by=row["pruned_by"],
        pruned_at=_parse_optional_datetime(row["pruned_at"]),
        prune_reason=row["prune_reason"],
        last_sequence=row["last_sequence"],
    )


__all__ = [
    "confirm_workspace_memory",
    "get_workspace_memory",
    "invalidate_workspace_memory",
    "list_workspace_memory",
    "prune_workspace_memory",
]
