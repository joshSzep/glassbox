"""Integration tests for non-interactive CLI session commands."""

import json
import os
from contextlib import nullcontext
from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import MessagePart
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import ResumeOutcomeRecorded
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_task_checkpoint_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.models import CommandEnvironmentSummary
from glassbox.core.models import CommandToolchainVersion
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import AutonomyMode
from glassbox.core.types import CommandPurpose
from glassbox.core.types import CommandReviewRelevance
from glassbox.core.types import LongRunPhase
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.budgeting import evaluate_budget
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


def _write_running_owner_metadata(workspace_root: Path, db_path: Path) -> None:
    owner_path = workspace_root / ".glassbox" / "runtime-owner.json"
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "workspace_root": str(workspace_root),
                "database_path": str(db_path),
                "host": "127.0.0.1",
                "port": 8765,
                "dashboard_url": "http://127.0.0.1:8765/",
                "started_at": "2025-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _append_runtime_notes(db_path: Path, session_id: UUID, *, count: int) -> None:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        for index in range(count):
            repository.append_event(
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=RuntimeNoteRecorded(
                        category="test",
                        message=f"large compaction source event {index}",
                    ),
                )
            )
    finally:
        connection.close()


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


@pytest.mark.parametrize(
    ("argv", "action"),
    [
        (["session", "run", "hello"], "start a local session runner"),
        (
            ["session", "resume", "00000000-0000-0000-0000-000000000001"],
            "resume a session locally",
        ),
        (
            [
                "session",
                "message",
                "00000000-0000-0000-0000-000000000001",
                "hello",
            ],
            "submit a message locally",
        ),
        (
            [
                "session",
                "answer",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
                "blue",
            ],
            "answer a question locally",
        ),
        (
            [
                "session",
                "approve",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000003",
            ],
            "resolve an approval locally",
        ),
        (
            [
                "session",
                "deny",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000003",
            ],
            "resolve an approval locally",
        ),
        (
            ["session", "fork", "00000000-0000-0000-0000-000000000001"],
            "fork a session locally",
        ),
        (
            ["session", "import", "handoff.json"],
            "import a session handoff package locally",
        ),
    ],
)
def test_cli_local_mutations_are_rejected_while_daemon_owns_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    action: str,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    _write_running_owner_metadata(tmp_path, db_path)

    exit_code = main([*argv, "--cwd", str(tmp_path), "--db-path", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"cannot {action}" in captured.err
    assert "workspace runtime is owned by glassbox daemon" in captured.err


def test_cli_replay_help_lists_replay_subcommands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["replay", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "run" in captured.out
    assert "bundle" in captured.out
    assert "export" not in captured.out


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


def test_cli_resume_rejects_blocked_checkpoint_with_recovery_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    checkpoint_id = new_task_checkpoint_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCheckpointCreated(
                    checkpoint_id=checkpoint_id,
                    objective="Finish checkpoint resume safety",
                    current_phase=LongRunPhase.CHECKPOINTING,
                    completed_step="Prepared checkpoint projection",
                    next_action="Resolve checkpoint blocker",
                    recovery_guidance="Clear the checkpoint blocker or refresh it",
                    blockers=["operator approval required"],
                    source_start_sequence=1,
                    source_end_sequence=3,
                ),
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

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        persisted_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 1
    assert f"cannot resume session {session_id} from checkpoint" in captured.err
    assert "unresolved blockers" in captured.err
    assert "Clear the checkpoint blocker or refresh it" in captured.err
    assert [event.event_type for event in persisted_events[-2:]] == [
        "RecoveryDecisionRecorded",
        "ResumeOutcomeRecorded",
    ]
    recovery_payload = persisted_events[-2].payload
    outcome_payload = persisted_events[-1].payload
    assert isinstance(recovery_payload, RecoveryDecisionRecorded)
    assert isinstance(outcome_payload, ResumeOutcomeRecorded)
    assert recovery_payload.checkpoint_id == checkpoint_id
    assert outcome_payload.checkpoint_id == checkpoint_id


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
    assert "Checkpoint absence: not_expected_yet" in captured.out


def test_cli_status_explains_checkpoint_absence_reasons(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active_root = tmp_path / "active"
    historical_root = tmp_path / "historical"
    imported_root = tmp_path / "imported"
    active_root.mkdir()
    historical_root.mkdir()
    imported_root.mkdir()
    active_db_path, active_session_id = _run_baseline_session(active_root)
    historical_db_path, historical_session_id = _run_baseline_session(historical_root)
    imported_db_path, imported_session_id = _run_baseline_session(imported_root)

    connection = open_database(active_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        budget = default_budget_for_autonomy_mode(AutonomyMode.TEST_DRIVEN)
        usage = AutonomyBudgetUsage(
            seconds_since_checkpoint=budget.checkpoint_interval_seconds or 0,
        )
        repository.append_event(
            EventEnvelope(
                session_id=active_session_id,
                sequence=0,
                payload=BudgetDecisionRecorded(
                    scope="session",
                    mode=AutonomyMode.TEST_DRIVEN,
                    budget=budget,
                    usage=usage,
                    remaining=evaluate_budget(budget, usage).remaining,
                    decision="allowed",
                ),
            )
        )
    finally:
        connection.close()

    connection = open_database(historical_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=historical_session_id,
                sequence=0,
                payload=SessionCompleted(reason="finished before checkpoints"),
            )
        )
    finally:
        connection.close()

    connection = open_database(imported_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        imported_session = repository.get_session(imported_session_id)
        assert imported_session is not None
        repository.append_event(
            EventEnvelope(
                session_id=imported_session_id,
                sequence=0,
                payload=TranscriptMessageImported(
                    message_id=new_message_id(),
                    source_session_id=active_session_id,
                    source_message_id=new_message_id(),
                    source_turn_id=None,
                    role="user",
                    parts=[MessagePart(kind="text", text="imported prompt")],
                    source_created_at=imported_session.created_at,
                ),
            )
        )
        repository.append_event(
            EventEnvelope(
                session_id=imported_session_id,
                sequence=0,
                payload=SessionCompleted(reason="imported for inspection"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    outputs: list[str] = []
    for root, db_path, session_id in (
        (active_root, active_db_path, active_session_id),
        (historical_root, historical_db_path, historical_session_id),
        (imported_root, imported_db_path, imported_session_id),
    ):
        exit_code = main(
            [
                "session",
                "status",
                str(session_id),
                "--cwd",
                str(root),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        outputs.append(captured.out)

    assert "Checkpoint absence: active_checkpoint_expected" in outputs[0]
    assert "reached its checkpoint interval" in outputs[0]
    assert "Checkpoint absence: historical_pre_checkpoint" in outputs[1]
    assert "No checkpoint action is required for historical inspection." in outputs[1]
    assert "Checkpoint absence: imported_inspection_only" in outputs[2]
    assert "imported for inspection" in outputs[2]


def test_cli_status_includes_latest_checkpoint(
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
                payload=TaskCheckpointCreated(
                    checkpoint_id=new_task_checkpoint_id(),
                    objective="Finish checkpoint handoff",
                    current_phase=LongRunPhase.CHECKPOINTING,
                    completed_step="Added checkpoint read model",
                    next_action="Expose checkpoint in session status",
                    recovery_guidance="Resume from the latest checkpoint",
                    blockers=["awaiting operator review"],
                    source_start_sequence=1,
                    source_end_sequence=3,
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
    assert (
        "Latest checkpoint: Finish checkpoint handoff; phase checkpointing; "
        "last step: Added checkpoint read model; "
        "next: Expose checkpoint in session status; source events 1-3; "
        "blockers: awaiting operator review"
    ) in captured.out


def test_cli_compact_creates_and_lists_context_compaction(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "compact",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    created = capsys.readouterr()

    list_exit_code = main(
        [
            "session",
            "compactions",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    listed = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        compactions = repository.list_context_compactions(session_id)
        persisted_events = repository.read_session_events(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert list_exit_code == 0
    assert "Created context compaction" in created.out
    assert "Context compactions: 1" in listed.out
    assert len(compactions) == 1
    assert compactions[0].summary.startswith("Compacted")
    artifact_path = (
        tmp_path
        / ".glassbox"
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{compactions[0].artifact_id}.context-compaction.json"
    )
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact_payload["artifact_kind"] == "context_compaction_v1"
    assert artifact_payload["source_references"]
    assert persisted_events[-1].event_type == "ContextCompactionCreated"


def test_cli_compact_rejects_over_cap_range_with_bounded_json_guidance(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _append_runtime_notes(db_path, session_id, count=205)
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "compact",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    json_output = capsys.readouterr()
    payload = json.loads(json_output.out)

    assert exit_code == 1
    assert payload["error"] == "source_range_exceeds_cap"
    assert payload["selected_event_count"] > 200
    assert payload["source_reference_cap"] == 200
    assert payload["suggested_ranges"][0]["selected_event_count"] == 200
    assert payload["suggested_ranges"][-1]["label"] == "latest"

    text_exit_code = main(
        [
            "session",
            "compact",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    text_output = capsys.readouterr()

    assert text_exit_code == 1
    assert "Selected source range contains" in text_output.err
    assert "Retry with a bounded range" in text_output.err


def test_cli_compaction_refresh_and_invalidate_are_confirmation_gated(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _ = capsys.readouterr()

    assert (
        main(
            [
                "session",
                "compact",
                str(session_id),
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        == 0
    )
    _ = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        original = repository.list_context_compactions(session_id)[0]
    finally:
        connection.close()

    refresh_without_confirmation = main(
        [
            "session",
            "compaction-refresh",
            str(session_id),
            str(original.compaction_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_warning = capsys.readouterr()

    assert refresh_without_confirmation == 2
    assert "Re-run with --yes" in refresh_warning.out

    refresh_exit_code = main(
        [
            "session",
            "compaction-refresh",
            str(session_id),
            str(original.compaction_id),
            "--yes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_output = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        compactions_after_refresh = repository.list_context_compactions(session_id)
        refreshed = [
            row
            for row in compactions_after_refresh
            if row.compaction_id != original.compaction_id
        ][0]
        previous = repository.get_context_compaction(session_id, original.compaction_id)
    finally:
        connection.close()

    assert refresh_exit_code == 0
    assert "replacement" in refresh_output.out
    assert previous is not None
    assert previous.freshness.value == "stale"
    assert previous.superseded_by_compaction_id == refreshed.compaction_id

    invalidate_exit_code = main(
        [
            "session",
            "compaction-invalidate",
            str(session_id),
            str(refreshed.compaction_id),
            "--reason",
            "summary omitted an operator blocker",
            "--yes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    invalidate_output = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        invalidated = repository.get_context_compaction(
            session_id,
            refreshed.compaction_id,
        )
    finally:
        connection.close()

    assert invalidate_exit_code == 0
    assert "Invalidated context compaction" in invalidate_output.out
    assert invalidated is not None
    assert invalidated.freshness.value == "invalidated"
    assert invalidated.freshness_reason == "summary omitted an operator blocker"


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
    tool_attempt_id = new_tool_attempt_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=ToolAttemptStatus.RUNNING,
                    turn_id=turn_id,
                    tool_name="run_command",
                    message="pytest is still running",
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
    assert "Recent tool attempts:" in captured.out
    assert f"run_command attempt {str(tool_attempt_id)[:8]} running" in captured.out
    assert "pytest is still running" in captured.out


def test_cli_tool_attempts_lists_durable_attempts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, turn_id, _approval_id = _seed_status_projection_details(
        tmp_path
    )
    tool_attempt_id = new_tool_attempt_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=ToolAttemptStatus.STALE,
                    turn_id=turn_id,
                    tool_name="run_command",
                    message="heartbeat expired before completion",
                    safe_to_retry=None,
                    retry_classification=ToolAttemptRetryClassification.UNKNOWN,
                    retry_requires_approval=True,
                    retry_reason=(
                        "attempt heartbeat is stale; retry side effects are unknown "
                        "from retained evidence"
                    ),
                    retry_policy_reason="command retry requires confirmation",
                    command_purpose=CommandPurpose.TEST,
                    command_review_relevance=CommandReviewRelevance.VERIFICATION,
                    command_supports_verification=True,
                    command_purpose_reason=(
                        "test command can support verification evidence"
                    ),
                    command_environment=CommandEnvironmentSummary(
                        capture_scope="verification_or_local_artifact",
                        command_purpose=CommandPurpose.TEST,
                        platform="Darwin",
                        python_version="3.13.0",
                        toolchains=[
                            CommandToolchainVersion(
                                name="python",
                                version="3.13.0",
                                available=True,
                                source="fixture",
                                redacted_executable="<redacted-path>/python",
                            )
                        ],
                        environment={"CI": "true"},
                        redaction_notes=["raw environment is not stored"],
                    ),
                ),
            )
        )
    finally:
        connection.close()
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "tool-attempts",
            str(session_id),
            "--status",
            "stale",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Tool attempts: 1" in captured.out
    assert str(tool_attempt_id) in captured.out
    assert "run_command  stale" in captured.out
    assert "heartbeat expired before completion" in captured.out
    assert "Retry classification: unknown" in captured.out
    assert "Retry requires approval: true" in captured.out
    assert "retry side effects are unknown" in captured.out
    assert "Retry policy reason: command retry requires confirmation" in captured.out
    assert "Command purpose: test" in captured.out
    assert "Review relevance: verification" in captured.out
    assert "Supports verification: true" in captured.out
    assert "test command can support verification evidence" in captured.out
    assert "Command environment: captured" in captured.out


def test_cli_tool_attempt_inspect_and_abandon_record_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, turn_id, _approval_id = _seed_status_projection_details(
        tmp_path
    )
    tool_attempt_id = new_tool_attempt_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=ToolAttemptStatus.STALE,
                    turn_id=turn_id,
                    tool_name="read_file",
                    message="heartbeat expired before completion",
                    safe_to_retry=True,
                    retry_classification=ToolAttemptRetryClassification.RETRYABLE,
                    retry_requires_approval=False,
                    retry_reason="read-only tools do not mutate workspace state",
                ),
            )
        )
    finally:
        connection.close()
    _ = capsys.readouterr()

    inspect_code = main(
        [
            "session",
            "tool-attempt",
            "inspect",
            str(session_id),
            str(tool_attempt_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    inspect_output = capsys.readouterr().out

    abandon_code = main(
        [
            "session",
            "tool-attempt",
            "abandon",
            str(session_id),
            str(tool_attempt_id),
            "--reason",
            "operator chose a fresh path",
            "--yes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    abandon_output = capsys.readouterr().out

    assert inspect_code == 0
    assert "Recovery actions: inspect, retry, abandon" in inspect_output
    assert abandon_code == 0
    assert f"abandoned {tool_attempt_id}" in abandon_output
    assert "Status: abandoned" in abandon_output

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        attempt = repository.get_tool_attempt(session_id, tool_attempt_id)
        assert attempt is not None
        assert attempt.status == ToolAttemptStatus.ABANDONED
        recovery_events = [
            event
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, RecoveryDecisionRecorded)
            and event.payload.tool_attempt_id == tool_attempt_id
        ]
        assert len(recovery_events) == 1
    finally:
        connection.close()


def test_cli_tool_attempt_retry_replays_read_only_tool_call(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")
    db_path, session_id, turn_id, _approval_id = _seed_status_projection_details(
        tmp_path
    )
    tool_attempt_id = new_tool_attempt_id()
    tool_call_id = new_tool_call_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ModelToolCallRequested(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        arguments_json=json.dumps({"path": "note.txt"}),
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
                    payload=ToolAttemptHeartbeat(
                        tool_attempt_id=tool_attempt_id,
                        status=ToolAttemptStatus.FAILED,
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        message="transient read failure",
                        safe_to_retry=True,
                        retry_classification=ToolAttemptRetryClassification.RETRYABLE,
                        retry_requires_approval=False,
                        retry_reason="read-only tools do not mutate workspace state",
                    ),
                ),
            ]
        )
    finally:
        connection.close()
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "tool-attempt",
            "retry",
            str(session_id),
            str(tool_attempt_id),
            "--yes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"retried {tool_attempt_id}" in captured.out
    assert "Retry status: succeeded" in captured.out

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        original = repository.get_tool_attempt(session_id, tool_attempt_id)
        assert original is not None
        assert original.status == ToolAttemptStatus.RETRIED
        retry_attempts = [
            attempt
            for attempt in repository.list_tool_attempts(session_id)
            if attempt.tool_attempt_id != tool_attempt_id
        ]
        assert len(retry_attempts) == 1
        assert retry_attempts[0].status == ToolAttemptStatus.SUCCEEDED
    finally:
        connection.close()


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
