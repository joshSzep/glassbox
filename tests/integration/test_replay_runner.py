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
from glassbox.runtime import (
    EventBus,
    ReplayRunner,
    SessionSupervisor,
    TurnContextBuilder,
    TurnEngine,
)
from glassbox.store import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRuntime,
    build_ask_user_tool_registry,
    build_patch_tool_registry,
    build_read_only_tool_registry,
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
    for event in repository.read_session_events(session_id):
        if not isinstance(event.payload, ReplayArtifactRecorded):
            continue
        if event.payload.artifact_kind == "replay_model_call":
            assert event.payload.path is not None
            return Path(event.payload.path)
    raise AssertionError("expected replay_model_call artifact")


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
