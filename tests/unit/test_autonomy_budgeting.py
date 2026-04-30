"""Tests for autonomy budget evaluation."""

from typing import Any

import pytest

from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.runtime.budgeting import evaluate_budget


def _budget(**overrides) -> AutonomyBudget:
    values: dict[str, Any] = {
        "max_steps": 5,
        "max_tool_calls": 5,
        "max_write_operations": 0,
        "max_command_operations": 0,
        "max_wall_clock_seconds": 60,
        "max_verification_attempts": 2,
        "max_branch_attempts": 1,
        "max_artifact_bytes": 1024,
        "allowed_risk_buckets": ["read_only"],
    }
    values.update(overrides)
    return AutonomyBudget(**values)


def test_evaluate_budget_allows_with_remaining_counters() -> None:
    budget = _budget(
        max_steps=3,
        max_tool_calls=4,
        max_write_operations=1,
        max_command_operations=1,
        max_wall_clock_seconds=20,
        max_unattended_seconds=15,
        checkpoint_interval_seconds=10,
        max_retry_delay_seconds=5,
        max_verification_attempts=2,
        max_branch_attempts=1,
        max_artifact_bytes=100,
        allowed_risk_buckets=["read_only", "workspace_write", "command"],
    )

    evaluation = evaluate_budget(
        budget,
        AutonomyBudgetUsage(steps=1, tool_calls=1),
        AutonomyBudgetUsage(
            steps=1,
            tool_calls=2,
            unattended_seconds=5,
            seconds_since_checkpoint=4,
            retry_delay_seconds=2,
            artifact_bytes=40,
        ),
    )

    assert evaluation.allowed is True
    assert evaluation.usage.steps == 2
    assert evaluation.usage.tool_calls == 3
    assert evaluation.remaining.steps == 1
    assert evaluation.remaining.tool_calls == 1
    assert evaluation.remaining.unattended_seconds == 10
    assert evaluation.remaining.seconds_since_checkpoint == 6
    assert evaluation.remaining.retry_delay_seconds == 3
    assert evaluation.remaining.artifact_bytes == 60


def test_evaluate_budget_blocks_unattended_window_expiry() -> None:
    budget = _budget(max_unattended_seconds=30)

    evaluation = evaluate_budget(
        budget,
        AutonomyBudgetUsage(unattended_seconds=25),
        AutonomyBudgetUsage(unattended_seconds=6),
    )

    assert evaluation.allowed is False
    assert evaluation.reason == AutonomyEscalationReason.BUDGET_EXHAUSTED
    assert evaluation.limit_name == "unattended_seconds"
    assert evaluation.used == 31
    assert evaluation.limit == 30
    assert evaluation.remaining.unattended_seconds == 0


def test_evaluate_budget_blocks_missing_checkpoint_interval() -> None:
    budget = _budget(checkpoint_interval_seconds=20)

    evaluation = evaluate_budget(
        budget,
        AutonomyBudgetUsage(seconds_since_checkpoint=19),
        AutonomyBudgetUsage(seconds_since_checkpoint=2),
    )

    assert evaluation.allowed is False
    assert evaluation.limit_name == "seconds_since_checkpoint"
    assert "seconds_since_checkpoint budget exhausted" in (evaluation.detail or "")


def test_checkpoint_approval_requires_checkpoint_interval() -> None:
    with pytest.raises(
        ValueError,
        match="checkpoint_approval_required requires checkpoint_interval_seconds",
    ):
        _budget(checkpoint_approval_required=True)


def test_evaluate_budget_blocks_when_projected_usage_exceeds_limit() -> None:
    budget = _budget(max_tool_calls=2)

    evaluation = evaluate_budget(
        budget,
        AutonomyBudgetUsage(tool_calls=2),
        AutonomyBudgetUsage(tool_calls=1),
    )

    assert evaluation.allowed is False
    assert evaluation.reason == AutonomyEscalationReason.BUDGET_EXHAUSTED
    assert evaluation.limit_name == "tool_calls"
    assert evaluation.used == 3
    assert evaluation.limit == 2
    assert evaluation.remaining.tool_calls == 0


def test_budget_evaluation_builds_decision_and_exhaustion_events() -> None:
    budget = _budget(max_steps=1)
    evaluation = evaluate_budget(
        budget,
        AutonomyBudgetUsage(steps=1),
        AutonomyBudgetUsage(steps=1),
    )

    decision_event = evaluation.decision_event(
        scope="session",
        mode=AutonomyMode.GUIDED,
        budget=budget,
    )
    exhausted_event = evaluation.exhausted_event(scope="session")

    assert decision_event.decision == "exhausted"
    assert decision_event.mode == AutonomyMode.GUIDED
    assert decision_event.reason == AutonomyEscalationReason.BUDGET_EXHAUSTED
    assert exhausted_event is not None
    assert exhausted_event.limit_name == "steps"
