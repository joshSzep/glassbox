"""Long-run verification ledger projection handlers for SQLite."""

import json
import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.events import TaskVerificationSkipped
from glassbox.core.events import TaskVerificationStarted
from glassbox.core.models import VerificationPlanEntry
from glassbox.core.types import TaskVerificationStatus


def _apply_verification_ledger_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, TaskVerificationPlanned):
        _upsert_planned_entry(
            connection,
            event,
            payload.verification,
            task_id=str(payload.task_id),
            step_id=str(payload.step_id) if payload.step_id else None,
            attempt=payload.attempt,
        )
        return
    if isinstance(payload, TaskVerificationStarted):
        _ensure_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            step_id=str(payload.step_id) if payload.step_id else None,
            check_name=payload.check_name,
        )
        connection.execute(
            """
            update task_verification_ledger
            set status = ?,
                step_id = coalesce(?, step_id),
                check_name = ?,
                attempt_count = max(attempt_count, ?),
                latest_attempt = max(latest_attempt, ?),
                started_sequence = coalesce(started_sequence, ?),
                updated_at = ?,
                last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.RUNNING.value,
                str(payload.step_id) if payload.step_id else None,
                payload.check_name,
                payload.attempt,
                payload.attempt,
                event.sequence,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        return
    if isinstance(payload, TaskVerificationFailed):
        failure_artifact_id = (
            str(payload.failure.artifact_id) if payload.failure.artifact_id else None
        )
        _ensure_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            step_id=str(payload.step_id) if payload.step_id else None,
            check_name="verification",
        )
        connection.execute(
            """
            update task_verification_ledger
            set status = ?,
                step_id = coalesce(?, step_id),
                latest_failed_sequence = ?,
                latest_failed_summary = ?,
                latest_failed_category = ?,
                latest_failed_artifact_id = ?,
                latest_artifact_id = ?,
                summary = ?,
                updated_at = ?,
                last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.FAILED.value,
                str(payload.step_id) if payload.step_id else None,
                event.sequence,
                payload.failure.summary,
                payload.failure.category.value,
                failure_artifact_id,
                failure_artifact_id,
                payload.failure.summary,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        return
    if isinstance(payload, TaskVerificationSkipped):
        _update_terminal_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            status=TaskVerificationStatus.SKIPPED,
            summary=payload.reason,
            step_id=str(payload.step_id) if payload.step_id else None,
            artifact_id=None,
            success_sequence=None,
        )
        return
    if isinstance(payload, TaskVerificationRetried):
        _update_terminal_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            status=TaskVerificationStatus.RETRIED,
            summary=payload.reason,
            step_id=str(payload.step_id) if payload.step_id else None,
            artifact_id=None,
            success_sequence=None,
        )
        return
    if isinstance(payload, TaskVerificationCompleted):
        success_sequence = (
            event.sequence if payload.status == TaskVerificationStatus.PASSED else None
        )
        _update_terminal_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            status=payload.status,
            summary=payload.summary,
            step_id=None,
            artifact_id=str(payload.artifact_id) if payload.artifact_id else None,
            success_sequence=success_sequence,
        )
        return
    if isinstance(payload, TaskVerificationResidualRiskAccepted):
        _ensure_entry(
            connection,
            event,
            task_id=str(payload.task_id),
            verification_id=str(payload.verification_id),
            step_id=None,
            check_name="verification",
        )
        row = connection.execute(
            """
            select accepted_risks_json
            from task_verification_ledger
            where session_id = ? and verification_id = ?
            """,
            (str(event.session_id), str(payload.verification_id)),
        ).fetchone()
        accepted_risks = _json_list(row["accepted_risks_json"] if row else "[]")
        accepted_risks.extend(payload.residual_risks)
        connection.execute(
            """
            update task_verification_ledger
            set status = ?,
                accepted_risk_count = accepted_risk_count + ?,
                accepted_risks_json = ?,
                residual_risk_reason = ?,
                summary = ?,
                updated_at = ?,
                last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.ACCEPTED_WITH_RISK.value,
                max(1, len(payload.residual_risks)),
                json.dumps(accepted_risks),
                payload.reason,
                payload.reason,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )


def _upsert_planned_entry(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    verification: VerificationPlanEntry,
    *,
    task_id: str,
    step_id: str | None,
    attempt: int,
) -> None:
    connection.execute(
        """
        insert into task_verification_ledger (
            session_id,
            task_id,
            verification_id,
            step_id,
            status,
            check_name,
            kind,
            source,
            command_json,
            changed_paths_json,
            eval_case_id,
            eval_profile_id,
            blocking,
            attempt_count,
            latest_attempt,
            planned_sequence,
            accepted_risks_json,
            updated_at,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, verification_id) do update set
            task_id = excluded.task_id,
            step_id = coalesce(excluded.step_id, task_verification_ledger.step_id),
            status = excluded.status,
            check_name = excluded.check_name,
            kind = excluded.kind,
            source = excluded.source,
            command_json = excluded.command_json,
            changed_paths_json = excluded.changed_paths_json,
            eval_case_id = excluded.eval_case_id,
            eval_profile_id = excluded.eval_profile_id,
            blocking = excluded.blocking,
            attempt_count = max(
                task_verification_ledger.attempt_count,
                excluded.attempt_count
            ),
            latest_attempt = max(
                task_verification_ledger.latest_attempt,
                excluded.latest_attempt
            ),
            planned_sequence = coalesce(
                task_verification_ledger.planned_sequence,
                excluded.planned_sequence
            ),
            updated_at = excluded.updated_at,
            last_sequence = excluded.last_sequence
        """,
        (
            str(event.session_id),
            task_id,
            str(verification.verification_id),
            step_id,
            TaskVerificationStatus.PLANNED.value,
            verification.check_name,
            verification.kind.value,
            verification.source.value,
            json.dumps(verification.command),
            json.dumps([str(path) for path in verification.changed_paths]),
            verification.eval_case_id,
            verification.eval_profile_id,
            1 if verification.blocking else 0,
            attempt,
            attempt,
            event.sequence,
            "[]",
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _ensure_entry(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    task_id: str,
    verification_id: str,
    step_id: str | None,
    check_name: str,
) -> None:
    connection.execute(
        """
        insert into task_verification_ledger (
            session_id,
            task_id,
            verification_id,
            step_id,
            status,
            check_name,
            command_json,
            changed_paths_json,
            accepted_risks_json,
            updated_at,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, verification_id) do nothing
        """,
        (
            str(event.session_id),
            task_id,
            verification_id,
            step_id,
            check_name,
            TaskVerificationStatus.PLANNED.value,
            "[]",
            "[]",
            "[]",
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _update_terminal_entry(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    task_id: str,
    verification_id: str,
    status: TaskVerificationStatus,
    summary: str | None,
    step_id: str | None,
    artifact_id: str | None,
    success_sequence: int | None,
) -> None:
    _ensure_entry(
        connection,
        event,
        task_id=task_id,
        verification_id=verification_id,
        step_id=step_id,
        check_name="verification",
    )
    connection.execute(
        """
        update task_verification_ledger
        set status = ?,
            step_id = coalesce(?, step_id),
            last_success_sequence = coalesce(?, last_success_sequence),
            latest_artifact_id = coalesce(?, latest_artifact_id),
            summary = ?,
            updated_at = ?,
            last_sequence = ?
        where session_id = ? and verification_id = ?
        """,
        (
            status.value,
            step_id,
            success_sequence,
            artifact_id,
            summary,
            event.created_at.isoformat(),
            event.sequence,
            str(event.session_id),
            verification_id,
        ),
    )


def _json_list(raw_json: str) -> list[str]:
    value = json.loads(raw_json)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = ["_apply_verification_ledger_projection"]
