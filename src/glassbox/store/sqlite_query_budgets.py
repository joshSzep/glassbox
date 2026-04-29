"""Autonomy-budget projection read helpers for SQLite-backed stores."""

import sqlite3
from datetime import datetime
from uuid import UUID

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import AutonomyBudgetRemaining
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode


def get_budget_posture(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    task_id: TaskId | None = None,
) -> AutonomyBudgetPostureRecord | None:
    """Read the latest projected autonomy budget posture."""

    row = connection.execute(
        """
        select
            session_id,
            task_id,
            mode,
            budget_json,
            usage_json,
            remaining_json,
            last_decision,
            last_reason,
            last_limit_name,
            last_detail,
            updated_at,
            last_sequence
        from autonomy_budget_posture
        where session_id = ? and task_id = ?
        """,
        (str(session_id), str(task_id) if task_id is not None else ""),
    ).fetchone()
    if row is None:
        return None
    return AutonomyBudgetPostureRecord(
        session_id=UUID(row["session_id"]),
        task_id=UUID(row["task_id"]) if row["task_id"] else None,
        mode=AutonomyMode(row["mode"]) if row["mode"] is not None else None,
        budget=(
            AutonomyBudget.model_validate_json(row["budget_json"])
            if row["budget_json"] is not None
            else None
        ),
        usage=AutonomyBudgetUsage.model_validate_json(row["usage_json"]),
        remaining=(
            AutonomyBudgetRemaining.model_validate_json(row["remaining_json"])
            if row["remaining_json"] is not None
            else None
        ),
        last_decision=row["last_decision"],
        last_reason=(
            AutonomyEscalationReason(row["last_reason"])
            if row["last_reason"] is not None
            else None
        ),
        last_limit_name=row["last_limit_name"],
        last_detail=row["last_detail"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
    )


__all__ = ["get_budget_posture"]
