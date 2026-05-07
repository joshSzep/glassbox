"""Changeset inventory and verification projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import ChangesetInventoryRefreshed
from glassbox.core.events import ChangesetVerificationPostureUpdated
from glassbox.core.events import EventEnvelope
from glassbox.store.sqlite_projection_changeset_lifecycle import _optional_str
from glassbox.store.sqlite_projection_changeset_lifecycle import _update_changeset


def _apply_changeset_inventory_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ChangesetInventoryRefreshed):
        connection.execute(
            """
            insert into changeset_inventories (
                session_id, changeset_id, artifact_id, artifact_schema_version,
                freshness, changed_path_count, source_digest, previous_artifact_id,
                refreshed_by, risk_level, risk_summary, unresolved_risk_count,
                accepted_risk_count, task_id, turn_id, branch_search_id,
                branch_candidate_id, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, changeset_id) do update set
                artifact_id = excluded.artifact_id,
                artifact_schema_version = excluded.artifact_schema_version,
                freshness = excluded.freshness,
                changed_path_count = excluded.changed_path_count,
                source_digest = excluded.source_digest,
                previous_artifact_id = excluded.previous_artifact_id,
                refreshed_by = excluded.refreshed_by,
                risk_level = excluded.risk_level,
                risk_summary = excluded.risk_summary,
                unresolved_risk_count = excluded.unresolved_risk_count,
                accepted_risk_count = excluded.accepted_risk_count,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                branch_search_id = excluded.branch_search_id,
                branch_candidate_id = excluded.branch_candidate_id,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.changeset_id),
                str(payload.artifact_id),
                payload.artifact_schema_version,
                payload.freshness.value,
                payload.changed_path_count,
                payload.source_digest,
                _optional_str(payload.previous_artifact_id),
                payload.refreshed_by,
                payload.risk_level.value,
                payload.risk_summary,
                payload.unresolved_risk_count,
                payload.accepted_risk_count,
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.branch_search_id),
                _optional_str(payload.branch_candidate_id),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _update_changeset(
            connection,
            event,
            str(payload.changeset_id),
            latest_inventory_artifact_id=str(payload.artifact_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            branch_search_id=_optional_str(payload.branch_search_id),
            branch_candidate_id=_optional_str(payload.branch_candidate_id),
            risk_level=payload.risk_level.value,
            risk_summary=payload.risk_summary,
            unresolved_risk_count=payload.unresolved_risk_count,
            accepted_risk_count=payload.accepted_risk_count,
        )
        return
    if isinstance(payload, ChangesetVerificationPostureUpdated):
        connection.execute(
            """
            insert into changeset_verification_posture (
                session_id, changeset_id, state, summary, verification_id,
                artifact_id, task_id, turn_id, stale_count, missing_count,
                failed_count, accepted_risk_count, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, changeset_id) do update set
                state = excluded.state,
                summary = excluded.summary,
                verification_id = excluded.verification_id,
                artifact_id = excluded.artifact_id,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                stale_count = excluded.stale_count,
                missing_count = excluded.missing_count,
                failed_count = excluded.failed_count,
                accepted_risk_count = excluded.accepted_risk_count,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.changeset_id),
                payload.state.value,
                payload.summary,
                _optional_str(payload.verification_id),
                _optional_str(payload.artifact_id),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                payload.stale_count,
                payload.missing_count,
                payload.failed_count,
                payload.accepted_risk_count,
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _update_changeset(
            connection,
            event,
            str(payload.changeset_id),
            latest_verification_id=_optional_str(payload.verification_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
        )


__all__ = ["_apply_changeset_inventory_projection"]
