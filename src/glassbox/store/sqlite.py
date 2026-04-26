"""Public compatibility facade for the SQLite-backed Glassbox store."""

from glassbox.store.sqlite_events import append_event
from glassbox.store.sqlite_events import append_events
from glassbox.store.sqlite_events import read_events_by_correlation_id
from glassbox.store.sqlite_events import read_session_events
from glassbox.store.sqlite_events import read_session_events_after
from glassbox.store.sqlite_events import rebuild_session_projections
from glassbox.store.sqlite_fork import build_imported_transcript_events
from glassbox.store.sqlite_fork import resolve_fork_point
from glassbox.store.sqlite_projection_health import inspect_session_projection_health
from glassbox.store.sqlite_queries import list_approvals
from glassbox.store.sqlite_queries import list_runtime_notes
from glassbox.store.sqlite_queries import list_tool_calls
from glassbox.store.sqlite_queries import list_transcript_messages
from glassbox.store.sqlite_queries import list_turn_metrics
from glassbox.store.sqlite_schema import BOOTSTRAP_STATEMENTS
from glassbox.store.sqlite_schema import MIGRATIONS
from glassbox.store.sqlite_schema import SCHEMA_VERSION
from glassbox.store.sqlite_schema import initialize_database
from glassbox.store.sqlite_schema import open_database
from glassbox.store.sqlite_sessions import create_session
from glassbox.store.sqlite_sessions import get_session
from glassbox.store.sqlite_sessions import get_session_state
from glassbox.store.sqlite_sessions import list_sessions
from glassbox.store.sqlite_sessions import update_session

__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "append_event",
    "append_events",
    "build_imported_transcript_events",
    "create_session",
    "get_session",
    "get_session_state",
    "initialize_database",
    "inspect_session_projection_health",
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
