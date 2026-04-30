"""Provider recovery projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ProviderRecoveryRecorded


def _apply_provider_recovery_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if not isinstance(payload, ProviderRecoveryRecorded):
        return

    connection.execute(
        """
        insert or replace into provider_recovery (
            session_id,
            sequence,
            turn_id,
            task_id,
            checkpoint_id,
            provider,
            model_name,
            failure_kind,
            action,
            retryable,
            safe_to_continue,
            degraded,
            attempt,
            max_attempts,
            backoff_seconds,
            next_retry_at,
            reason,
            operator_next_action,
            created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(event.session_id),
            event.sequence,
            _optional_text(payload.turn_id),
            _optional_text(payload.task_id),
            _optional_text(payload.checkpoint_id),
            payload.provider,
            payload.model_name,
            payload.failure_kind.value,
            payload.action.value,
            int(payload.retryable),
            int(payload.safe_to_continue),
            int(payload.degraded),
            payload.attempt,
            payload.max_attempts,
            payload.backoff_seconds,
            payload.next_retry_at.isoformat() if payload.next_retry_at else None,
            payload.reason,
            payload.operator_next_action,
            event.created_at.isoformat(),
        ),
    )


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


__all__ = ["_apply_provider_recovery_projection"]
