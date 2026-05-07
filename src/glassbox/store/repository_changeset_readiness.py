"""Changeset review-readiness projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetReviewBriefRecord


class _SQLiteChangesetReviewReadinessMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_changeset_review_briefs(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReviewBriefRecord]:
        return query_store.list_changeset_review_briefs(
            self._connection,
            session_id,
            changeset_id,
        )

    def list_changeset_readiness(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReadinessRecord]:
        return query_store.list_changeset_readiness(
            self._connection,
            session_id,
            changeset_id,
        )


__all__ = ["_SQLiteChangesetReviewReadinessMethods"]
