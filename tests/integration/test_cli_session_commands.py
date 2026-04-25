"""Integration tests for non-interactive CLI session commands."""

import json
from contextlib import nullcontext
from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.context_builder import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_builder import PytestFailureDigestArtifact
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _completed_turn_ids
from tests.integration.cli_test_support import _list_sessions
from tests.integration.cli_test_support import _make_ask_user_runtime_context
from tests.integration.cli_test_support import _read_session_events
from tests.integration.cli_test_support import _run_baseline_session
from tests.integration.cli_test_support import _seed_pending_approval
from tests.integration.cli_test_support import _seed_pending_question_status
from tests.integration.cli_test_support import _seed_status_projection_details


def test_cli_help_lists_session_oriented_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "chat" not in captured.out
    assert "session" in captured.out
    assert "artifacts" in captured.out
    assert "backup" in captured.out
    assert "projection" in captured.out
    assert "replay" in captured.out
    assert "eval" in captured.out


def test_cli_session_help_lists_session_subcommands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["session", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "answer" in captured.out
    assert "approve" in captured.out
    assert "attach" in captured.out
    assert "deny" in captured.out
    assert "export" in captured.out
    assert "fork" in captured.out
    assert "import" in captured.out
    assert "message" in captured.out
    assert "resume" in captured.out
    assert "run" in captured.out
    assert "chat" in captured.out
    assert "status" in captured.out


def test_cli_replay_help_lists_replay_subcommands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["replay", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "run" in captured.out
    assert "export" in captured.out


def test_cli_session_list_reports_recent_sessions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first_db_path, first_session_id = _run_baseline_session(
        tmp_path,
        prompt="First prompt",
    )
    _ = capsys.readouterr()
    second_exit_code = main(
        [
            "session",
            "run",
            "Second prompt",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(first_db_path),
        ]
    )
    second_session_id = next(
        session.session_id
        for session in _list_sessions(first_db_path)
        if session.session_id != first_session_id
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "list",
            "--status",
            "running",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(first_db_path),
        ]
    )
    captured = capsys.readouterr()

    assert second_exit_code == 0
    assert exit_code == 0
    assert "Sessions: 2" in captured.out
    assert str(second_session_id) in captured.out
    assert str(first_session_id) in captured.out
    assert captured.out.index(str(second_session_id)) < captured.out.index(
        str(first_session_id)
    )
    assert "running" in captured.out
    assert "Next:" in captured.out


def test_cli_session_list_supports_json_and_limit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, first_session_id = _run_baseline_session(tmp_path, prompt="First prompt")
    _ = capsys.readouterr()
    second_exit_code = main(
        [
            "session",
            "run",
            "Second prompt",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    second_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != first_session_id
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "list",
            "--limit",
            "1",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert second_exit_code == 0
    assert exit_code == 0
    assert [session["session_id"] for session in payload] == [str(second_session_id)]
    assert payload[0]["latest_message_summary"] == (
        "assistant: I received your request: Second prompt"
    )


def test_cli_answer_resumes_pending_ask_user_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )

    try:
        exit_code = main(
            [
                "session",
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
                "session",
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
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )

    try:
        exit_code = main(
            [
                "session",
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
                "session",
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
            "session",
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


def test_cli_status_includes_runtime_context_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RuntimeNoteRecorded(
                    category="repo",
                    message="README.md is the primary entrypoint",
                ),
            )
        )
        artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
        artifact_repository.record_text_artifact(
            session_id,
            new_approval_id(),
            new_approval_id(),
            PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
            json.dumps(
                PytestFailureDigestArtifact(
                    target_paths=["tests/unit/test_context_builder.py"],
                    failure_count=1,
                    failing_tests=["tests/unit/test_context_builder.py::test_failure"],
                ).model_dump(mode="json")
            ),
            suffix="json",
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
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
    assert "Runtime context:" in captured.out
    assert "High-signal paths:" in captured.out
    assert "Runtime notes: 1 visible" in captured.out
    assert "[repo] README.md is the primary entrypoint" in captured.out
    assert "Working set:" in captured.out
    assert "[note] [repo] README.md is the primary entrypoint" in captured.out
    assert "Artifact-backed context: 1 visible" in captured.out
    assert (
        "[pytest_failure_digest] 1 failing test(s) for "
        "tests/unit/test_context_builder.py (fresh)" in captured.out
    )


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
            "session",
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
        primary_events = [
            event.event_type
            for event in persisted_events
            if event.event_type != "ReplayArtifactRecorded"
        ]
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
    assert (
        primary_events[-6:]
        == [
            "UserMessageReceived",
            "TurnStarted",
            "TurnStatusChanged",
            "ModelCallStarted",
            "ModelCallCompleted",
            "TurnStatusChanged",
        ]
        or primary_events[-1] == "TurnCompleted"
    )


def test_cli_message_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000001")

    exit_code = main(
        [
            "session",
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
            "session",
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
            "session",
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
            "session",
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
            "session",
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
            "session",
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


def test_cli_fork_creates_child_session_from_latest_completed_turn(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, parent_session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    parent_events_before = _read_session_events(db_path, parent_session_id)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "fork",
            str(parent_session_id),
            "--branch-label",
            "alt-path",
            "--prompt",
            "Try another route",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    sessions = _list_sessions(db_path)
    child_session = next(
        session for session in sessions if session.session_id != parent_session_id
    )
    parent_events_after = _read_session_events(db_path, parent_session_id)

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        child_transcript = repository.list_transcript_messages(child_session.session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Forked session {child_session.session_id}" in captured.out
    assert "Imported 2 transcript messages into child session" in captured.out
    assert "Branch label: alt-path" in captured.out
    assert "Queued user message: Try another route" in captured.out
    assert "Assistant: I received your request: Try another route" in captured.out
    assert child_session.parent_session_id == parent_session_id
    assert child_session.branch_label == "alt-path"
    assert len(parent_events_before) == len(parent_events_after)
    assert [message.parts[0].text for message in child_transcript] == [
        "Inspect the repository",
        "I received your request: Inspect the repository",
        "Try another route",
        "I received your request: Try another route",
    ]


def test_cli_fork_supports_explicit_completed_turn_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, parent_session_id = _run_baseline_session(
        tmp_path,
        prompt="First prompt",
    )
    _ = capsys.readouterr()

    second_exit_code = main(
        [
            "session",
            "message",
            str(parent_session_id),
            "Second prompt",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    assert second_exit_code == 0

    first_turn_id = _completed_turn_ids(db_path, parent_session_id)[0]

    exit_code = main(
        [
            "session",
            "fork",
            str(parent_session_id),
            "--turn",
            str(first_turn_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    sessions = _list_sessions(db_path)
    child_session = next(
        session for session in sessions if session.session_id != parent_session_id
    )

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        child_transcript = repository.list_transcript_messages(child_session.session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Forked session {child_session.session_id}" in captured.out
    assert child_session.parent_session_id == parent_session_id
    assert child_session.forked_from_turn_id == first_turn_id
    assert [message.parts[0].text for message in child_transcript] == [
        "First prompt",
        "I received your request: First prompt",
    ]


def test_cli_fork_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000042")

    exit_code = main(
        [
            "session",
            "fork",
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


def test_cli_fork_rejects_invalid_turn_identifier(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    unknown_turn_id = UUID("00000000-0000-0000-0000-000000000099")
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "fork",
            str(session_id),
            "--turn",
            str(unknown_turn_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"unknown turn_id: {unknown_turn_id}"


def test_cli_fork_rejects_non_branchable_session_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, _approval_id = _seed_pending_approval(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "fork",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"session {session_id} is awaiting approval"


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
            "session",
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
    assert "Dashboard URL:" not in captured.out
    assert "Transcript messages: 2" in captured.out
    assert (
        "Next action: submit a new prompt with 'glassbox session message "
        in captured.out
    )
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
            "session",
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
    assert "Dashboard URL:" not in captured.out
    assert "Session failure: dashboard wiring failed (retryable)" in captured.out
    assert (
        "Next action: inspect the retryable failure details above, or start a "
        "new session with 'glassbox session run PROMPT'" in captured.out
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
            "session",
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
    assert (
        "Session policy summary: 1 decision(s); allow 1, approve 0, deny 0, blocked 0;"
        in captured.out
    )
    assert (
        "Current turn policy summary: 1 decision(s); allow 1, approve 0, "
        "deny 0, blocked 0;" in captured.out
    )
    assert "Pending approvals: 1" in captured.out
    assert (
        f"{approval_id} for turn {turn_id}: run shell command "
        "[approve command via default:command] (needs confirmation)" in captured.out
    )
    assert (
        f"Next action: resolve approval {approval_id} with 'glassbox session approve "
        f"{session_id} {approval_id}' or 'glassbox session deny {session_id} "
        f"{approval_id}', or use the dashboard approvals pane" in captured.out
    )
    assert "Recent tool activity:" in captured.out
    assert (
        f"read_file succeeded (turn {turn_id}) [allow read_only via default:read_only]"
        in captured.out
    )
    assert "done" in captured.out


def test_cli_status_includes_pending_question_and_answer_next_action(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, question_id = _seed_pending_question_status(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
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
        f"Next action: answer question {question_id} with 'glassbox session answer "
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
            "session",
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
            "session",
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
            "session",
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
            "session",
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
