"""Changeset lifecycle projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import ChangesetArchived
from glassbox.core.events import ChangesetCandidateAdopted
from glassbox.core.events import ChangesetCreated
from glassbox.core.events import ChangesetReadinessDecided
from glassbox.core.events import ChangesetReviewBriefCreated
from glassbox.core.events import ChangesetSourceAttached
from glassbox.core.events import EventEnvelope
from glassbox.core.types import ChangesetSourceKind


def _apply_changeset_lifecycle_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ChangesetCreated):
        connection.execute(
            """
            insert into changesets (
                session_id, changeset_id, objective, summary, status, created_by,
                task_id, turn_id, branch_search_id, branch_candidate_id,
                risk_level, risk_summary, unresolved_risk_count,
                accepted_risk_count, created_at, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, changeset_id) do update set
                objective = excluded.objective,
                summary = excluded.summary,
                status = excluded.status,
                created_by = excluded.created_by,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                branch_search_id = excluded.branch_search_id,
                branch_candidate_id = excluded.branch_candidate_id,
                risk_level = excluded.risk_level,
                risk_summary = excluded.risk_summary,
                unresolved_risk_count = excluded.unresolved_risk_count,
                accepted_risk_count = excluded.accepted_risk_count,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.changeset_id),
                payload.objective,
                payload.summary,
                "active",
                payload.created_by,
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.branch_search_id),
                _optional_str(payload.branch_candidate_id),
                "unknown",
                None,
                0,
                0,
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        return
    if isinstance(payload, ChangesetSourceAttached):
        _insert_source(
            connection,
            event,
            changeset_id=str(payload.changeset_id),
            source_kind=payload.source_kind.value,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            branch_search_id=_optional_str(payload.branch_search_id),
            branch_candidate_id=_optional_str(payload.branch_candidate_id),
            verification_id=_optional_str(payload.verification_id),
            artifact_id=_optional_str(payload.artifact_id),
            reason=payload.reason,
            limitation=payload.limitation,
        )
        _touch_changeset(connection, event, str(payload.changeset_id))
        return
    if isinstance(payload, ChangesetReviewBriefCreated):
        connection.execute(
            """
            insert into changeset_review_briefs (
                session_id, changeset_id, artifact_id, artifact_schema_version,
                render_targets_json, inventory_artifact_id, verification_id,
                task_id, turn_id, created_by, redacted, local_only, created_at,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, changeset_id, artifact_id) do update set
                artifact_schema_version = excluded.artifact_schema_version,
                render_targets_json = excluded.render_targets_json,
                inventory_artifact_id = excluded.inventory_artifact_id,
                verification_id = excluded.verification_id,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                created_by = excluded.created_by,
                redacted = excluded.redacted,
                local_only = excluded.local_only,
                created_at = excluded.created_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.changeset_id),
                str(payload.artifact_id),
                payload.artifact_schema_version,
                json.dumps(payload.render_targets),
                _optional_str(payload.inventory_artifact_id),
                _optional_str(payload.verification_id),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                payload.created_by,
                int(payload.redacted),
                int(payload.local_only),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _update_changeset(
            connection,
            event,
            str(payload.changeset_id),
            latest_review_brief_artifact_id=str(payload.artifact_id),
            latest_inventory_artifact_id=_optional_str(payload.inventory_artifact_id),
            latest_verification_id=_optional_str(payload.verification_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
        )
        return
    if isinstance(payload, ChangesetReadinessDecided):
        connection.execute(
            """
            insert into changeset_readiness (
                session_id, changeset_id, readiness_kind, state, reason,
                blockers_json, safe_next_actions_json, inventory_artifact_id,
                review_brief_artifact_id, verification_id, task_id, turn_id,
                accepted_risk_count, decided_by, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, changeset_id, readiness_kind) do update set
                state = excluded.state,
                reason = excluded.reason,
                blockers_json = excluded.blockers_json,
                safe_next_actions_json = excluded.safe_next_actions_json,
                inventory_artifact_id = excluded.inventory_artifact_id,
                review_brief_artifact_id = excluded.review_brief_artifact_id,
                verification_id = excluded.verification_id,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                accepted_risk_count = excluded.accepted_risk_count,
                decided_by = excluded.decided_by,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.changeset_id),
                payload.readiness_kind.value,
                payload.state.value,
                payload.reason,
                json.dumps(payload.blockers),
                json.dumps(payload.safe_next_actions),
                _optional_str(payload.inventory_artifact_id),
                _optional_str(payload.review_brief_artifact_id),
                _optional_str(payload.verification_id),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                payload.accepted_risk_count,
                payload.decided_by,
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _update_changeset(
            connection,
            event,
            str(payload.changeset_id),
            latest_inventory_artifact_id=_optional_str(payload.inventory_artifact_id),
            latest_verification_id=_optional_str(payload.verification_id),
            latest_review_brief_artifact_id=_optional_str(
                payload.review_brief_artifact_id
            ),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            accepted_risk_count=payload.accepted_risk_count,
        )
        return
    if isinstance(payload, ChangesetCandidateAdopted):
        _insert_source(
            connection,
            event,
            changeset_id=str(payload.changeset_id),
            source_kind=ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE.value,
            source_session_id=_optional_str(payload.candidate_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            branch_search_id=str(payload.branch_search_id),
            branch_candidate_id=str(payload.branch_candidate_id),
            verification_id=_optional_str(payload.verification_id),
            artifact_id=_optional_str(payload.preview_artifact_id),
            reason=payload.reason,
            limitation=None,
        )
        _update_changeset(
            connection,
            event,
            str(payload.changeset_id),
            branch_search_id=str(payload.branch_search_id),
            branch_candidate_id=str(payload.branch_candidate_id),
            latest_inventory_artifact_id=_optional_str(payload.inventory_artifact_id),
            latest_verification_id=_optional_str(payload.verification_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
        )
        return
    if isinstance(payload, ChangesetArchived):
        connection.execute(
            """
            update changesets
            set status = ?, archived_by = ?, archived_reason = ?,
                replacement_changeset_id = ?, updated_at = ?, last_sequence = ?
            where session_id = ? and changeset_id = ?
            """,
            (
                "archived",
                payload.archived_by,
                payload.reason,
                _optional_str(payload.replacement_changeset_id),
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.changeset_id),
            ),
        )


def _insert_source(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    changeset_id: str,
    source_kind: str,
    source_session_id: str | None,
    task_id: str | None,
    turn_id: str | None,
    branch_search_id: str | None,
    branch_candidate_id: str | None,
    verification_id: str | None,
    artifact_id: str | None,
    reason: str,
    limitation: str | None,
) -> None:
    connection.execute(
        """
        insert or replace into changeset_sources (
            session_id, changeset_id, source_kind, source_session_id, task_id,
            turn_id, branch_search_id, branch_candidate_id, verification_id,
            artifact_id, reason, limitation, created_at, last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(event.session_id),
            changeset_id,
            source_kind,
            source_session_id,
            task_id,
            turn_id,
            branch_search_id,
            branch_candidate_id,
            verification_id,
            artifact_id,
            reason,
            limitation,
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _update_changeset(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    changeset_id: str,
    **optional_values: object | None,
) -> None:
    assignments = ["updated_at = ?", "last_sequence = ?"]
    parameters: list[object] = [event.created_at.isoformat(), event.sequence]
    for column_name, value in optional_values.items():
        if value is None:
            continue
        assignments.append(f"{column_name} = ?")
        parameters.append(value)
    parameters.extend([str(event.session_id), changeset_id])
    connection.execute(
        f"""
        update changesets
        set {", ".join(assignments)}
        where session_id = ? and changeset_id = ?
        """,
        parameters,
    )


def _touch_changeset(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    changeset_id: str,
) -> None:
    _update_changeset(connection, event, changeset_id)


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


__all__ = [
    "_apply_changeset_lifecycle_projection",
    "_optional_str",
    "_update_changeset",
]
