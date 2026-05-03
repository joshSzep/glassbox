"""Review-loop projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ReviewFeedbackArchived
from glassbox.core.events import ReviewFeedbackCreated
from glassbox.core.events import ReviewFeedbackDispositionUpdated
from glassbox.core.events import ReviewFeedbackFixupInventoryAttached
from glassbox.core.events import ReviewFeedbackReopened
from glassbox.core.events import ReviewFeedbackResolved
from glassbox.core.events import ReviewFeedbackRiskAccepted
from glassbox.core.events import ReviewFeedbackScopeAttached
from glassbox.core.types import ReviewFeedbackDisposition


def _apply_review_loop_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ReviewFeedbackCreated):
        connection.execute(
            """
            insert into review_feedback (
                session_id, feedback_id, changeset_id, feedback_kind, provenance,
                disposition, summary, body, source_label, reviewer_label, created_by,
                source_session_id, task_id, turn_id, artifact_id, verification_id,
                created_at, updated_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, feedback_id) do update set
                changeset_id = excluded.changeset_id,
                feedback_kind = excluded.feedback_kind,
                provenance = excluded.provenance,
                summary = excluded.summary,
                body = excluded.body,
                source_label = excluded.source_label,
                reviewer_label = excluded.reviewer_label,
                created_by = excluded.created_by,
                source_session_id = excluded.source_session_id,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                artifact_id = excluded.artifact_id,
                verification_id = excluded.verification_id,
                updated_at = excluded.updated_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.feedback_id),
                str(payload.changeset_id),
                payload.feedback_kind.value,
                payload.provenance.value,
                ReviewFeedbackDisposition.OPEN.value,
                payload.summary,
                payload.body,
                payload.source_label,
                payload.reviewer_label,
                payload.created_by,
                _optional_str(payload.source_session_id),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.artifact_id),
                _optional_str(payload.verification_id),
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        return
    if isinstance(payload, ReviewFeedbackScopeAttached):
        connection.execute(
            """
            insert into review_feedback_scopes (
                session_id, feedback_id, changeset_id, scope_kind, reason,
                source_session_id, task_id, turn_id, artifact_id, verification_id,
                branch_search_id, branch_candidate_id, file_path, line_start,
                line_end, created_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, feedback_id, last_sequence) do update set
                changeset_id = excluded.changeset_id,
                scope_kind = excluded.scope_kind,
                reason = excluded.reason,
                source_session_id = excluded.source_session_id,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                artifact_id = excluded.artifact_id,
                verification_id = excluded.verification_id,
                branch_search_id = excluded.branch_search_id,
                branch_candidate_id = excluded.branch_candidate_id,
                file_path = excluded.file_path,
                line_start = excluded.line_start,
                line_end = excluded.line_end,
                created_at = excluded.created_at
            """,
            (
                str(event.session_id),
                str(payload.feedback_id),
                str(payload.changeset_id),
                payload.scope_kind.value,
                payload.reason,
                _optional_str(payload.source_session_id),
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.artifact_id),
                _optional_str(payload.verification_id),
                _optional_str(payload.branch_search_id),
                _optional_str(payload.branch_candidate_id),
                payload.file_path,
                payload.line_start,
                payload.line_end,
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _touch_feedback(connection, event, str(payload.feedback_id))
        return
    if isinstance(payload, ReviewFeedbackDispositionUpdated):
        _update_feedback(
            connection,
            event,
            str(payload.feedback_id),
            disposition=payload.disposition.value,
            updated_by=payload.updated_by,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            artifact_id=_optional_str(payload.artifact_id),
            verification_id=_optional_str(payload.verification_id),
        )
        return
    if isinstance(payload, ReviewFeedbackResolved):
        _update_feedback(
            connection,
            event,
            str(payload.feedback_id),
            disposition=ReviewFeedbackDisposition.RESOLVED_LOCALLY.value,
            resolved_by=payload.resolved_by,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            artifact_id=_optional_str(payload.artifact_id),
            verification_id=_optional_str(payload.verification_id),
            resolution_summary=payload.resolution_summary,
            residual_risk=payload.residual_risk,
        )
        return
    if isinstance(payload, ReviewFeedbackReopened):
        _update_feedback(
            connection,
            event,
            str(payload.feedback_id),
            disposition=ReviewFeedbackDisposition.OPEN.value,
            updated_by=payload.reopened_by,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            artifact_id=_optional_str(payload.artifact_id),
            verification_id=_optional_str(payload.verification_id),
            increment_reopened=True,
        )
        return
    if isinstance(payload, ReviewFeedbackArchived):
        _update_feedback(
            connection,
            event,
            str(payload.feedback_id),
            disposition=ReviewFeedbackDisposition.ARCHIVED.value,
            archived_by=payload.archived_by,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            artifact_id=_optional_str(payload.artifact_id),
            verification_id=_optional_str(payload.verification_id),
            archived_reason=payload.reason,
            replacement_feedback_id=_optional_str(payload.replacement_feedback_id),
        )
        return
    if isinstance(payload, ReviewFeedbackRiskAccepted):
        _update_feedback(
            connection,
            event,
            str(payload.feedback_id),
            disposition=ReviewFeedbackDisposition.ACCEPTED_WITH_RISK.value,
            accepted_by=payload.accepted_by,
            source_session_id=_optional_str(payload.source_session_id),
            task_id=_optional_str(payload.task_id),
            turn_id=_optional_str(payload.turn_id),
            artifact_id=_optional_str(payload.artifact_id),
            verification_id=_optional_str(payload.verification_id),
            risk_summary=payload.risk_summary,
            acceptance_reason=payload.acceptance_reason,
        )
        return
    if isinstance(payload, ReviewFeedbackFixupInventoryAttached):
        connection.execute(
            """
            insert into review_feedback_fixup_inventories (
                session_id, feedback_id, changeset_id, artifact_id,
                artifact_schema_version, source_kind, source_summary,
                source_digest, inventory_freshness, changed_path_count,
                matched_scope_path_count, stale, stale_reason, recorded_by,
                task_id, turn_id, verification_id, created_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, feedback_id, artifact_id) do update set
                changeset_id = excluded.changeset_id,
                artifact_schema_version = excluded.artifact_schema_version,
                source_kind = excluded.source_kind,
                source_summary = excluded.source_summary,
                source_digest = excluded.source_digest,
                inventory_freshness = excluded.inventory_freshness,
                changed_path_count = excluded.changed_path_count,
                matched_scope_path_count = excluded.matched_scope_path_count,
                stale = excluded.stale,
                stale_reason = excluded.stale_reason,
                recorded_by = excluded.recorded_by,
                task_id = excluded.task_id,
                turn_id = excluded.turn_id,
                verification_id = excluded.verification_id,
                created_at = excluded.created_at,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.feedback_id),
                str(payload.changeset_id),
                str(payload.artifact_id),
                payload.artifact_schema_version,
                payload.source_kind.value,
                payload.source_summary,
                payload.source_digest,
                payload.inventory_freshness.value,
                payload.changed_path_count,
                payload.matched_scope_path_count,
                int(payload.stale),
                payload.stale_reason,
                payload.recorded_by,
                _optional_str(payload.task_id),
                _optional_str(payload.turn_id),
                _optional_str(payload.verification_id),
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        connection.execute(
            """
            delete from review_feedback_fixup_paths
            where session_id = ? and feedback_id = ? and artifact_id = ?
            """,
            (
                str(event.session_id),
                str(payload.feedback_id),
                str(payload.artifact_id),
            ),
        )
        connection.executemany(
            """
            insert into review_feedback_fixup_paths (
                session_id, feedback_id, changeset_id, artifact_id, path,
                change_kind, generated, test_file, docs_file, policy_sensitive,
                risk_level, provenance_confidence, matches_feedback_scope,
                summary, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(event.session_id),
                    str(payload.feedback_id),
                    str(payload.changeset_id),
                    str(payload.artifact_id),
                    path.path,
                    path.change_kind,
                    int(path.generated),
                    int(path.test_file),
                    int(path.docs_file),
                    int(path.policy_sensitive),
                    path.risk_level,
                    path.provenance_confidence,
                    int(path.matches_feedback_scope),
                    path.summary,
                    event.sequence,
                )
                for path in payload.paths
            ],
        )
        _touch_feedback(connection, event, str(payload.feedback_id))


