"""Projection read methods for SQLite repositories."""

import sqlite3
from typing import TYPE_CHECKING

import glassbox.store.sqlite_projection_health as projection_health_store
import glassbox.store.sqlite_queries as query_store
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import AutonomyBudgetPostureRecord
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import ToolExecutionStatus


class _SQLiteProjectionReadMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def inspect_session_projection_health(
        self,
        session_id: SessionId,
    ) -> ProjectionHealth:
        return projection_health_store.inspect_session_projection_health(
            self._connection,
            session_id,
        )

    def list_tool_calls(
        self,
        session_id: SessionId,
        *,
        status: ToolExecutionStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ToolCallRecord]:
        return query_store.list_tool_calls(
            self._connection,
            session_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def list_approvals(
        self,
        session_id: SessionId,
        *,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]:
        return query_store.list_approvals(self._connection, session_id, status=status)

    def list_turn_metrics(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TurnMetricsRecord]:
        return query_store.list_turn_metrics(
            self._connection,
            session_id,
            limit=limit,
            offset=offset,
        )

    def get_budget_posture(
        self,
        session_id: SessionId,
        *,
        task_id: TaskId | None = None,
    ) -> AutonomyBudgetPostureRecord | None:
        return query_store.get_budget_posture(
            self._connection,
            session_id,
            task_id=task_id,
        )


__all__ = ["_SQLiteProjectionReadMethods"]
