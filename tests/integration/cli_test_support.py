"""Shared helpers for CLI integration tests."""

import json
import sqlite3
from pathlib import Path
from typing import Any
from typing import cast
from uuid import UUID

from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.replay import ReplayRunner
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_ask_user_tool_registry
from glassbox.tools import build_patch_tool_registry


def _run_baseline_session(
    tmp_path: Path,
    *,
    prompt: str | None = None,
) -> tuple[Path, UUID]:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    argv = ["session", "run"]
    if prompt is not None:
        argv.append(prompt)
    argv.extend(["--cwd", str(tmp_path), "--db-path", str(db_path)])

    exit_code = main(argv)
    assert exit_code == 0

    sessions = _list_sessions(db_path)
    assert len(sessions) == 1
    return db_path, sessions[0].session_id


def _seed_pending_approval(tmp_path: Path) -> tuple[Path, UUID, UUID]:
    db_path, session_id = _run_baseline_session(tmp_path)
    approval_id = new_approval_id()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=new_turn_id(),
                    reason="needs confirmation",
                    subject="run shell command",
                    policy_outcome="approve",
                    policy_risk_level="command",
                    policy_source_kind="default",
                    policy_source_label="command",
                ),
            )
        )
    finally:
        connection.close()

    return db_path, session_id, approval_id


def _seed_status_projection_details(
    tmp_path: Path,
) -> tuple[Path, UUID, UUID, UUID]:
    db_path, session_id = _run_baseline_session(tmp_path)
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    approval_id = new_approval_id()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_message_id(),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=42,
                        output_tokens=13,
                        duration_ms=600,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        policy_outcome="allow",
                        policy_risk_level="read_only",
                        policy_source_kind="default",
                        policy_source_label="read_only",
                        policy_reason="allowed: read-only tool within workspace scope",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        summary="done",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=turn_id,
                        reason="needs confirmation",
                        subject="run shell command",
                        policy_outcome="approve",
                        policy_risk_level="command",
                        policy_source_kind="default",
                        policy_source_label="command",
                    ),
                ),
            ]
        )
    finally:
        connection.close()

    return db_path, session_id, turn_id, approval_id


def _seed_pending_question_status(tmp_path: Path) -> tuple[Path, UUID, UUID]:
    db_path, session_id = _run_baseline_session(tmp_path)
    turn_id = new_turn_id()
    question_id = new_question_id()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_message_id(),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserQuestionAsked(
                        question_id=question_id,
                        turn_id=turn_id,
                        tool_call_id=new_tool_call_id(),
                        provider_tool_call_id="provider-ask-1",
                        question="What colour should I use?",
                    ),
                ),
            ]
        )
    finally:
        connection.close()

    return db_path, session_id, question_id


def _list_sessions(db_path: Path):
    connection = open_database(db_path)
    try:
        return SQLiteSessionRepository(connection).list_sessions()
    finally:
        connection.close()


def _read_session_events(db_path: Path, session_id: UUID) -> list[EventEnvelope]:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return repository.read_session_events(session_id)
    finally:
        connection.close()


def _completed_turn_ids(db_path: Path, session_id: UUID) -> list[UUID]:
    return [
        event.payload.turn_id
        for event in _read_session_events(db_path, session_id)
        if isinstance(event.payload, TurnCompleted)
        and event.payload.outcome == "completed"
    ]


def _first_replay_artifact_path(db_path: Path, session_id: UUID) -> Path:
    for event in _read_session_events(db_path, session_id):
        if not isinstance(event.payload, ReplayArtifactRecorded):
            continue
        assert event.payload.path is not None
        return db_path.parent.parent / event.payload.path
    raise AssertionError("expected replay artifact")


def _export_eval_bundle(tmp_path: Path, case_id: str) -> tuple[Path, UUID]:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    bundle_path = tmp_path / "evals" / "bundles" / f"{case_id}.json"

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
        exported_path = ReplayRunner(
            repository,
            artifact_repository,
        ).export_session_bundle(session_id, bundle_path)
    finally:
        connection.close()

    return exported_path, session_id


def _write_eval_case(
    tmp_path: Path,
    *,
    case_id: str,
    title: str,
    bundle_name: str,
    tags: list[str],
    expectation: dict[str, object] | None = None,
    release_contract: dict[str, object] | None = None,
    baseline_history: list[dict[str, object]] | None = None,
) -> Path:
    case_path = tmp_path / "evals" / "cases" / f"{case_id}.json"
    case_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "manifest_version": 1,
        "case_id": case_id,
        "title": title,
        "bundle_path": f"../bundles/{bundle_name}",
        "tags": tags,
    }
    if expectation is not None:
        payload["expectation"] = expectation
    if release_contract is not None:
        payload["release_contract"] = release_contract
    if baseline_history is not None:
        payload["baseline_history"] = baseline_history
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return case_path


