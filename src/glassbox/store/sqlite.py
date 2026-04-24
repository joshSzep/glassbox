"""Public compatibility facade for the SQLite-backed Glassbox store."""

from glassbox.store._sqlite_events import (
    append_event,
    append_events,
    read_events_by_correlation_id,
    read_session_events,
    read_session_events_after,
    rebuild_session_projections,
)
from glassbox.store._sqlite_fork import (
    build_imported_transcript_events,
    resolve_fork_point,
)
from glassbox.store._sqlite_queries import (
    list_approvals,
    list_runtime_notes,
    list_tool_calls,
    list_transcript_messages,
    list_turn_metrics,
)
from glassbox.store._sqlite_schema import (
    BOOTSTRAP_STATEMENTS,
    SCHEMA_VERSION,
    initialize_database,
    open_database,
)
from glassbox.store._sqlite_sessions import (
    create_session,
    get_session,
    get_session_state,
    list_sessions,
    update_session,
)

__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "SCHEMA_VERSION",
    "append_event",
    "append_events",
    "build_imported_transcript_events",
    "create_session",
    "get_session",
    "get_session_state",
    "initialize_database",
    "list_approvals",
    "list_runtime_notes",
    "list_sessions",
    "list_tool_calls",
    "list_transcript_messages",
    "list_turn_metrics",
    "open_database",
    "read_events_by_correlation_id",
    "read_session_events",
    "read_session_events_after",
    "rebuild_session_projections",
    "resolve_fork_point",
    "update_session",
]
