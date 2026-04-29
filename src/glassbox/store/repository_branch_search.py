"""Branch-search projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import SessionId
from glassbox.core.models import BranchCandidateRecord
from glassbox.core.models import BranchSearchRecord


class _SQLiteBranchSearchMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_branch_searches(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
    ) -> list[BranchSearchRecord]:
        return query_store.list_branch_searches(
            self._connection,
            session_id=session_id,
            limit=limit,
        )

    def get_branch_search(
        self,
        search_id: BranchSearchId,
    ) -> BranchSearchRecord | None:
        return query_store.get_branch_search(self._connection, search_id)

    def list_branch_candidates(
        self,
        session_id: SessionId,
        search_id: BranchSearchId,
    ) -> list[BranchCandidateRecord]:
        return query_store.list_branch_candidates(
            self._connection,
            session_id,
            search_id,
        )


__all__ = ["_SQLiteBranchSearchMethods"]
