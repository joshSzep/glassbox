"""Integration tests for the offline deterministic replay runner."""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope, SessionConfig
from glassbox.core.events import (
    ApprovalRequested,
    ReplayArtifactRecorded,
    UserQuestionAsked,
)
from glassbox.core.types import ApprovalDecision
from glassbox.llm import (
    ModelProviderConfig,
    PydanticAIModelAdapter,
    PydanticAIModelExecutor,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.eval_runner import EvalRunner
from glassbox.runtime.replay import ReplayRunner
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
)
from glassbox.store.sqlite import initialize_database, open_database
from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRuntime,
    build_ask_user_tool_registry,
    build_patch_tool_registry,
    build_read_only_tool_registry,
    build_workflow_tool_registry,
)


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _build_turn_engine(
    repository: SQLiteSessionRepository,
    artifact_repository: FilesystemArtifactRepository,
    bus: EventBus[EventEnvelope],
    *,
    model_fn: Callable[..., ModelResponse],
    model_settings: dict[str, Any] | None = None,
    tool_runtime_factory: Callable[[Any], ToolRuntime] | None = None,
) -> TurnEngine:
    return TurnEngine(
        repository,
        bus,
        TurnContextBuilder(repository),
        lambda _session: PydanticAIModelAdapter(
            ModelProviderConfig(
                provider="openai",
                model_name="gpt-5.4",
                model_settings=model_settings or {},
            )
        ),
        lambda _session: PydanticAIModelExecutor(
            FunctionModel(function=model_fn, model_name="openai:gpt-5.4")
        ),
        tool_runtime_factory,
        artifact_repository=artifact_repository,
    )


def _replay_model_call_artifact_path(
    repository: SQLiteSessionRepository,
    session_id,
) -> Path:
    return _replay_model_call_artifact_paths(repository, session_id)[0]


def _replay_model_call_artifact_paths(
    repository: SQLiteSessionRepository,
    session_id,
) -> list[Path]:
    paths: list[Path] = []
    for event in repository.read_session_events(session_id):
        if not isinstance(event.payload, ReplayArtifactRecorded):
            continue
        if event.payload.artifact_kind == "replay_model_call":
            assert event.payload.path is not None
            paths.append(Path(event.payload.path))
    if not paths:
        raise AssertionError("expected replay_model_call artifact")
    return paths


def _first_replay_artifact_path(
    repository: SQLiteSessionRepository,
    session_id,
) -> Path:
    for event in repository.read_session_events(session_id):
        if isinstance(event.payload, ReplayArtifactRecorded):
            assert event.payload.path is not None
            return Path(event.payload.path)
    raise AssertionError("expected replay artifact")


def _text_only_response(messages: list, _agent_info: Any) -> ModelResponse:
    user_prompt = None
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                user_prompt = part.content
    assert user_prompt == "Inspect the repo"
    return ModelResponse(parts=[TextPart(content="Repo inspection complete.")])


def _read_file_then_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    saw_tool_return = False
    tool_content = None

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "read_file":
                saw_tool_return = True
                tool_content = part.content

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="read_file",
                    args={"path": "README.md", "start_line": 1, "end_line": 1},
                    tool_call_id="provider-call-read-1",
                )
            ]
        )

    assert isinstance(tool_content, dict)
    assert tool_content["content"] == "Glassbox tool loop"
    return ModelResponse(parts=[TextPart(content="README says: Glassbox tool loop")])


def _patch_then_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "apply_patch":
                return ModelResponse(parts=[TextPart(content="Patch applied.")])

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="apply_patch",
                args={
                    "path": "hello.txt",
                    "old_text": "",
                    "new_text": "Hello, world!\n",
                },
                tool_call_id="provider-call-patch-1",
            )
        ]
    )


def _ask_user_then_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "ask_user":
                assert isinstance(part.content, dict)
                answer = str(part.content["answer"])
                return ModelResponse(parts=[TextPart(content=f"I will use: {answer}")])

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="ask_user",
                args={"question": "What colour should I use?"},
                tool_call_id="provider-ask-1",
            )
        ]
    )


