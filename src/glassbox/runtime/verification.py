"""Verification plan helpers, failure classification, and repair loops."""

import shlex
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from typing import cast

from glassbox.core.events import EventPayload
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepFailed
from glassbox.core.events import TaskStepStarted
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.events import TaskVerificationStarted
from glassbox.core.events import TaskVerificationStreamed
from glassbox.core.events import ToolOutputStream
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import new_task_verification_id
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.models import VerificationFailureDigest
from glassbox.core.models import VerificationPlanEntry
from glassbox.core.types import AutonomyMode
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import VerificationFailureCategory
from glassbox.runtime.budgeting import evaluate_budget
from glassbox.tools.command import RunCommandArgs
from glassbox.tools.command import RunCommandTool

VerificationLoopStatus = Literal[
    "passed",
    "failed",
    "budget_exhausted",
    "policy_blocked",
    "repeated_failure",
]
VerificationEventSink = Callable[[EventPayload], None]
VerificationArtifactRecorder = Callable[[str], ArtifactId | None]
VerificationPolicyCheck = Callable[[VerificationPlanEntry], str | None]
VerificationRepairCallback = Callable[
    [VerificationFailureDigest, int],
    Awaitable["VerificationRepairResult"],
]


@dataclass(frozen=True, slots=True)
class VerificationRepairResult:
    """Result from one bounded repair attempt."""

    step_id: TaskStepId
    summary: str
    wrote_changes: bool = False
    blocked_reason: TaskBlockedReason | None = None


@dataclass(frozen=True, slots=True)
class VerificationLoopResult:
    """Summary of one verify-repair loop."""

    status: VerificationLoopStatus
    attempts: int
    usage: AutonomyBudgetUsage
    failure: VerificationFailureDigest | None = None
    detail: str | None = None


async def run_verify_repair_loop(
    *,
    session_id: SessionId,
    task_id: TaskId,
    plan_entry: VerificationPlanEntry,
    workspace_root: Path,
    mode: AutonomyMode,
    budget: AutonomyBudget,
    current_usage: AutonomyBudgetUsage | None = None,
    max_repair_attempts: int = 0,
    event_sink: VerificationEventSink | None = None,
    repair_callback: VerificationRepairCallback | None = None,
    policy_check: VerificationPolicyCheck | None = None,
    artifact_recorder: VerificationArtifactRecorder | None = None,
) -> VerificationLoopResult:
    """Run one bounded local verification loop for a task.

    The coordinator records compact verification evidence through ``event_sink``.
    Full command output can be retained by ``artifact_recorder`` and linked from
    failure digests.
    """

    del session_id
    emit = event_sink or _ignore_event
    usage = current_usage or AutonomyBudgetUsage()
    command_tool = RunCommandTool(workspace_root)
    seen_failures: set[tuple[VerificationFailureCategory, str, int | None]] = set()
    verification = plan_entry
    max_attempts = max_repair_attempts + 1

    for attempt in range(1, max_attempts + 1):
        budget_decision = evaluate_budget(
            budget,
            usage,
            AutonomyBudgetUsage(
                tool_calls=1,
                command_operations=1,
                verification_attempts=1,
                wall_clock_seconds=verification.timeout_seconds,
            ),
        )
        emit(
            budget_decision.decision_event(
                scope="task",
                mode=mode,
                budget=budget,
                task_id=task_id,
            )
        )
        if not budget_decision.allowed:
            exhausted = budget_decision.exhausted_event(
                scope="task",
                task_id=task_id,
            )
            if exhausted is not None:
                emit(exhausted)
            return VerificationLoopResult(
                status="budget_exhausted",
                attempts=attempt - 1,
                usage=budget_decision.usage,
                detail=budget_decision.detail,
            )
        usage = budget_decision.usage

        policy_reason = policy_check(verification) if policy_check else None
        if policy_reason is not None:
            failure = VerificationFailureDigest(
                category=VerificationFailureCategory.POLICY,
                summary=policy_reason,
            )
            emit(
                TaskVerificationFailed(
                    task_id=task_id,
                    verification_id=verification.verification_id,
                    failure=failure,
                )
            )
            return VerificationLoopResult(
                status="policy_blocked",
                attempts=attempt - 1,
                usage=usage,
                failure=failure,
                detail=policy_reason,
            )

        emit(TaskVerificationPlanned(task_id=task_id, verification=verification))
        emit(
            TaskVerificationStarted(
                task_id=task_id,
                verification_id=verification.verification_id,
                check_name=verification.check_name,
                attempt=attempt,
            )
        )
        chunks: list[str] = []

        def on_chunk(
            stream: str,
            chunk: str,
            *,
            attempt_chunks: list[str] = chunks,
            verification_id=verification.verification_id,
        ) -> None:
            attempt_chunks.append(chunk)
            emit(
                TaskVerificationStreamed(
                    task_id=task_id,
                    verification_id=verification_id,
                    stream=cast(ToolOutputStream, stream),
                    chunk_summary=chunk.strip()[:2000] or f"{stream} output",
                )
            )

        command = shlex.join(verification.command)
        result = await command_tool.execute_streaming(
            RunCommandArgs(
                command=command,
                timeout=min(verification.timeout_seconds, 300),
            ),
            on_chunk,
        )
        output = "\n".join(
            part for part in [result.stdout, result.stderr, *chunks] if part
        )
        if (
            result.exit_code in verification.expected_exit_codes
            and not result.timed_out
        ):
            emit(
                TaskVerificationCompleted(
                    task_id=task_id,
                    verification_id=verification.verification_id,
                    status=TaskVerificationStatus.PASSED,
                    summary=f"{verification.check_name} passed",
                )
            )
            return VerificationLoopResult(
                status="passed",
                attempts=attempt,
                usage=usage,
            )

        failure = classify_verification_failure(
            output,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
        )
        if artifact_recorder is not None:
            artifact_id = artifact_recorder(output)
            if artifact_id is not None:
                failure = failure.model_copy(update={"artifact_id": artifact_id})
        emit(
            TaskVerificationFailed(
                task_id=task_id,
                verification_id=verification.verification_id,
                failure=failure,
            )
        )

        failure_signature = (failure.category, failure.summary, failure.exit_code)
        if failure_signature in seen_failures:
            return VerificationLoopResult(
                status="repeated_failure",
                attempts=attempt,
                usage=usage,
                failure=failure,
                detail="verification produced an identical failure twice",
            )
        seen_failures.add(failure_signature)

        if repair_callback is None or attempt >= max_attempts:
            return VerificationLoopResult(
                status="failed",
                attempts=attempt,
                usage=usage,
                failure=failure,
            )

        repair_budget = evaluate_budget(
            budget,
            usage,
            AutonomyBudgetUsage(steps=1, write_operations=1),
        )
        emit(
            repair_budget.decision_event(
                scope="task",
                mode=mode,
                budget=budget,
                task_id=task_id,
            )
        )
        if not repair_budget.allowed:
            exhausted = repair_budget.exhausted_event(scope="task", task_id=task_id)
            if exhausted is not None:
                emit(exhausted)
            return VerificationLoopResult(
                status="budget_exhausted",
                attempts=attempt,
                usage=repair_budget.usage,
                failure=failure,
                detail=repair_budget.detail,
            )
        usage = repair_budget.usage

        repair = await repair_callback(failure, attempt)
        emit(TaskStepStarted(task_id=task_id, step_id=repair.step_id))
        if repair.blocked_reason is not None:
            emit(
                TaskStepFailed(
                    task_id=task_id,
                    step_id=repair.step_id,
                    reason=repair.summary,
                    blocked_reason=repair.blocked_reason,
                )
            )
            return VerificationLoopResult(
                status="failed",
                attempts=attempt,
                usage=usage,
                failure=failure,
                detail=repair.summary,
            )
        emit(
            TaskStepCompleted(
                task_id=task_id,
                step_id=repair.step_id,
                summary=repair.summary,
            )
        )
        next_verification_id = new_task_verification_id()
        emit(
            TaskVerificationRetried(
                task_id=task_id,
                verification_id=verification.verification_id,
                next_verification_id=next_verification_id,
                attempt=attempt + 1,
                reason=repair.summary,
            )
        )
        verification = verification.model_copy(
            update={"verification_id": next_verification_id}
        )

    return VerificationLoopResult(status="failed", attempts=max_attempts, usage=usage)


