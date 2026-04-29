"""Unit tests for structured task-plan capture."""

from glassbox.core import new_turn_id
from glassbox.runtime.task_plan_capture import capture_task_plan_proposal


def test_capture_task_plan_proposal_builds_canonical_events() -> None:
    turn_id = new_turn_id()
    capture = capture_task_plan_proposal(
        """
Here is the proposed plan.

```glassbox-task-plan
{
  "title": "Add task dashboard",
  "goal": "Expose durable task state in the dashboard",
  "steps": [
    {"title": "Add API client", "description": "Read task pages"},
    {"title": "Render task pane"}
  ]
}
```
""",
        source_turn_id=turn_id,
    )

    assert capture is not None
    assert capture.created.task_id == capture.proposed.task_id
    assert capture.created.source_turn_id == turn_id
    assert capture.created.title == "Add task dashboard"
    assert capture.proposed.plan.goal == "Expose durable task state in the dashboard"
    assert [step.order for step in capture.proposed.plan.steps] == [0, 1]
    assert capture.proposed.plan.steps[0].description == "Read task pages"
    assert capture.replay_details()["task_plan"] == {
        "task_id": str(capture.task_id),
        "title": "Add task dashboard",
        "step_count": 2,
    }


def test_capture_task_plan_proposal_skips_invalid_or_ambiguous_blocks() -> None:
    turn_id = new_turn_id()

    assert capture_task_plan_proposal("plain text only", source_turn_id=turn_id) is None
    assert (
        capture_task_plan_proposal(
            "```glassbox-task-plan\n{not json}\n```",
            source_turn_id=turn_id,
        )
        is None
    )
    assert (
        capture_task_plan_proposal(
            "```glassbox-task-plan\n{}\n```",
            source_turn_id=turn_id,
        )
        is None
    )
    assert (
        capture_task_plan_proposal(
            "```glassbox-task-plan\n"
            '{"title":"A","goal":"B","steps":[{"title":"C"}]}\n'
            "```\n"
            "```glassbox-task-plan\n"
            '{"title":"D","goal":"E","steps":[{"title":"F"}]}\n'
            "```",
            source_turn_id=turn_id,
        )
        is None
    )
