"""Manual evidence projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ManualEvidenceArchived
from glassbox.core.events import ManualEvidenceAttached
from glassbox.core.events import ManualEvidenceRejected
from glassbox.core.events import ManualEvidenceSuperseded
from glassbox.core.types import ManualEvidenceFreshness
from glassbox.core.types import ManualEvidenceState


def _apply_manual_evidence_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ManualEvidenceAttached):
        connection.execute(
            """
            insert into manual_evidence (
                session_id, evidence_id, evidence_kind, state, target_kind,
                target_id, changeset_id, feedback_id, artifact_id,
                artifact_schema_version, summary, source_label, observed_at,
                created_by, local_only, redaction_status, freshness,
                limitations_json, non_claims_json, task_id, turn_id,
                verification_id, created_at, updated_at, last_sequence
            ) values (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            on conflict(session_id, evidence_id) do update set
                evidence_kind = excluded.evidence_kind,
                state = excluded.state,
                target_kind = excluded.target_kind,
                target_id = excluded.target_id,
                changeset_id = excluded.changeset_id,
                feedback_id = excluded.feedback_id,
                artifact_id = excluded.artifact_id,
                artifact_schema_version = excluded.artifact_schema_version,
                summary = excluded.summary,
                source_label = excluded.source_label,
                observed_at = excluded.observed_at,
                created_by = excluded.created_by,
                local_only = excluded.local_only,
                redaction_status = excluded.redaction_status,
                freshness = excluded.freshness,
                limitations_json = excluded.limitations_json,
                non_claims_json = excluded.non_claims_json,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                verification_id = excluded.verification_id,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.evidence_id),
                payload.evidence_kind.value,
                ManualEvidenceState.ATTACHED.value,
                payload.target_kind.value,
                payload.target_id,
                _optional_str(payload.changeset_id),
                _optional_str(payload.feedback_id),
                str(payload.artifact_id),
                payload.artifact_schema_version,
                payload.summary,
                payload.source_label,
                payload.observed_at.isoformat() if payload.observed_at else None,
                payload.created_by,
                int(payload.local_only),
                payload.redaction_status.value,
                payload.freshness.value,
                json.dumps(payload.limitations),
                json.dumps(payload.non_claims),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.verification_id),
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        return
    if isinstance(payload, ManualEvidenceRejected):
        connection.execute(
            """
            insert into manual_evidence (
                session_id, evidence_id, evidence_kind, state, target_kind,
                target_id, changeset_id, feedback_id, summary, source_label,
                created_by, local_only, redaction_status, freshness,
                limitations_json, non_claims_json, rejected_reason, rejected_by,
                task_id, turn_id, verification_id, created_at, updated_at,
                last_sequence
            ) values (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            on conflict(session_id, evidence_id) do update set
                evidence_kind = excluded.evidence_kind,
                state = excluded.state,
                target_kind = excluded.target_kind,
                target_id = excluded.target_id,
                changeset_id = excluded.changeset_id,
                feedback_id = excluded.feedback_id,
                summary = excluded.summary,
                source_label = excluded.source_label,
                created_by = excluded.created_by,
                local_only = excluded.local_only,
                redaction_status = excluded.redaction_status,
                freshness = excluded.freshness,
                limitations_json = excluded.limitations_json,
                non_claims_json = excluded.non_claims_json,
                rejected_reason = excluded.rejected_reason,
                rejected_by = excluded.rejected_by,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                verification_id = excluded.verification_id,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.evidence_id),
                payload.evidence_kind.value,
                ManualEvidenceState.REJECTED.value,
                payload.target_kind.value,
                payload.target_id,
                _optional_str(payload.changeset_id),
                _optional_str(payload.feedback_id),
                payload.summary,
                payload.source_label,
                payload.rejected_by,
                1,
                payload.redaction_status.value,
                ManualEvidenceFreshness.UNKNOWN.value,
                json.dumps(
                    [
                        "manual evidence rejected before attachment",
                        *payload.redaction_findings,
                    ]
                ),
                json.dumps(["not retained command evidence"]),
                payload.reason,
                payload.rejected_by,
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.verification_id),
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        return
    if isinstance(payload, ManualEvidenceSuperseded):
        _update_manual_evidence(
            connection,
            event,
            str(payload.evidence_id),
            state=ManualEvidenceState.SUPERSEDED.value,
            superseded_reason=payload.reason,
            replacement_evidence_id=str(payload.replacement_evidence_id),
            superseded_by=payload.superseded_by,
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
        )
        return
    if isinstance(payload, ManualEvidenceArchived):
        _update_manual_evidence(
            connection,
            event,
            str(payload.evidence_id),
            state=ManualEvidenceState.ARCHIVED.value,
            archived_reason=payload.reason,
            archived_by=payload.archived_by,
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
        )


def _update_manual_evidence(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    evidence_id: str,
    **columns: object,
) -> None:
    allowed_columns = {
        "state",
        "archived_reason",
        "superseded_reason",
        "replacement_evidence_id",
        "superseded_by",
        "archived_by",
        "task_id",
        "turn_id",
    }
    assignments: list[str] = []
    values: list[object] = []
    for column_name, value in columns.items():
        if value is None:
            continue
        if column_name not in allowed_columns:
            raise ValueError(
                f"unsupported manual evidence projection column: {column_name}"
            )
        assignments.append(f"{column_name} = ?")
        values.append(value)
    assignments.extend(["updated_at = ?", "last_sequence = ?"])
    values.extend([event.created_at.isoformat(), event.sequence])
    values.extend([str(event.session_id), evidence_id])
    connection.execute(
        f"""
        update manual_evidence
        set {", ".join(assignments)}
        where session_id = ? and evidence_id = ?
        """,
        values,
    )


def _optional_str(value: object | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["_apply_manual_evidence_projection"]
