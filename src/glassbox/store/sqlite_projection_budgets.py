"""Autonomy budget projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import BudgetExhausted
from glassbox.core.events import BudgetOverrideRequested
from glassbox.core.events import BudgetOverrideResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.models import AutonomyBudgetUsage


def _apply_budget_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, BudgetDecisionRecorded):
        _upsert_budget_posture(
            connection,
            event,
            scope=payload.scope,
            task_id=str(payload.task_id) if payload.task_id is not None else None,
            mode=payload.mode.value,
            budget_json=payload.budget.model_dump_json(),
            usage_json=payload.usage.model_dump_json(),
            remaining_json=payload.remaining.model_dump_json(),
            last_decision=payload.decision,
            last_reason=payload.reason.value if payload.reason is not None else None,
            last_limit_name=payload.limit_name,
            last_detail=payload.detail,
        )
        return
    if isinstance(payload, BudgetExhausted):
        _upsert_budget_posture(
            connection,
            event,
            scope=payload.scope,
            task_id=str(payload.task_id) if payload.task_id is not None else None,
            mode=None,
            budget_json=None,
            usage_json=AutonomyBudgetUsage().model_dump_json(),
            remaining_json=None,
            last_decision="exhausted",
            last_reason=payload.reason.value,
            last_limit_name=payload.limit_name,
            last_detail=payload.detail,
        )
        return
    if isinstance(payload, BudgetOverrideRequested):
        _upsert_budget_posture(
            connection,
            event,
            scope=payload.scope,
            task_id=str(payload.task_id) if payload.task_id is not None else None,
            mode=None,
            budget_json=None,
            usage_json=AutonomyBudgetUsage().model_dump_json(),
            remaining_json=None,
            last_decision="override_requested",
            last_reason=payload.reason.value,
            last_limit_name=None,
            last_detail=payload.detail,
        )
        return
    if isinstance(payload, BudgetOverrideResolved):
        _touch_session_budget_postures(
            connection,
            event,
            last_decision=f"override_{payload.decision.value}",
            last_detail=payload.reason,
        )


def _upsert_budget_posture(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    scope: str,
    task_id: str | None,
    mode: str | None,
    budget_json: str | None,
    usage_json: str,
    remaining_json: str | None,
    last_decision: str,
    last_reason: str | None,
    last_limit_name: str | None,
    last_detail: str | None,
) -> None:
    connection.execute(
        """
        insert into autonomy_budget_posture (
            session_id, task_id, scope, mode, budget_json, usage_json,
            remaining_json, last_decision, last_reason, last_limit_name,
            last_detail, updated_at, last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, task_id) do update set
            scope = excluded.scope,
            mode = coalesce(excluded.mode, autonomy_budget_posture.mode),
            budget_json = coalesce(
                excluded.budget_json,
                autonomy_budget_posture.budget_json
            ),
            usage_json = case
                when excluded.last_decision in ('exhausted', 'override_requested')
                then autonomy_budget_posture.usage_json
                else excluded.usage_json
            end,
            remaining_json = coalesce(
                excluded.remaining_json,
                autonomy_budget_posture.remaining_json
            ),
            last_decision = excluded.last_decision,
            last_reason = excluded.last_reason,
            last_limit_name = excluded.last_limit_name,
            last_detail = excluded.last_detail,
            updated_at = excluded.updated_at,
            last_sequence = excluded.last_sequence
        """,
        (
            str(event.session_id),
            task_id or "",
            scope,
            mode,
            budget_json,
            usage_json,
            remaining_json,
            last_decision,
            last_reason,
            last_limit_name,
            last_detail,
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _touch_session_budget_postures(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    last_decision: str,
    last_detail: str | None,
) -> None:
    connection.execute(
        """
        update autonomy_budget_posture
        set last_decision = ?, last_detail = ?, updated_at = ?, last_sequence = ?
        where session_id = ?
        """,
        (
            last_decision,
            last_detail,
            event.created_at.isoformat(),
            event.sequence,
            str(event.session_id),
        ),
    )


__all__ = ["_apply_budget_projection"]
