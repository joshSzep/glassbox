"""Unit tests for Glassbox system prompt composition."""

from __future__ import annotations

from uuid import uuid4

from glassbox.core.types import SessionStatus
from glassbox.llm import build_system_prompt, build_tool_usage_prompt_fragment
from glassbox.runtime import (
    PolicyContext,
    ToolSchema,
    TurnContext,
    WorkingSetItemSnapshot,
    WorkingSetSnapshot,
)


def test_build_system_prompt_includes_policy_tools_repo_and_memory() -> None:
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=uuid4(),
        last_sequence=9,
        transcript=[],
        available_tools=[
            ToolSchema(
                name="shell",
                description="Run a shell command.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                },
            ),
            ToolSchema(
                name="read_file",
                description="Read a file from disk.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
        ],
        policy=PolicyContext(
            approval_mode="on-request",
            pending_approval_id=uuid4(),
        ),
        repo_context="Repository root: /workspace/glassbox",
        memory_notes=[
            "Prefer targeted validation.",
            "Avoid claiming unseen file changes.",
        ],
        working_set=WorkingSetSnapshot(
            items=[
                WorkingSetItemSnapshot(
                    subject_kind="file",
                    subject="src/glassbox/runtime/context_builder.py",
                    summary="recently targeted workspace path",
                    reasons=[
                        "apply_patch targeted src/glassbox/runtime/context_builder.py"
                    ],
                    signal_types=["tool_request_path"],
                )
            ]
        ),
    )

    prompt = build_system_prompt(turn_context)

    assert "You are Glassbox" in prompt
    assert "Approval policy:" in prompt
    assert "Current approval mode: on-request." in prompt
    assert "Pending approval id:" in prompt
    assert "Repository context:" in prompt
    assert "Repository root: /workspace/glassbox" in prompt
    assert "Memory notes:" in prompt
    assert "Prefer targeted validation." in prompt
    assert "Avoid claiming unseen file changes." in prompt
    assert "Working set:" in prompt
    assert "[file] src/glassbox/runtime/context_builder.py" in prompt
    assert prompt.index("read_file: Read a file from disk.") < prompt.index(
        "shell: Run a shell command."
    )


def test_build_system_prompt_handles_missing_optional_context() -> None:
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=None,
        last_sequence=0,
        transcript=[],
        available_tools=[],
        policy=PolicyContext(approval_mode="never"),
    )

    prompt = build_system_prompt(turn_context)

    assert "No tools are currently available for this turn." in prompt
    assert "No approval request is currently pending." in prompt
    assert "Repository context:" not in prompt
    assert "Memory notes:" not in prompt
    assert "Working set:" not in prompt


def test_tool_usage_fragment_is_stable_and_includes_schema() -> None:
    fragment = build_tool_usage_prompt_fragment(
        [
            ToolSchema(
                name="write_file",
                description="Write text to a file.",
                parameters_json_schema={
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "type": "object",
                },
            ),
            ToolSchema(
                name="apply_patch",
                description="Edit existing files with a patch.",
                parameters_json_schema={
                    "properties": {"patch": {"type": "string"}},
                    "type": "object",
                },
            ),
        ]
    )

    assert fragment.index(
        "apply_patch: Edit existing files with a patch."
    ) < fragment.index("write_file: Write text to a file.")
    assert (
        'Schema: {"properties": {"patch": {"type": "string"}}, "type": "object"}'
        in fragment
    )
