"""Review feedback projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ReviewFeedbackId
from glassbox.core.ids import SessionId
from glassbox.core.models import ReviewFeedbackFixupInventoryRecord
from glassbox.core.models import ReviewFeedbackFixupPathRecord
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.core.types import ReviewFeedbackDisposition


class _SQLiteReviewFeedbackMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_review_feedback(
        self,
        *,
        session_id: SessionId | None = None,
        changeset_id: ChangesetId | None = None,
        disposition: ReviewFeedbackDisposition | None = None,
        include_archived: bool = False,
        file_path: str | None = None,
        limit: int | None = None,
    ) -> list[ReviewFeedbackRecord]:
        return query_store.list_review_feedback(
            self._connection,
            session_id=session_id,
            changeset_id=changeset_id,
            disposition=disposition,
            include_archived=include_archived,
            file_path=file_path,
            limit=limit,
        )

    def get_review_feedback(
        self,
        feedback_id: ReviewFeedbackId,
    ) -> ReviewFeedbackRecord | None:
        return query_store.get_review_feedback(self._connection, feedback_id)

    def list_review_feedback_scopes(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackScopeRecord]:
        return query_store.list_review_feedback_scopes(
            self._connection,
            session_id,
            feedback_id,
        )

    def list_review_feedback_fixup_inventories(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackFixupInventoryRecord]:
        return query_store.list_review_feedback_fixup_inventories(
            self._connection,
            session_id,
            feedback_id,
        )

    def list_review_feedback_fixup_paths(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
        artifact_id: ArtifactId,
    ) -> list[ReviewFeedbackFixupPathRecord]:
        return query_store.list_review_feedback_fixup_paths(
            self._connection,
            session_id,
            feedback_id,
            artifact_id,
        )


__all__ = ["_SQLiteReviewFeedbackMethods"]
