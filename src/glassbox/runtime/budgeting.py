"""Autonomy budget evaluation helpers."""

from dataclasses import dataclass
from typing import Literal

from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import BudgetExhausted
from glassbox.core.ids import TaskId
from glassbox.core.ids import TurnId
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetRemaining
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode

BudgetScope = Literal["session", "task"]

_LIMIT_FIELDS = {
    "steps": "max_steps",
    "tool_calls": "max_tool_calls",
    "write_operations": "max_write_operations",
    "command_operations": "max_command_operations",
    "wall_clock_seconds": "max_wall_clock_seconds",
    "unattended_seconds": "max_unattended_seconds",
    "seconds_since_checkpoint": "checkpoint_interval_seconds",
    "retry_delay_seconds": "max_retry_delay_seconds",
    "verification_attempts": "max_verification_attempts",
    "branch_attempts": "max_branch_attempts",
    "artifact_bytes": "max_artifact_bytes",
}


@dataclass(frozen=True, slots=True)
class BudgetEvaluation:
    """Result of one budget check before work proceeds."""

    allowed: bool
    usage: AutonomyBudgetUsage
    remaining: AutonomyBudgetRemaining
    limit_name: str | None = None
    used: int | None = None
    limit: int | None = None
    reason: AutonomyEscalationReason | None = None
    detail: str | None = None

    def decision_event(
        self,
        *,
        scope: BudgetScope,
        mode: AutonomyMode,
        budget: AutonomyBudget,
        task_id: TaskId | None = None,
        turn_id: TurnId | None = None,
    ) -> BudgetDecisionRecorded:
        return BudgetDecisionRecorded(
            scope=scope,
            mode=mode,
            budget=budget,
            usage=self.usage,
            remaining=self.remaining,
            decision="allowed" if self.allowed else "exhausted",
            task_id=task_id,
            turn_id=turn_id,
            reason=self.reason,
            limit_name=self.limit_name,
            detail=self.detail,
        )

    def exhausted_event(
        self,
        *,
        scope: BudgetScope,
        task_id: TaskId | None = None,
        turn_id: TurnId | None = None,
    ) -> BudgetExhausted | None:
        if self.allowed or self.limit_name is None or self.used is None:
            return None
        assert self.limit is not None
        return BudgetExhausted(
            scope=scope,
            task_id=task_id,
            turn_id=turn_id,
            limit_name=self.limit_name,
            used=self.used,
            limit=self.limit,
            detail=self.detail,
        )


def evaluate_budget(
    budget: AutonomyBudget,
    current_usage: AutonomyBudgetUsage,
    requested_usage: AutonomyBudgetUsage | None = None,
) -> BudgetEvaluation:
    """Evaluate whether projected usage remains within budget."""

    requested = requested_usage or AutonomyBudgetUsage()
    projected = _add_usage(current_usage, requested)
    remaining = _remaining_budget(budget, projected)
    for usage_field, limit_field in _LIMIT_FIELDS.items():
        used = getattr(projected, usage_field)
        limit = getattr(budget, limit_field)
        if limit is None:
            continue
        if used > limit:
            return BudgetEvaluation(
                allowed=False,
                usage=projected,
                remaining=remaining,
                limit_name=usage_field,
                used=used,
                limit=limit,
                reason=AutonomyEscalationReason.BUDGET_EXHAUSTED,
                detail=f"{usage_field} budget exhausted: used {used}, limit {limit}",
            )
    return BudgetEvaluation(allowed=True, usage=projected, remaining=remaining)


def _add_usage(
    current: AutonomyBudgetUsage,
    requested: AutonomyBudgetUsage,
) -> AutonomyBudgetUsage:
    return AutonomyBudgetUsage(
        **{
            field_name: getattr(current, field_name) + getattr(requested, field_name)
            for field_name in _LIMIT_FIELDS
        }
    )


def _remaining_budget(
    budget: AutonomyBudget,
    usage: AutonomyBudgetUsage,
) -> AutonomyBudgetRemaining:
    def optional_remaining(limit: int | None, used: int) -> int | None:
        if limit is None:
            return None
        return max(0, limit - used)

    return AutonomyBudgetRemaining(
        steps=max(0, budget.max_steps - usage.steps),
        tool_calls=max(0, budget.max_tool_calls - usage.tool_calls),
        write_operations=max(
            0,
            budget.max_write_operations - usage.write_operations,
        ),
        command_operations=max(
            0,
            budget.max_command_operations - usage.command_operations,
        ),
        wall_clock_seconds=max(
            0,
            budget.max_wall_clock_seconds - usage.wall_clock_seconds,
        ),
        unattended_seconds=optional_remaining(
            budget.max_unattended_seconds,
            usage.unattended_seconds,
        ),
        seconds_since_checkpoint=optional_remaining(
            budget.checkpoint_interval_seconds,
            usage.seconds_since_checkpoint,
        ),
        retry_delay_seconds=optional_remaining(
            budget.max_retry_delay_seconds,
            usage.retry_delay_seconds,
        ),
        verification_attempts=max(
            0,
            budget.max_verification_attempts - usage.verification_attempts,
        ),
        branch_attempts=max(
            0,
            budget.max_branch_attempts - usage.branch_attempts,
        ),
        artifact_bytes=max(0, budget.max_artifact_bytes - usage.artifact_bytes),
    )


__all__ = ["BudgetEvaluation", "BudgetScope", "evaluate_budget"]
