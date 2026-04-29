"""Task autonomy observability collector."""

from typing import cast

from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.runtime.observability_models import TaskAutonomyObservability
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.services import SessionRepository


def build_task_autonomy_observability(
    session_repository: SessionRepository,
) -> TaskAutonomyObservability:
    task_repository = cast(TaskPlanRepository, session_repository)
    tasks = task_repository.list_tasks()
    active_tasks = [task for task in tasks if task.status == TaskPlanStatus.ACTIVE]
    blocked_tasks = [
        task
        for task in tasks
        if task.status == TaskPlanStatus.PAUSED or task.blocked_reason is not None
    ]
    failed_tasks = [task for task in tasks if task.status == TaskPlanStatus.FAILED]
    budget_exhausted_tasks = []
    for task in tasks:
        posture = session_repository.get_budget_posture(
            task.session_id,
            task_id=task.task_id,
        )
        if posture is not None and posture.last_reason == "budget_exhausted":
            budget_exhausted_tasks.append(task)
    verification_failed_count = 0
    for task in tasks:
        verification_failed_count += sum(
            1
            for verification in task_repository.list_task_verifications(
                task.session_id,
                task.task_id,
            )
            if verification.status == TaskVerificationStatus.FAILED
        )

    latest_blocked = _latest_task(blocked_tasks)
    latest_failed = _latest_task(failed_tasks)
    latest_budget_exhausted = _latest_task(budget_exhausted_tasks)
    next_actions: list[str] = []
    if active_tasks:
        next_actions.append("glassbox task list")
    if latest_blocked is not None:
        next_actions.append(f"glassbox task show {latest_blocked.task_id}")
    if latest_budget_exhausted is not None:
        next_actions.append(
            f"glassbox task continue {latest_budget_exhausted.task_id} --verify-repair"
        )
    if latest_failed is not None:
        next_actions.append(f"glassbox task show {latest_failed.task_id}")

    return TaskAutonomyObservability(
        task_count=len(tasks),
        active_count=len(active_tasks),
        blocked_count=len(blocked_tasks),
        failed_count=len(failed_tasks),
        budget_exhausted_count=len(budget_exhausted_tasks),
        verification_failed_count=verification_failed_count,
        latest_blocked_task_id=(
            str(latest_blocked.task_id) if latest_blocked is not None else None
        ),
        latest_failed_task_id=(
            str(latest_failed.task_id) if latest_failed is not None else None
        ),
        latest_budget_exhausted_task_id=(
            str(latest_budget_exhausted.task_id)
            if latest_budget_exhausted is not None
            else None
        ),
        next_actions=_dedupe(next_actions),
    )


def _latest_task(tasks):
    return max(tasks, key=lambda task: task.updated_at, default=None)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


__all__ = ["build_task_autonomy_observability"]
