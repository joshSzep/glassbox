"""Unit tests for Glassbox system prompt composition."""

from uuid import uuid4

from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
from glassbox.core.types import SessionStatus
from glassbox.llm import build_system_prompt
from glassbox.llm import build_tool_usage_prompt_fragment
from glassbox.runtime.context_builder import ArtifactBackedContextSnapshot
from glassbox.runtime.context_builder import ArtifactBackedContextSummarySnapshot
from glassbox.runtime.context_builder import CheckpointResumeSnapshot
from glassbox.runtime.context_builder import ContextCompactionContextItemSnapshot
from glassbox.runtime.context_builder import ContextCompactionContextSnapshot
from glassbox.runtime.context_builder import PolicyContext
from glassbox.runtime.context_builder import RepositoryIntelligenceContextItemSnapshot
from glassbox.runtime.context_builder import RepositoryIntelligenceContextSnapshot
from glassbox.runtime.context_builder import RepositoryIntelligenceContextSourceSnapshot
from glassbox.runtime.context_builder import ToolSchema
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.context_builder import WorkingSetItemSnapshot
from glassbox.runtime.context_builder import WorkingSetSnapshot


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
        artifact_context=ArtifactBackedContextSnapshot(
            summaries=[
                ArtifactBackedContextSummarySnapshot(
                    summary_kind="pytest_failure_digest",
                    source_tool_name="run_tests",
                    artifact_kind="context_pytest_failure_digest",
                    artifact_path=(
                        ".glassbox/sessions/session-123/artifacts/failure-digest.json"
                    ),
                    summary=(
                        "1 failing test(s) for tests/unit/test_context_builder.py"
                    ),
                    target_paths=["tests/unit/test_context_builder.py"],
                    failing_tests=[
                        "tests/unit/test_context_builder.py::test_example_failure"
                    ],
                )
            ]
        ),
    )

    prompt = build_system_prompt(turn_context)

    assert "You are Glassbox" in prompt
    assert "Task plan proposals:" in prompt
    assert "```glassbox-task-plan" in prompt
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
    assert "Artifact-backed context:" in prompt
    assert "pytest_failure_digest" in prompt
    assert "tests/unit/test_context_builder.py::test_example_failure" in prompt
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
    assert "Artifact-backed context:" not in prompt


def test_build_system_prompt_includes_checkpoint_resume_caveats() -> None:
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=None,
        last_sequence=8,
        transcript=[],
        available_tools=[],
        policy=PolicyContext(approval_mode="confirm"),
        checkpoint_context=CheckpointResumeSnapshot(
            checkpoint_id=uuid4(),
            objective="Finish the long task",
            current_phase=LongRunPhase.CHECKPOINTING,
            completed_step="Stored checkpoint projection",
            next_action="Refresh checkpoint before continuing",
            recovery_guidance="Inspect events after checkpoint",
            source_start_sequence=1,
            source_end_sequence=4,
            checkpoint_sequence=5,
            latest_session_sequence=8,
            status="stale",
            safe_to_use=False,
            context_source="replay",
            reason="events were recorded after the latest checkpoint",
            limitations=["checkpoint source range is stale"],
        ),
    )

    prompt = build_system_prompt(turn_context)

    assert "Checkpoint resume context:" in prompt
    assert "Status: stale." in prompt
    assert "Context source: replay." in prompt
    assert "events were recorded after the latest checkpoint" in prompt
    assert "source events 1-4" in prompt
    assert "Do not treat this checkpoint as an active continuation point" in prompt


def test_build_system_prompt_includes_fresh_context_compactions() -> None:
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=None,
        last_sequence=8,
        transcript=[],
        available_tools=[],
        policy=PolicyContext(approval_mode="confirm"),
        context_compactions=ContextCompactionContextSnapshot(
            items=[
                ContextCompactionContextItemSnapshot(
                    compaction_id=uuid4(),
                    scope=ContextCompactionScope.TRANSCRIPT,
                    artifact_id=uuid4(),
                    source_start_sequence=1,
                    source_end_sequence=8,
                    summary="Compacted decisions and verification posture.",
                    freshness=ContextCompactionFreshness.FRESH,
                    limitations=["Raw transcript omitted."],
                )
            ],
            stale_item_count=1,
        ),
    )

    prompt = build_system_prompt(turn_context)

    assert "Context compactions:" in prompt
    assert "[transcript] Compacted decisions and verification posture." in prompt
    assert "source events 1-8" in prompt
    assert "Raw transcript omitted." in prompt
    assert "1 stale compaction(s) excluded." in prompt


def test_build_system_prompt_includes_repository_intelligence_context() -> None:
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=None,
        last_sequence=4,
        transcript=[],
        available_tools=[],
        policy=PolicyContext(approval_mode="confirm"),
        repository_intelligence=RepositoryIntelligenceContextSnapshot(
            status="fresh",
            sources=[
                RepositoryIntelligenceContextSourceSnapshot(
                    source_name="path-to-verification",
                    source_kind="verification_recommendation",
                    freshness="fresh",
                    confidence="medium",
                    included=True,
                    provenance="eval recommend",
                )
            ],
            items=[
                RepositoryIntelligenceContextItemSnapshot(
                    item_kind="likely_test",
                    title="context builder tests",
                    summary="Run focused context and prompt tests.",
                    source_names=["path-to-verification"],
                    confidence="medium",
                )
            ],
            safe_next_actions=[
                "uv run pytest tests/unit/test_context_builder.py "
                "tests/unit/test_llm_prompts.py"
            ],
        ),
    )

    prompt = build_system_prompt(turn_context)

    assert "Repository intelligence: fresh; schema 1; 1 item(s)" in prompt
    assert "[likely_test] context builder tests" in prompt
    assert "path-to-verification=fresh/medium" in prompt
    assert "uv run pytest tests/unit/test_context_builder.py" in prompt


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
