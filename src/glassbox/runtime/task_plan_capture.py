"""Structured capture of task-plan proposals from assistant output."""

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from glassbox.core.events import TaskCreated
from glassbox.core.events import TaskPlanProposed
from glassbox.core.ids import TaskId
from glassbox.core.ids import TurnId
from glassbox.core.ids import new_task_id
from glassbox.core.ids import new_task_step_id
from glassbox.core.models import TaskPlanSnapshot
from glassbox.core.models import TaskStepProposal

TASK_PLAN_FENCE = "glassbox-task-plan"
MAX_CAPTURED_TASK_STEPS = 8

_TASK_PLAN_BLOCK_RE = re.compile(
    r"```glassbox-task-plan\s*(.*?)\s*```",
    re.DOTALL,
)


class CapturedTaskStepProposal(BaseModel):
    """Model-emitted task step proposal."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class CapturedTaskPlanProposal(BaseModel):
    """Model-emitted task plan proposal."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4000)
    steps: list[CapturedTaskStepProposal] = Field(
        min_length=1,
        max_length=MAX_CAPTURED_TASK_STEPS,
    )


@dataclass(frozen=True, slots=True)
class CapturedTaskPlanEvents:
    """Canonical task-plan events derived from one assistant proposal."""

    task_id: TaskId
    created: TaskCreated
    proposed: TaskPlanProposed

    @property
    def payloads(self) -> tuple[TaskCreated, TaskPlanProposed]:
        return (self.created, self.proposed)

    def replay_details(self) -> dict[str, object]:
        return {
            "task_plan": {
                "task_id": str(self.task_id),
                "title": self.created.title,
                "step_count": len(self.proposed.plan.steps),
            }
        }


def capture_task_plan_proposal(
    assistant_text: str,
    *,
    source_turn_id: TurnId,
) -> CapturedTaskPlanEvents | None:
    """Extract one structured task-plan proposal from assistant output."""

    matches = _TASK_PLAN_BLOCK_RE.findall(assistant_text)
    if len(matches) != 1:
        return None
    proposal = _decode_task_plan(matches[0])
    if proposal is None:
        return None
    return _build_task_plan_events(proposal, source_turn_id=source_turn_id)


def build_task_plan_prompt_fragment() -> str:
    """Return model-facing instructions for optional task-plan emission."""

    return "\n".join(
        [
            "Task plan proposals:",
            (
                "- When a durable plan would help the operator inspect or resume "
                "the work later, include exactly one structured plan block."
            ),
            "- Do not imply the plan has been approved or executed.",
            f"- Keep proposed plans to {MAX_CAPTURED_TASK_STEPS} steps or fewer.",
            "- Use this exact fenced JSON shape when proposing a plan:",
            f"```{TASK_PLAN_FENCE}",
            '{"title":"...","goal":"...","steps":[{"title":"...","description":"..."}]}',
            "```",
        ]
    )


def _decode_task_plan(raw_block: str) -> CapturedTaskPlanProposal | None:
    try:
        payload: Any = json.loads(raw_block)
    except json.JSONDecodeError:
        return None
    try:
        return CapturedTaskPlanProposal.model_validate(payload)
    except ValidationError:
        return None


def _build_task_plan_events(
    proposal: CapturedTaskPlanProposal,
    *,
    source_turn_id: TurnId,
) -> CapturedTaskPlanEvents:
    task_id = new_task_id()
    steps = [
        TaskStepProposal(
            step_id=new_task_step_id(),
            title=step.title,
            description=step.description,
            order=index,
        )
        for index, step in enumerate(proposal.steps)
    ]
    created = TaskCreated(
        task_id=task_id,
        title=proposal.title,
        goal=proposal.goal,
        source_turn_id=source_turn_id,
    )
    proposed = TaskPlanProposed(
        task_id=task_id,
        plan=TaskPlanSnapshot(
            task_id=task_id,
            title=proposal.title,
            goal=proposal.goal,
            steps=steps,
        ),
    )
    return CapturedTaskPlanEvents(
        task_id=task_id,
        created=created,
        proposed=proposed,
    )


__all__ = [
    "CapturedTaskPlanEvents",
    "CapturedTaskPlanProposal",
    "CapturedTaskStepProposal",
    "MAX_CAPTURED_TASK_STEPS",
    "TASK_PLAN_FENCE",
    "build_task_plan_prompt_fragment",
    "capture_task_plan_proposal",
]
