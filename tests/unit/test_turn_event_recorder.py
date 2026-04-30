"""Focused tests for turn event recording helpers."""

from glassbox.runtime.turn_event_recorder import _tool_output_artifact_content
from glassbox.runtime.turn_event_recorder import _tool_output_artifact_kind


def test_tool_output_artifact_content_marks_timeout_as_partial() -> None:
    artifact = _tool_output_artifact_content(
        "run_command",
        {
            "exit_code": -9,
            "stdout": "ready\n",
            "stderr": "",
            "truncated": False,
            "timed_out": True,
            "cancelled": False,
            "failure_category": "timed_out",
        },
    )

    assert artifact is not None
    assert artifact["output_status"] == "partial"
    assert artifact["stdout"] == "ready\n"
    assert artifact["redacted"] is False
    assert _tool_output_artifact_kind(artifact) == (
        "tool_output_partial_complete_unredacted"
    )


def test_tool_output_artifact_content_marks_truncated_output() -> None:
    artifact = _tool_output_artifact_content(
        "run_tests",
        {
            "exit_code": 1,
            "stdout": "large output\n",
            "stderr": "",
            "truncated": True,
            "timed_out": False,
            "cancelled": False,
            "failure_category": "execution_error",
        },
    )

    assert artifact is not None
    assert artifact["output_status"] == "partial"
    assert artifact["truncated"] is True
    assert _tool_output_artifact_kind(artifact) == (
        "tool_output_partial_truncated_unredacted"
    )