def _touch_feedback(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    feedback_id: str,
) -> None:
    connection.execute(
        """
        update review_feedback
        set updated_at = ?, last_sequence = ?
        where session_id = ? and feedback_id = ?
        """,
        (
            event.created_at.isoformat(),
            event.sequence,
            str(event.session_id),
            feedback_id,
        ),
    )


def _update_feedback(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    feedback_id: str,
    **columns: object,
) -> None:
    allowed_columns = {
        "disposition",
        "updated_by",
        "resolved_by",
        "archived_by",
        "accepted_by",
        "source_session_id",
        "task_id",
        "turn_id",
        "artifact_id",
        "verification_id",
        "resolution_summary",
        "residual_risk",
        "risk_summary",
        "acceptance_reason",
        "archived_reason",
        "replacement_feedback_id",
    }
    assignments: list[str] = []
    values: list[object] = []
    for column_name, value in columns.items():
        if value is None or column_name == "increment_reopened":
            continue
        if column_name not in allowed_columns:
            raise ValueError(
                f"unsupported review feedback projection column: {column_name}"
            )
        assignments.append(f"{column_name} = ?")
        values.append(value)
    if columns.get("increment_reopened"):
        assignments.append("reopened_count = reopened_count + 1")
    assignments.extend(["updated_at = ?", "last_sequence = ?"])
    values.extend([event.created_at.isoformat(), event.sequence])
    values.extend([str(event.session_id), feedback_id])
    connection.execute(
        f"""
        update review_feedback
        set {", ".join(assignments)}
        where session_id = ? and feedback_id = ?
        """,
        values,
    )


def _optional_str(value: object | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["_apply_review_loop_projection"]
