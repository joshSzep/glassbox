"""Integration tests for session-oriented CLI commands."""

import sqlite3
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    EventEnvelope,
    ModelCallCompleted,
    SessionCompleted,
    SessionFailed,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    TurnStarted,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    new_approval_id,
    new_message_id,
    new_question_id,
    new_tool_call_id,
    new_turn_id,
)
from glassbox.core.types import ApprovalDecision
from glassbox.llm import (
    ModelProviderConfig,
    PydanticAIModelAdapter,
    PydanticAIModelExecutor,
)
from glassbox.runtime import (
    EventBus,
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
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
)


def test_cli_help_lists_session_oriented_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "answer" in captured.out
    assert "message" in captured.out
    assert "resume" in captured.out
    assert "status" in captured.out
    assert "rebuild" in captured.out
    assert "approve" in captured.out
    assert "deny" in captured.out


def test_cli_answer_resumes_pending_ask_user_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )

    try:
        exit_code = main(
            [
                "run",
                "Pick a colour.",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        first_capture = capsys.readouterr()

        repository = runtime_context.repositories.sessions
        session_id = repository.list_sessions()[0].session_id
        question = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, UserQuestionAsked)
        )

        assert exit_code == 0
        assert (
            f"Question asked ({question.question_id}): What colour should I use?"
            in first_capture.out
        )

        exit_code = main(
            [
                "answer",
                str(session_id),
                str(question.question_id),
                "blue",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Answer submitted for question {question.question_id}: blue" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_answer_rejects_unknown_question_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )

    try:
        exit_code = main(
            [
                "run",
                "Pick a colour.",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        _ = capsys.readouterr()

        session_id = runtime_context.repositories.sessions.list_sessions()[0].session_id

        assert exit_code == 0

        unknown_question_id = UUID("00000000-0000-0000-0000-000000000042")
        exit_code = main(
            [
                "answer",
                str(session_id),
                str(unknown_question_id),
                "blue",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()
    finally:
        connection.close()

    assert exit_code == 1
    assert captured.err.strip() == f"unknown question_id: {unknown_question_id}"


def test_cli_answer_rejects_session_not_awaiting_user_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "answer",
            str(session_id),
            str(UUID("00000000-0000-0000-0000-000000000042")),
            "blue",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"session {session_id} is not awaiting user input"


def test_cli_message_submits_new_user_turn_to_existing_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "message",
            str(session_id),
            "Now summarize the tests.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        transcript = repository.list_transcript_messages(session_id)
        persisted_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Queued user message: Now summarize the tests." in captured.out
    assert (
        "Assistant: I received your request: Now summarize the tests." in captured.out
    )
    assert transcript[-2].role == "user"
    assert transcript[-2].parts[0].text == "Now summarize the tests."
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == (
        "I received your request: Now summarize the tests."
    )
    assert [event.event_type for event in persisted_events[-6:]] == [
        "UserMessageReceived",
        "TurnStarted",
        "TurnStatusChanged",
        "ModelCallStarted",
        "ModelCallCompleted",
        "TurnStatusChanged",
    ] or persisted_events[-1].event_type == "TurnCompleted"


def test_cli_message_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000001")

    exit_code = main(
        [
            "message",
            str(unknown_session_id),
            "Hello",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"unknown session_id: {unknown_session_id}"


def test_cli_message_rejects_non_interactive_session_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason="done"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "message",
            str(session_id),
            "Hello again",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == (
        "session cannot accept input in its current state: completed"
    )


def test_cli_resume_replays_resume_event(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "resume",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    persisted_events = _read_session_events(db_path, session_id)

    assert exit_code == 0
    assert "Resumed session" in captured.out
    assert persisted_events[-1].event_type == "SessionResumed"


def test_cli_resume_preserves_awaiting_approval_session_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "resume",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        state = repository.get_session_state(session_id)
        persisted_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert approval_id is not None
    assert "Resumed session" in captured.out
    assert state is not None
    assert state.status == "awaiting_approval"
    assert state.pending_approval_id == approval_id
    assert persisted_events[-1].event_type == "SessionResumed"


def test_cli_resume_preserves_mid_transcript_running_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "resume",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        state = repository.get_session_state(session_id)
        transcript_messages = repository.list_transcript_messages(session_id)
        persisted_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Resumed session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert len(transcript_messages) == 2
    assert persisted_events[-1].event_type == "SessionResumed"


def test_cli_resume_rejects_completed_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason="done"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "resume",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == (
        f"cannot resume session {session_id} in status completed"
    )


def test_cli_status_prints_human_session_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "status",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Session {session_id}" in captured.out
    assert "Status: running" in captured.out
    assert "Current turn: none" in captured.out
    assert "Pending approvals: none" in captured.out
    assert "Recent tool activity: none" in captured.out
    assert "Dashboard URL: http://127.0.0.1:8765" in captured.out
    assert "Transcript messages: 2" in captured.out
    assert "Next action: submit a new prompt with 'glassbox message " in captured.out
    assert (
        "Latest message: assistant: I received your request: Inspect the repository"
        in captured.out
    )


def test_cli_status_includes_session_failure_details(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionFailed(
                    error_message="dashboard wiring failed",
                    retryable=True,
                ),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "status",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Status: failed" in captured.out
    assert "Dashboard URL: http://127.0.0.1:8765" in captured.out
    assert "Session failure: dashboard wiring failed (retryable)" in captured.out
    assert (
        "Next action: inspect the retryable failure details above, or start a "
        "new session with 'glassbox run PROMPT'" in captured.out
    )


def test_cli_status_includes_turn_approvals_tool_activity_and_metrics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, turn_id, approval_id = _seed_status_projection_details(
        tmp_path
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "status",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Current turn: {turn_id} (awaiting_approval)" in captured.out
    assert "Current turn metrics: turn" in captured.out
    assert "model 1 call(s), 42 input / 13 output tokens, 600 ms" in captured.out
    assert "tools 1 call(s)," in captured.out
    assert "Pending approvals: 1" in captured.out
    assert (
        f"{approval_id} for turn {turn_id}: run shell command (needs confirmation)"
        in captured.out
    )
    assert (
        f"Next action: resolve approval {approval_id} with 'glassbox approve "
        f"{session_id} {approval_id}' or 'glassbox deny {session_id} "
        f"{approval_id}', or use the dashboard approvals pane" in captured.out
    )
    assert "Recent tool activity:" in captured.out
    assert "read_file succeeded" in captured.out
    assert "done" in captured.out


def test_cli_status_includes_pending_question_and_answer_next_action(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, question_id = _seed_pending_question_status(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "status",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Status: awaiting_user_input" in captured.out
    assert f"Pending question: {question_id}: What colour should I use?" in captured.out
    assert (
        f"Next action: answer question {question_id} with 'glassbox answer "
        f"{session_id} {question_id} ANSWER', or use the dashboard Next Action pane"
        in captured.out
    )


def test_cli_approve_resolves_pending_approval(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "approve",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    persisted_events = _read_session_events(db_path, session_id)

    assert exit_code == 0
    assert "Approval resolved: approved by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"
    assert isinstance(persisted_events[-1].payload, ApprovalResolved)
    assert persisted_events[-1].payload.decision == ApprovalDecision.APPROVED


def test_cli_deny_resolves_pending_approval(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "deny",
            str(session_id),
            str(approval_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    persisted_events = _read_session_events(db_path, session_id)

    assert exit_code == 0
    assert "Approval resolved: denied by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"
    assert isinstance(persisted_events[-1].payload, ApprovalResolved)
    assert persisted_events[-1].payload.decision == ApprovalDecision.DENIED


def test_cli_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000001")

    exit_code = main(
        [
            "resume",
            str(unknown_session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"unknown session_id: {unknown_session_id}"


def test_cli_rejects_invalid_approval_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "approve",
            str(session_id),
            str(new_approval_id()),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == (
        f"session {session_id} is not awaiting approval resolution"
    )


def _run_baseline_session(
    tmp_path: Path,
    *,
    prompt: str | None = None,
) -> tuple[Path, UUID]:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    argv = ["run"]
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
