"""Approval projection handlers for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope


def _apply_approval_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ApprovalRequested):
        connection.execute(
            """
            insert into approvals (
                approval_id,
                session_id,
                turn_id,
                subject,
                reason,
                policy_outcome,
                policy_risk_level,
                policy_source_kind,
                policy_source_label,
                status,
                requested_at,
                resolved_at,
                decided_by
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(approval_id) do update set
                turn_id = excluded.turn_id,
                subject = excluded.subject,
                reason = excluded.reason,
                policy_outcome = coalesce(
                    excluded.policy_outcome,
                    approvals.policy_outcome
                ),
                policy_risk_level = coalesce(
                    excluded.policy_risk_level,
                    approvals.policy_risk_level
                ),
                policy_source_kind = coalesce(
                    excluded.policy_source_kind,
                    approvals.policy_source_kind
                ),
                policy_source_label = coalesce(
                    excluded.policy_source_label,
                    approvals.policy_source_label
                ),
                status = excluded.status,
                requested_at = excluded.requested_at
            """,
            (
                str(payload.approval_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.subject,
                payload.reason,
                payload.policy_outcome,
                payload.policy_risk_level,
                payload.policy_source_kind,
                payload.policy_source_label,
                "pending",
                event.created_at.isoformat(),
                None,
                None,
            ),
        )
        return

    if isinstance(payload, ApprovalResolved):
        connection.execute(
            """
            update approvals
            set
                status = ?,
                resolved_at = ?,
                decided_by = ?
            where approval_id = ?
            """,
            (
                payload.decision,
                event.created_at.isoformat(),
                payload.decided_by,
                str(payload.approval_id),
            ),
        )


__all__ = ["_apply_approval_projection"]
