"""Provider recovery projection read helpers."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.models import ProviderRecoveryRecord
from glassbox.core.types import ProviderRecoveryAction
from glassbox.core.types import ProviderRecoveryKind


def get_latest_provider_recovery(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> ProviderRecoveryRecord | None:
    records = list_provider_recovery(connection, session_id, limit=1)
    return records[0] if records else None


def list_provider_recovery(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[ProviderRecoveryRecord]:
    query = """
        select
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
        from provider_recovery
        where session_id = ?
        order by sequence desc
    """
    parameters: list[object] = [str(session_id)]
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    elif offset:
        query += " limit -1"
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_record_from_row(row) for row in rows]


def _record_from_row(row: sqlite3.Row) -> ProviderRecoveryRecord:
    return ProviderRecoveryRecord(
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        task_id=row["task_id"],
        checkpoint_id=row["checkpoint_id"],
        provider=row["provider"],
        model_name=row["model_name"],
        failure_kind=ProviderRecoveryKind(row["failure_kind"]),
        action=ProviderRecoveryAction(row["action"]),
        reason=row["reason"],
        retryable=bool(row["retryable"]),
        safe_to_continue=bool(row["safe_to_continue"]),
        degraded=bool(row["degraded"]),
        operator_next_action=row["operator_next_action"],
        attempt=row["attempt"],
        max_attempts=row["max_attempts"],
        backoff_seconds=row["backoff_seconds"],
        next_retry_at=(
            datetime.fromisoformat(row["next_retry_at"])
            if row["next_retry_at"]
            else None
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
        last_sequence=row["sequence"],
    )


__all__ = ["get_latest_provider_recovery", "list_provider_recovery"]