def _write_eval_profiles(
    tmp_path: Path,
    *,
    profiles: list[dict[str, object]],
) -> Path:
    profiles_path = tmp_path / "evals" / "profiles.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "profiles": profiles,
    }
    profiles_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return profiles_path


def _write_eval_coverage(
    tmp_path: Path,
    *,
    profiles: list[dict[str, object]],
) -> Path:
    coverage_path = tmp_path / "evals" / "coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "capabilities": profiles,
    }
    coverage_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return coverage_path


def _write_eval_impact(
    tmp_path: Path,
    *,
    rules: list[dict[str, object]],
) -> Path:
    impact_path = tmp_path / "evals" / "impact.json"
    impact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "rules": rules,
    }
    impact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return impact_path


def _ask_user_then_text_response(
    messages: list,
    _agent_info: Any,
) -> ModelResponse:
    saw_tool_return = False
    answer: str | None = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "ask_user":
                    saw_tool_return = True
                    assert isinstance(part.content, dict)
                    answer_payload = cast(dict[str, Any], part.content)
                    answer = str(answer_payload["answer"])

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="ask_user",
                    args={"question": "What colour should I use?"},
                    tool_call_id="provider-ask-1",
                )
            ]
        )

    return ModelResponse(parts=[TextPart(content=f"I will use: {answer}")])


def _patch_then_text_response(
    messages: list,
    _agent_info: Any,
) -> ModelResponse:
    saw_tool_return = False

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "apply_patch":
                    saw_tool_return = True

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="apply_patch",
                    args={
                        "path": "hello.txt",
                        "old_text": "",
                        "new_text": "Hello from CLI chat!\n",
                    },
                    tool_call_id="provider-call-cli-chat-patch-1",
                )
            ]
        )

    return ModelResponse(parts=[TextPart(content="Patch applied.")])


def _make_ask_user_runtime_context(
    tmp_path: Path,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)

    repository = SQLiteSessionRepository(connection)
    artifacts_root = tmp_path / ".glassbox" / "artifacts"
    artifact_repository = FilesystemArtifactRepository(connection, artifacts_root)
    bus: EventBus[EventEnvelope] = EventBus()
    turn_engine = TurnEngine(
        repository,
        bus,
        TurnContextBuilder(repository),
        lambda _session: PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        ),
        lambda _session: PydanticAIModelExecutor(
            FunctionModel(
                function=_ask_user_then_text_response,
                model_name="openai:gpt-5.4",
            )
        ),
        lambda session: ToolRuntime(
            build_ask_user_tool_registry(session.cwd),
            ToolPolicyEngine(),
            ToolPolicyContext(
                workspace_root=session.cwd,
                approval_mode=ApprovalMode.NEVER,
            ),
        ),
    )
    supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
    runtime_context = RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=repository,
            artifacts=artifact_repository,
        ),
        services=RuntimeServices(session_service=supervisor),
        infrastructure=RuntimeInfrastructure(
            event_bus=bus,
            artifacts_root=artifacts_root,
        ),
    )
    return runtime_context, connection


def _make_approval_runtime_context(
    tmp_path: Path,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)

    repository = SQLiteSessionRepository(connection)
    artifacts_root = tmp_path / ".glassbox" / "artifacts"
    artifact_repository = FilesystemArtifactRepository(connection, artifacts_root)
    bus: EventBus[EventEnvelope] = EventBus()
    turn_engine = TurnEngine(
        repository,
        bus,
        TurnContextBuilder(repository),
        lambda _session: PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        ),
        lambda _session: PydanticAIModelExecutor(
            FunctionModel(
                function=_patch_then_text_response,
                model_name="openai:gpt-5.4",
            )
        ),
        lambda session: ToolRuntime(
            build_patch_tool_registry(session.cwd),
            ToolPolicyEngine(),
            ToolPolicyContext(
                workspace_root=session.cwd,
                approval_mode=ApprovalMode.CONFIRM,
            ),
        ),
    )
    supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
    runtime_context = RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=repository,
            artifacts=artifact_repository,
        ),
        services=RuntimeServices(session_service=supervisor),
        infrastructure=RuntimeInfrastructure(
            event_bus=bus,
            artifacts_root=artifacts_root,
        ),
    )
    return runtime_context, connection