def classify_verification_failure(
    output: str,
    *,
    exit_code: int | None = None,
    timed_out: bool = False,
) -> VerificationFailureDigest:
    """Return a compact evidence-based failure digest for verification output."""

    normalized = output.lower()
    category = VerificationFailureCategory.UNKNOWN
    if timed_out or "timed out" in normalized or "timeout" in normalized:
        category = VerificationFailureCategory.TIMEOUT
    elif "budget exhausted" in normalized:
        category = VerificationFailureCategory.BUDGET
    elif "policy" in normalized and ("blocked" in normalized or "denied" in normalized):
        category = VerificationFailureCategory.POLICY
    elif "mypy" in normalized or "type error" in normalized:
        category = VerificationFailureCategory.TYPECHECK
    elif "ruff" in normalized or "flake8" in normalized or "lint" in normalized:
        category = VerificationFailureCategory.LINT
    elif "build failed" in normalized or "packaging" in normalized:
        category = VerificationFailureCategory.PACKAGE
    elif "connection refused" in normalized or "no such file" in normalized:
        category = VerificationFailureCategory.INFRASTRUCTURE
    elif "flaky" in normalized or "rerun" in normalized:
        category = VerificationFailureCategory.FLAKY
    elif "assert" in normalized or "failed" in normalized:
        category = VerificationFailureCategory.ASSERTION

    first_relevant_line = _first_nonempty_line(output)
    summary = first_relevant_line or (
        f"verification exited with code {exit_code}"
        if exit_code is not None
        else "verification failed without output"
    )
    return VerificationFailureDigest(
        category=category,
        summary=summary[:4000],
        exit_code=exit_code,
        timed_out=timed_out,
        first_relevant_line=first_relevant_line,
    )


def _first_nonempty_line(output: str) -> str | None:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:1000]
    return None


def _ignore_event(_event: EventPayload) -> None:
    return None


__all__ = [
    "VerificationArtifactRecorder",
    "VerificationEventSink",
    "VerificationLoopResult",
    "VerificationLoopStatus",
    "VerificationPolicyCheck",
    "VerificationRepairCallback",
    "VerificationRepairResult",
    "classify_verification_failure",
    "run_verify_repair_loop",
]
