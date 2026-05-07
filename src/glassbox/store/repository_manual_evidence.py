"""Manual evidence projection methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ManualEvidenceId
from glassbox.core.ids import SessionId
from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.types import ManualEvidenceState
from glassbox.core.types import ManualEvidenceTargetKind


class _SQLiteManualEvidenceMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def list_manual_evidence(
        self,
        *,
        session_id: SessionId | None = None,
        changeset_id: ChangesetId | None = None,
        target_kind: ManualEvidenceTargetKind | None = None,
        target_id: str | None = None,
        state: ManualEvidenceState | None = None,
        include_archived: bool = False,
        include_rejected: bool = False,
        include_superseded: bool = False,
        limit: int | None = None,
    ) -> list[ManualEvidenceRecord]:
        return query_store.list_manual_evidence(
            self._connection,
            session_id=session_id,
            changeset_id=changeset_id,
            target_kind=target_kind,
            target_id=target_id,
            state=state,
            include_archived=include_archived,
            include_rejected=include_rejected,
            include_superseded=include_superseded,
            limit=limit,
        )

    def get_manual_evidence(
        self,
        evidence_id: ManualEvidenceId,
    ) -> ManualEvidenceRecord | None:
        return query_store.get_manual_evidence(self._connection, evidence_id)


__all__ = ["_SQLiteManualEvidenceMethods"]
