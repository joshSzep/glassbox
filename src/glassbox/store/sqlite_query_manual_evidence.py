"""Manual evidence projection read helpers for SQLite-backed stores."""

import json
import sqlite3
from datetime import datetime

from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ManualEvidenceId
from glassbox.core.ids import SessionId
from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.types import ManualEvidenceFreshness
from glassbox.core.types import ManualEvidenceKind
from glassbox.core.types import ManualEvidenceRedactionStatus
from glassbox.core.types import ManualEvidenceState
from glassbox.core.types import ManualEvidenceTargetKind


def list_manual_evidence(
    connection: sqlite3.Connection,
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
    query = _manual_evidence_select_sql()
    parameters: list[object] = []
    query += " where 1 = 1"
    if session_id is not None:
        query += " and e.session_id = ?"
        parameters.append(str(session_id))
    if changeset_id is not None:
        query += " and e.changeset_id = ?"
        parameters.append(str(changeset_id))
    if target_kind is not None:
        query += " and e.target_kind = ?"
        parameters.append(target_kind.value)
    if target_id is not None:
        query += " and e.target_id = ?"
        parameters.append(target_id)
    if state is not None:
        query += " and e.state = ?"
        parameters.append(state.value)
    else:
        if not include_archived:
            query += " and e.state != 'archived'"
        if not include_rejected:
            query += " and e.state != 'rejected'"
        if not include_superseded:
            query += " and e.state != 'superseded'"
    query += " order by e.updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    rows = connection.execute(query, parameters).fetchall()
    return [_manual_evidence_record_from_row(row) for row in rows]


def get_manual_evidence(
    connection: sqlite3.Connection,
    evidence_id: ManualEvidenceId,
) -> ManualEvidenceRecord | None:
    row = connection.execute(
        _manual_evidence_select_sql() + " where e.evidence_id = ?",
        (str(evidence_id),),
    ).fetchone()
    if row is None:
        return None
    return _manual_evidence_record_from_row(row)


def _manual_evidence_select_sql() -> str:
    return """
        select
            e.session_id, e.evidence_id, e.evidence_kind, e.state,
            e.target_kind, e.target_id, e.changeset_id, e.feedback_id,
            e.artifact_id, e.artifact_schema_version, e.summary, e.source_label,
            e.observed_at, e.created_by, e.local_only, e.redaction_status,
            e.freshness, e.limitations_json, e.non_claims_json,
            e.rejected_reason, e.archived_reason, e.superseded_reason,
            e.replacement_evidence_id, e.superseded_by, e.archived_by,
            e.rejected_by, e.task_id, e.turn_id, e.verification_id,
            e.created_at, e.updated_at, e.last_sequence
        from manual_evidence e
    """


def _manual_evidence_record_from_row(row: sqlite3.Row) -> ManualEvidenceRecord:
    return ManualEvidenceRecord(
        session_id=row["session_id"],
        evidence_id=row["evidence_id"],
        evidence_kind=ManualEvidenceKind(row["evidence_kind"]),
        state=ManualEvidenceState(row["state"]),
        target_kind=ManualEvidenceTargetKind(row["target_kind"]),
        target_id=row["target_id"],
        changeset_id=row["changeset_id"],
        feedback_id=row["feedback_id"],
        artifact_id=row["artifact_id"],
        artifact_schema_version=row["artifact_schema_version"],
        summary=row["summary"],
        source_label=row["source_label"],
        observed_at=_optional_datetime(row["observed_at"]),
        created_by=row["created_by"],
        local_only=bool(row["local_only"]),
        redaction_status=ManualEvidenceRedactionStatus(row["redaction_status"]),
        freshness=ManualEvidenceFreshness(row["freshness"]),
        limitations=json.loads(row["limitations_json"]),
        non_claims=json.loads(row["non_claims_json"]),
        rejected_reason=row["rejected_reason"],
        archived_reason=row["archived_reason"],
        superseded_reason=row["superseded_reason"],
        replacement_evidence_id=row["replacement_evidence_id"],
        superseded_by=row["superseded_by"],
        archived_by=row["archived_by"],
        rejected_by=row["rejected_by"],
        task_id=row["task_id"],
        turn_id=row["turn_id"],
        verification_id=row["verification_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


def _optional_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


__all__ = [
    "get_manual_evidence",
    "list_manual_evidence",
]
