"""Concrete repository adapters backed by the Glassbox store modules."""

import sqlite3

from glassbox.store.repository_artifacts import FilesystemArtifactRepository
from glassbox.store.repository_background_jobs import _SQLiteBackgroundJobMethods
from glassbox.store.repository_branch_search import _SQLiteBranchSearchMethods
from glassbox.store.repository_changesets import _SQLiteChangesetMethods
from glassbox.store.repository_events import _SQLiteEventMethods
from glassbox.store.repository_handoff import _SQLiteHandoffMethods
from glassbox.store.repository_projection_reads import _SQLiteProjectionReadMethods
from glassbox.store.repository_review_loop import _SQLiteReviewLoopMethods
from glassbox.store.repository_sessions import _SQLiteSessionMethods
from glassbox.store.repository_tasks import _SQLiteTaskMethods
from glassbox.store.repository_workspace_memory import _SQLiteWorkspaceMemoryMethods


class SQLiteSessionRepository(
    _SQLiteSessionMethods,
    _SQLiteEventMethods,
    _SQLiteProjectionReadMethods,
    _SQLiteBackgroundJobMethods,
    _SQLiteWorkspaceMemoryMethods,
    _SQLiteTaskMethods,
    _SQLiteBranchSearchMethods,
    _SQLiteChangesetMethods,
    _SQLiteReviewLoopMethods,
    _SQLiteHandoffMethods,
):
    """Session repository adapter backed by a SQLite connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection


__all__ = ["FilesystemArtifactRepository", "SQLiteSessionRepository"]
