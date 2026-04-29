"""Tests for the budgeted verify-repair coordinator."""

import asyncio
import sys
from pathlib import Path

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyMode
from glassbox.core import EventPayload
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationRetried
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.verification import VerificationRepairResult
from glassbox.runtime.verification import run_verify_repair_loop


def test_verify_repair_loop_repairs_and_reruns_until_success(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    events: list[EventPayload] = []
    plan_entry = _plan_entry(
        tmp_path,
        (
            "from pathlib import Path; import sys; "
            "sys.exit(0 if Path('marker.txt').exists() else 1)"
        ),
    )

    async def repair(_failure, _attempt: int) -> VerificationRepairResult:
        marker.write_text("fixed\n", encoding="utf-8")
        return VerificationRepairResult(
            step_id=new_task_step_id(),
            summary="Created missing marker file.",
            wrote_changes=True,
        )

    result = asyncio.run(
        run_verify_repair_loop(
            session_id=new_session_id(),
            task_id=new_task_id(),
            plan_entry=plan_entry,
            workspace_root=tmp_path,
            mode=AutonomyMode.TEST_DRIVEN,
            budget=_budget(),
            max_repair_attempts=1,
            event_sink=events.append,
            repair_callback=repair,
        )
    )

    assert result.status == "passed"
    assert result.attempts == 2
    assert any(isinstance(event, TaskVerificationFailed) for event in events)
    assert any(isinstance(event, TaskVerificationRetried) for event in events)


def test_verify_repair_loop_stops_on_repeated_failure(tmp_path: Path) -> None:
    events: list[EventPayload] = []
    plan_entry = _plan_entry(tmp_path, "import sys; print('same failure'); sys.exit(1)")

    async def repair(_failure, _attempt: int) -> VerificationRepairResult:
        return VerificationRepairResult(
            step_id=new_task_step_id(),
            summary="No deterministic repair available.",
        )

    result = asyncio.run(
        run_verify_repair_loop(
            session_id=new_session_id(),
            task_id=new_task_id(),
            plan_entry=plan_entry,
            workspace_root=tmp_path,
            mode=AutonomyMode.TEST_DRIVEN,
            budget=_budget(max_write_operations=2),
            max_repair_attempts=2,
            event_sink=events.append,
            repair_callback=repair,
        )
    )

    assert result.status == "repeated_failure"
    assert result.attempts == 2


def test_verify_repair_loop_stops_on_budget_exhaustion(tmp_path: Path) -> None:
    plan_entry = _plan_entry(tmp_path, "print('would run')")

    result = asyncio.run(
        run_verify_repair_loop(
            session_id=new_session_id(),
            task_id=new_task_id(),
            plan_entry=plan_entry,
            workspace_root=tmp_path,
            mode=AutonomyMode.GUIDED,
            budget=_budget(
                max_write_operations=0,
                max_command_operations=0,
                allowed_risk_buckets=["read_only"],
            ),
        )
    )

    assert result.status == "budget_exhausted"
    assert result.attempts == 0


def _plan_entry(tmp_path: Path, script: str) -> VerificationPlanEntry:
    return VerificationPlanEntry(
        verification_id=new_task_verification_id(),
        check_name="python check",
        kind=VerificationCheckKind.TEST,
        command=[sys.executable, "-c", script],
        source=VerificationPlanSource.OPERATOR,
        rationale="Unit test check.",
        timeout_seconds=30,
        changed_paths=[tmp_path / "marker.txt"],
    )


def _budget(**overrides) -> AutonomyBudget:
    values = {
        "max_steps": 3,
        "max_tool_calls": 5,
        "max_write_operations": 1,
        "max_command_operations": 5,
        "max_wall_clock_seconds": 120,
        "max_verification_attempts": 5,
        "max_branch_attempts": 0,
        "max_artifact_bytes": 1024 * 1024,
        "allowed_risk_buckets": ["read_only", "workspace_write", "command"],
    }
    values.update(overrides)
    return AutonomyBudget.model_validate(values)
