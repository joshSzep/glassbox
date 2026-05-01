"""Changeset projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord


class _SQLiteChangesetMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_changesets(
        self,
        *,
        session_id: SessionId | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ChangesetRecord]:
        return query_store.list_changesets(
            self._connection,
            session_id=session_id,
            include_archived=include_archived,
            limit=limit,
        )

    def get_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord | None:
        return query_store.get_changeset(self._connection, changeset_id)

    def list_changeset_sources(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetSourceRecord]:
        return query_store.list_changeset_sources(
            self._connection,
            session_id,
            changeset_id,
        )

    def get_changeset_inventory(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetInventoryRecord | None:
        return query_store.get_changeset_inventory(
            self._connection,
            session_id,
            changeset_id,
        )

    def get_changeset_verification_posture(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetVerificationPostureRecord | None:
        return query_store.get_changeset_verification_posture(
            self._connection,
            session_id,
            changeset_id,
        )

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


__all__ = ["_SQLiteChangesetMethods"]