def _run_tests_then_use_digest_response(
    messages: list, _agent_info: Any
) -> ModelResponse:
    saw_tool_return = False
    user_prompt = None
    tool_content = None

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                user_prompt = part.content
            if isinstance(part, ToolReturnPart) and part.tool_name == "run_tests":
                saw_tool_return = True
                tool_content = part.content

    assert user_prompt is not None
    if user_prompt == "Run the targeted tests":
        if not saw_tool_return:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="run_tests",
                        args={"paths": ["test_fail.py"]},
                        tool_call_id="provider-call-run-tests-1",
                    )
                ]
            )

        assert isinstance(tool_content, dict)
        assert tool_content["failed"] == 1
        return ModelResponse(parts=[TextPart(content="Captured failing test.")])

    assert user_prompt == "Summarize the latest failure"
    return ModelResponse(parts=[TextPart(content="Latest failure summarized.")])


def test_replay_runner_matches_text_only_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "exact_match"
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_matches_tool_assisted_session(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Glassbox tool loop\n", encoding="utf-8")

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_read_file_then_text_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "exact_match"
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_matches_approval_resume_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_patch_then_text_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_patch_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Patch the repo")
            approval_payload = next(
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ApprovalRequested)
            )
            await supervisor.resolve_approval(
                state.session_id,
                approval_payload.approval_id,
                ApprovalDecision.APPROVED,
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "exact_match"
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_matches_ask_user_resume_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_ask_user_then_text_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_ask_user_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.NEVER,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="never",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Pick a colour")
            question_payload = next(
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, UserQuestionAsked)
            )
            await supervisor.provide_user_answer(
                state.session_id,
                question_payload.question_id,
                "blue",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "exact_match"
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_preserves_artifact_backed_context_under_replay(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_fail.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_run_tests_then_use_digest_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_workflow_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Run the targeted tests",
            )
            approval_payload = next(
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ApprovalRequested)
            )
            await supervisor.resolve_approval(
                state.session_id,
                approval_payload.approval_id,
                ApprovalDecision.APPROVED,
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Summarize the latest failure",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "behavioral_drift"
        assert result.mismatches == ["event_families drift"]
        assert result.triage is not None
        assert result.triage.classification == "behavioral_drift"
        assert result.triage.first_relevant_change == "event_families drift"
        assert result.triage.impacted_dimensions == ["event_families"]
        assert result.triage.recommended_inspection_path is not None
        assert "event stream" in result.triage.recommended_inspection_path

    asyncio.run(scenario())


def test_replay_runner_reports_manifest_drift(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _replay_model_call_artifact_path(
                repository,
                state.session_id,
            )
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_payload["prepared_turn"]["user_prompt"] = "Unexpected prompt"
            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "manifest_drift"
        assert result.message is not None
        assert result.triage is not None
        assert result.triage.classification == "manifest_drift"
        assert result.triage.drift_sources == ["prepared_turn"]
        assert result.triage.recommended_inspection_path is not None
        assert "prepared turn manifest" in result.triage.recommended_inspection_path

    asyncio.run(scenario())


def test_replay_runner_reports_enriched_context_manifest_drift(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                state.session_id,
                category="operator",
                message="Stay inside src/glassbox",
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _replay_model_call_artifact_path(
                repository,
                state.session_id,
            )
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_payload["turn_context"]["memory_notes"] = [
                "[operator] Unexpected note"
            ]
            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "manifest_drift"
        assert result.message is not None
        assert (
            "recorded enriched context source drifted: runtime_notes" in result.message
        )
        assert result.triage is not None
        assert result.triage.classification == "context_source_drift"
        assert result.triage.drift_sources == ["runtime_notes"]
        assert result.triage.recommended_inspection_path is not None
        assert "runtime note inputs" in result.triage.recommended_inspection_path

    asyncio.run(scenario())


def test_replay_runner_reports_artifact_backed_context_manifest_drift(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_fail.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_run_tests_then_use_digest_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_workflow_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Run the targeted tests",
            )
            approval_payload = next(
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ApprovalRequested)
            )
            await supervisor.resolve_approval(
                state.session_id,
                approval_payload.approval_id,
                ApprovalDecision.APPROVED,
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Summarize the latest failure",
            )

            artifact_paths = _replay_model_call_artifact_paths(
                repository,
                state.session_id,
            )
            artifact_path = tmp_path / artifact_paths[-1]
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_payload["turn_context"]["artifact_context"]["summaries"][0][
                "failing_tests"
            ] = ["unexpected::failure"]
            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "manifest_drift"
        assert result.message is not None
        assert (
            "recorded enriched context source drifted: pytest_failure_digest"
            in result.message
        )
        assert result.triage is not None
        assert result.triage.classification == "context_source_drift"
        assert result.triage.drift_sources == ["pytest_failure_digest"]
        assert result.triage.recommended_inspection_path is not None
        assert (
            "pytest failure digest artifact"
            in result.triage.recommended_inspection_path
        )

    asyncio.run(scenario())


def test_replay_runner_preserves_older_artifact_enriched_context_fallback(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                state.session_id,
                category="operator",
                message="Stay inside src/glassbox",
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _replay_model_call_artifact_path(
                repository,
                state.session_id,
            )
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_payload.pop("enriched_context_sources", None)
            artifact_payload["turn_context"]["memory_notes"] = [
                "[operator] Unexpected note"
            ]
            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "manifest_drift"
        assert result.message is not None
        assert (
            "enriched context no longer matches recorded replay manifest"
            in result.message
        )

    asyncio.run(scenario())


def test_replay_runner_replays_runtime_note_actions_and_inherited_child_notes(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                parent_state.session_id,
                category="operator",
                message="Stay inside src/glassbox",
            )
            await supervisor.submit_user_message(
                parent_state.session_id,
                "Inspect the repo",
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.record_runtime_note(
                forked_session.child_session_id,
                category="runtime",
                message="Child branch prefers narrow diffs",
            )
            await supervisor.submit_user_message(
                forked_session.child_session_id,
                "Inspect the repo",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                forked_session.child_session_id
            )
        finally:
            connection.close()

        assert result.outcome == "exact_match"
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_reports_missing_artifact(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _first_replay_artifact_path(
                repository,
                state.session_id,
            )
            artifact_path.unlink()

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "replay_failure"
        assert result.message is not None

    asyncio.run(scenario())


def test_replay_runner_reports_unsupported_manifest_version(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _replay_model_call_artifact_path(
                repository,
                state.session_id,
            )
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_payload["manifest_version"] = 2
            artifact_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "unsupported_session"
        assert result.message is not None

    asyncio.run(scenario())


def test_replay_runner_reports_corrupt_artifact_payload(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = tmp_path / _replay_model_call_artifact_path(
                repository,
                state.session_id,
            )
            artifact_path.write_text("not valid json", encoding="utf-8")

            result = await ReplayRunner(repository, artifact_repository).replay_session(
                state.session_id
            )
        finally:
            connection.close()

        assert result.outcome == "replay_failure"
        assert result.message is not None

    asyncio.run(scenario())


def test_replay_runner_exports_bundle_and_replays_without_source_database(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-workspace"
    source_root.mkdir()
    (source_root / "README.md").write_text("Glassbox tool loop\n", encoding="utf-8")
    portable_root = tmp_path / "portable-workspace"
    portable_root.mkdir()
    bundle_path = tmp_path / "bundles" / "read-file-session.json"

    async def scenario() -> None:
        connection = _open_initialized_database(source_root)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, source_root)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_read_file_then_text_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=source_root,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            runner = ReplayRunner(repository, artifact_repository)
            exported_path = runner.export_session_bundle(state.session_id, bundle_path)
            result = await ReplayRunner().replay_bundle_file(
                exported_path,
                workspace_root=portable_root,
            )
        finally:
            connection.close()

        shutil.rmtree(source_root)

        assert exported_path == bundle_path.resolve()
        assert result.outcome == "exact_match"
        assert result.source_session_id == state.session_id
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_exports_forked_child_bundle_with_imported_history(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-workspace"
    source_root.mkdir()
    portable_root = tmp_path / "portable-workspace"
    portable_root.mkdir()
    bundle_path = tmp_path / "bundles" / "forked-child-session.json"

    async def scenario() -> None:
        connection = _open_initialized_database(source_root)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, source_root)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=source_root,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                parent_state.session_id,
                "Inspect the repo",
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.submit_user_message(
                forked_session.child_session_id,
                "Inspect the repo",
            )

            runner = ReplayRunner(repository, artifact_repository)
            exported_path = runner.export_session_bundle(
                forked_session.child_session_id,
                bundle_path,
            )
            result = await ReplayRunner().replay_bundle_file(
                exported_path,
                workspace_root=portable_root,
            )
        finally:
            connection.close()

        shutil.rmtree(source_root)

        assert exported_path == bundle_path.resolve()
        assert result.outcome == "exact_match"
        assert result.source_session_id == forked_session.child_session_id
        assert result.replay == result.baseline

    asyncio.run(scenario())


def test_replay_runner_reports_post_fork_drift_separately_from_inherited_history(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-workspace"
    source_root.mkdir()
    portable_root = tmp_path / "portable-workspace"
    portable_root.mkdir()
    bundle_path = tmp_path / "bundles" / "forked-child-session-drift.json"

    async def scenario() -> None:
        connection = _open_initialized_database(source_root)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, source_root)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=source_root,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                parent_state.session_id,
                "Inspect the repo",
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.submit_user_message(
                forked_session.child_session_id,
                "Inspect the repo",
            )

            ReplayRunner(repository, artifact_repository).export_session_bundle(
                forked_session.child_session_id,
                bundle_path,
            )
        finally:
            connection.close()

        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload["baseline"]["transcript"][-1]["parts"][0]["text"] = (
            "Unexpected post-fork text"
        )
        payload["baseline"]["post_fork_transcript"][-1]["parts"][0]["text"] = (
            "Unexpected post-fork text"
        )
        bundle_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

        result = await ReplayRunner().replay_bundle_file(
            bundle_path,
            workspace_root=portable_root,
        )

        assert result.outcome == "behavioral_drift"
        assert result.mismatches == ["transcript drift", "post_fork_transcript drift"]

    asyncio.run(scenario())


def test_eval_runner_executes_forked_child_bundle_case(tmp_path: Path) -> None:
    source_root = tmp_path / "source-workspace"
    source_root.mkdir()
    cases_dir = tmp_path / "evals" / "cases"
    cases_dir.mkdir(parents=True)
    bundles_dir = tmp_path / "evals" / "bundles"
    bundles_dir.mkdir(parents=True)
    bundle_path = bundles_dir / "forked-child-session.json"
    case_path = cases_dir / "forked-child-session.json"
    output_dir = tmp_path / ".glassbox" / "evals" / "test-run"

    async def scenario() -> None:
        connection = _open_initialized_database(source_root)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, source_root)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=source_root,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                parent_state.session_id,
                "Inspect the repo",
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.submit_user_message(
                forked_session.child_session_id,
                "Inspect the repo",
            )

            ReplayRunner(repository, artifact_repository).export_session_bundle(
                forked_session.child_session_id,
                bundle_path,
            )
        finally:
            connection.close()

        case_path.write_text(
            json.dumps(
                {
                    "case_id": "forked-child-session",
                    "title": "Forked child session replay bundle",
                    "bundle_path": "../bundles/forked-child-session.json",
                    "tags": ["branching", "replay"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = await EvalRunner().run_suite(
            tmp_path,
            case_ids=["forked-child-session"],
            output_dir=output_dir,
        )

        assert result.selected_case_count == 1
        assert result.passed_case_count == 1
        assert result.failed_case_count == 0
        assert result.exit_code == 0
        assert result.outcome_counts["exact_match"] == 1
        assert result.cases[0].case_id == "forked-child-session"
        assert result.cases[0].replay_outcome == "exact_match"
        assert result.cases[0].passed is True

    asyncio.run(scenario())


def test_eval_runner_allows_selected_invariants_for_context_sensitive_bundle(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_fail.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )
    cases_dir = tmp_path / "evals" / "cases"
    cases_dir.mkdir(parents=True)
    bundles_dir = tmp_path / "evals" / "bundles"
    bundles_dir.mkdir(parents=True)
    bundle_path = bundles_dir / "context.artifact.json"
    case_path = cases_dir / "context.artifact.json"
    output_dir = tmp_path / ".glassbox" / "evals" / "context-run"

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_run_tests_then_use_digest_response,
                tool_runtime_factory=lambda session: ToolRuntime(
                    build_workflow_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Run the targeted tests",
            )
            approval_payload = next(
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ApprovalRequested)
            )
            await supervisor.resolve_approval(
                state.session_id,
                approval_payload.approval_id,
                ApprovalDecision.APPROVED,
            )
            await supervisor.submit_user_message(
                state.session_id,
                "Summarize the latest failure",
            )

            ReplayRunner(repository, artifact_repository).export_session_bundle(
                state.session_id,
                bundle_path,
            )
        finally:
            connection.close()

        bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle_payload["baseline"]["transcript"][-1]["parts"][0]["text"] = (
            "Unexpected relaxed transcript"
        )
        bundle_path.write_text(
            json.dumps(bundle_payload, indent=2) + "\n",
            encoding="utf-8",
        )

        case_path.write_text(
            json.dumps(
                {
                    "case_id": "context.artifact",
                    "title": "Artifact-backed context can ignore transcript-only drift",
                    "bundle_path": "../bundles/context.artifact.json",
                    "tags": ["context"],
                    "expectation": {
                        "mode": "selected_invariants",
                        "invariants": [
                            "tool_calls",
                            "approvals",
                            "final_state",
                        ],
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = await EvalRunner().run_suite(
            tmp_path,
            case_ids=["context.artifact"],
            output_dir=output_dir,
        )

        assert result.selected_case_count == 1
        assert result.passed_case_count == 1
        assert result.failed_case_count == 0
        assert result.exit_code == 0
        assert result.cases[0].replay_outcome == "behavioral_drift"
        assert result.cases[0].passed is True
        assert sorted(result.cases[0].ignored_mismatches) == [
            "event_families drift",
            "transcript drift",
        ]
        assert result.cases[0].message == (
            "selected invariants matched; ignored drift was limited to "
            "transcript drift, event_families drift"
        )
        assert result.cases[0].selected_invariant_interpretation == (
            "selected invariants matched; ignored drift was limited to "
            "transcript drift, event_families drift"
        )

    asyncio.run(scenario())


def test_replay_runner_reports_missing_bundle_file(tmp_path: Path) -> None:
    result = asyncio.run(
        ReplayRunner().replay_bundle_file(
            tmp_path / "missing-replay-bundle.json",
            workspace_root=tmp_path,
        )
    )

    assert result.outcome == "replay_failure"
    assert result.message is not None
    assert "missing replay bundle file" in result.message


def test_replay_runner_reports_unsupported_bundle_version(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            ReplayRunner(repository, artifact_repository).export_session_bundle(
                state.session_id,
                bundle_path,
            )
        finally:
            connection.close()

    asyncio.run(scenario())

    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["bundle_version"] = 2
    bundle_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = asyncio.run(
        ReplayRunner().replay_bundle_file(bundle_path, workspace_root=tmp_path)
    )

    assert result.outcome == "unsupported_session"
    assert result.message == "unsupported replay bundle version: 2"


def test_replay_runner_exported_bundles_preserve_redaction_and_omit_artifact_paths(
    tmp_path: Path,
) -> None:
    bundle_path = tmp_path / "bundle.json"

    async def scenario() -> Path:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository,
                artifact_repository,
                bus,
                model_fn=_text_only_response,
                model_settings={
                    "api_key": "super-secret-token",
                    "temperature": 0.2,
                },
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)

            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            artifact_path = _first_replay_artifact_path(repository, state.session_id)
            ReplayRunner(repository, artifact_repository).export_session_bundle(
                state.session_id,
                bundle_path,
            )
            return artifact_path
        finally:
            connection.close()

    artifact_path = asyncio.run(scenario())
    bundle_text = bundle_path.read_text(encoding="utf-8")

    assert "super-secret-token" not in bundle_text
    assert "[REDACTED]" in bundle_text
    assert str(artifact_path) not in bundle_text
    assert str((tmp_path / artifact_path).resolve()) not in bundle_text
