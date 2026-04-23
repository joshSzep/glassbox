"""Integration tests for the approval pause/resume workflow (GBX-070)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope, SessionConfig
from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    ReplayArtifactRecorded,
    TurnCompleted,
)
from glassbox.core.types import ApprovalDecision, SessionStatus
from glassbox.llm import (
    ModelProviderConfig,
    PydanticAIModelAdapter,
    PydanticAIModelExecutor,
)
from glassbox.runtime import EventBus, SessionSupervisor, TurnContextBuilder, TurnEngine
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
    build_patch_tool_registry,
)


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _build_turn_engine(
    repository: SQLiteSessionRepository,
    bus: EventBus[EventEnvelope],
    tmp_path: Path,
    model_fn,
) -> TurnEngine:
    return TurnEngine(
        repository,
        bus,
        TurnContextBuilder(repository),
        lambda _session: PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        ),
        lambda _session: PydanticAIModelExecutor(
            FunctionModel(function=model_fn, model_name="openai:gpt-5.4")
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


# ---------------------------------------------------------------------------
# Shared FunctionModel callbacks
# ---------------------------------------------------------------------------

_PATCH_CONTENT = "Hello, world!\n"
_PATCH_CALL_ID = "provider-call-patch-1"
_PATCH_ARGS = {
    "path": "hello.txt",
    "old_text": "",
    "new_text": _PATCH_CONTENT,
}


def _patch_then_text(messages, _agent_info) -> ModelResponse:
    """Return a patch tool call, then 'Done' after the tool returns."""
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
                    args=_PATCH_ARGS,
                    tool_call_id=_PATCH_CALL_ID,
                )
            ]
        )
    return ModelResponse(parts=[TextPart(content="Patch applied.")])


def _patch_then_text_after_denial(messages, _agent_info) -> ModelResponse:
    """Return a patch call, then acknowledge denial."""
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
                    args=_PATCH_ARGS,
                    tool_call_id=_PATCH_CALL_ID,
                )
            ]
        )
    return ModelResponse(parts=[TextPart(content="Understood, no patch.")])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_approval_approve_resumes_turn_and_executes_tool(tmp_path: Path) -> None:
    """Approving a pending request executes the tool and completes the turn."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository, bus, tmp_path, _patch_then_text
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted

                await supervisor.submit_user_message(
                    state.session_id, "Patch the repo."
                )

                # Wait for turn to suspend on approval
                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

                # Locate the approval_id
                approval_payloads = [
                    ev.payload
                    for ev in repository.read_session_events(state.session_id)
                    if isinstance(ev.payload, ApprovalRequested)
                ]
                assert len(approval_payloads) == 1
                approval_payload = approval_payloads[0]
                assert approval_payload.tool_call_id is not None
                assert approval_payload.provider_tool_call_id is not None

                # Verify session is suspended
                session_state = repository.get_session_state(state.session_id)
                assert session_state is not None
                assert session_state.status == SessionStatus.AWAITING_APPROVAL
                assert session_state.pending_approval_id == approval_payload.approval_id

                # Approve — this should resume the turn and execute the patch
                await supervisor.resolve_approval(
                    state.session_id,
                    approval_payload.approval_id,
                    ApprovalDecision.APPROVED,
                )

                # Wait for the resumed turn to complete
                resume_events: list[EventEnvelope] = []
                while (
                    not resume_events or resume_events[-1].event_type != "TurnCompleted"
                ):
                    resume_events.append(await subscription.get())

            final_state = repository.get_session_state(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
            all_events = repository.read_session_events(state.session_id)
        finally:
            connection.close()

        # The patch file must have been created
        assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == _PATCH_CONTENT

        # Session must be idle after resume
        assert final_state is not None
        assert final_state.status == SessionStatus.RUNNING
        assert final_state.pending_approval_id is None

        # Two TurnCompleted events: one 'awaiting_approval', one 'completed'
        turn_outcomes = [
            ev.payload.outcome
            for ev in all_events
            if isinstance(ev.payload, TurnCompleted)
        ]
        assert turn_outcomes == ["awaiting_approval", "completed"]

        # Final message from assistant
        assert transcript[-1].role == "assistant"
        assert transcript[-1].parts[0].text == "Patch applied."

        # An ApprovalResolved event must exist
        assert any(
            isinstance(ev.payload, ApprovalResolved)
            and ev.payload.decision == ApprovalDecision.APPROVED
            for ev in all_events
        )

    asyncio.run(scenario())


def test_approval_deny_resumes_turn_with_denial_message(tmp_path: Path) -> None:
    """Denying a pending request resumes the turn with a denial tool return."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository, bus, tmp_path, _patch_then_text_after_denial
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted

                await supervisor.submit_user_message(
                    state.session_id, "Patch the repo."
                )

                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

                approval_payloads = [
                    ev.payload
                    for ev in repository.read_session_events(state.session_id)
                    if isinstance(ev.payload, ApprovalRequested)
                ]
                assert len(approval_payloads) == 1
                approval_payload = approval_payloads[0]

                await supervisor.resolve_approval(
                    state.session_id,
                    approval_payload.approval_id,
                    ApprovalDecision.DENIED,
                )

                resume_events: list[EventEnvelope] = []
                while (
                    not resume_events or resume_events[-1].event_type != "TurnCompleted"
                ):
                    resume_events.append(await subscription.get())

            final_state = repository.get_session_state(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
            all_events = repository.read_session_events(state.session_id)
        finally:
            connection.close()

        # File must NOT have been created (tool was denied)
        assert not (tmp_path / "hello.txt").exists()

        assert final_state is not None
        assert final_state.status == SessionStatus.RUNNING
        assert final_state.pending_approval_id is None

        turn_outcomes = [
            ev.payload.outcome
            for ev in all_events
            if isinstance(ev.payload, TurnCompleted)
        ]
        assert turn_outcomes == ["awaiting_approval", "completed"]

        assert transcript[-1].role == "assistant"
        assert transcript[-1].parts[0].text == "Understood, no patch."

        assert any(
            isinstance(ev.payload, ApprovalResolved)
            and ev.payload.decision == ApprovalDecision.DENIED
            for ev in all_events
        )

    asyncio.run(scenario())


def test_approval_workflow_records_replay_artifacts_across_suspend_and_resume(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
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
                        function=_patch_then_text,
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
                artifact_repository=artifact_repository,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            state = await supervisor.start_session(config)
            await supervisor.submit_user_message(state.session_id, "Patch the repo.")
            approval_payload = next(
                ev.payload
                for ev in repository.read_session_events(state.session_id)
                if isinstance(ev.payload, ApprovalRequested)
            )
            await supervisor.resolve_approval(
                state.session_id,
                approval_payload.approval_id,
                ApprovalDecision.APPROVED,
            )

            replay_artifacts = [
                json.loads(
                    artifact_repository.read_text_artifact(Path(event.payload.path))
                )
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ReplayArtifactRecorded)
                and event.payload.path is not None
            ]
        finally:
            connection.close()

        output_outcomes = [
            artifact["outcome"]
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_turn_output"
        ]
        assert output_outcomes == ["awaiting_approval", "completed"]
        assert any(
            artifact["artifact_kind"] == "replay_tool_request"
            and artifact["tool_name"] == "apply_patch"
            for artifact in replay_artifacts
        )
        assert any(
            artifact["artifact_kind"] == "replay_tool_result"
            and artifact["tool_name"] == "apply_patch"
            and artifact["success"] is True
            for artifact in replay_artifacts
        )

    asyncio.run(scenario())


def test_approval_stores_tool_call_metadata_in_approval_requested_event(
    tmp_path: Path,
) -> None:
    """ApprovalRequested events emitted by the turn engine carry tool call IDs."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository, bus, tmp_path, _patch_then_text
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()
                await supervisor.submit_user_message(state.session_id, "Do it.")
                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

            all_events = repository.read_session_events(state.session_id)
        finally:
            connection.close()

        approval_payloads = [
            ev.payload for ev in all_events if isinstance(ev.payload, ApprovalRequested)
        ]
        assert len(approval_payloads) == 1
        assert approval_payloads[0].tool_call_id is not None
        assert approval_payloads[0].provider_tool_call_id == _PATCH_CALL_ID

    asyncio.run(scenario())


def test_approval_requested_without_metadata_does_not_crash_resolution(
    tmp_path: Path,
) -> None:
    """Legacy approvals without tool metadata can be resolved without error."""

    async def scenario() -> None:
        from glassbox.core.ids import new_approval_id, new_turn_id

        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _build_turn_engine(
                repository, bus, tmp_path, _patch_then_text
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            session_state = await supervisor.start_session(config)
            approval_id = new_approval_id()

            # Manually inject a legacy ApprovalRequested without tool metadata.
            repository.append_event(
                EventEnvelope(
                    session_id=session_state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=new_turn_id(),
                        reason="legacy",
                        subject="apply_patch",
                        # Intentionally no tool_call_id or provider_tool_call_id
                    ),
                )
            )

            # Resolving should not raise
            await supervisor.resolve_approval(
                session_state.session_id,
                approval_id,
                ApprovalDecision.APPROVED,
            )
        finally:
            connection.close()

    asyncio.run(scenario())
