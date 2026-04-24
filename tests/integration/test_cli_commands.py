"""Integration tests for session-oriented CLI commands."""

import asyncio
import json
import shutil
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
    ReplayArtifactRecorded,
    RuntimeNoteRecorded,
    SessionCompleted,
    SessionFailed,
    SessionStarted,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    TurnCompleted,
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
    PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
    EventBus,
    PytestFailureDigestArtifact,
    ReplayRunner,
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
    build_patch_tool_registry,
)
from glassbox.web import WebServerConfig


class FakeChatDashboardServer:
    def __init__(self, *, host: str, port: int) -> None:
        self.config = WebServerConfig(host=host, port=port)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class FailingChatDashboardServer(FakeChatDashboardServer):
    async def start(self) -> None:
        raise RuntimeError("web server failed to start")


def test_cli_help_lists_session_oriented_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "answer" in captured.out
    assert "attach" in captured.out
    assert "chat" in captured.out
    assert "message" in captured.out
    assert "resume" in captured.out
    assert "fork" in captured.out
    assert "status" in captured.out
    assert "rebuild" in captured.out
    assert "replay" in captured.out
    assert "replay-export" in captured.out
    assert "eval" in captured.out
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


def test_cli_replay_reports_exact_match_without_mutating_source_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        before_events = repository.read_session_events(session_id)
        before_paths = [
            event.payload.path
            for event in before_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        before_state = repository.get_session_state(session_id)
        assert before_state is not None
        before_last_sequence = before_state.last_sequence
    finally:
        connection.close()

    exit_code = main(
        [
            "replay",
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
        after_events = repository.read_session_events(session_id)
        after_paths = [
            event.payload.path
            for event in after_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        after_state = repository.get_session_state(session_id)
        assert after_state is not None
        after_last_sequence = after_state.last_sequence
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Replay session {session_id}" in captured.out
    assert "Outcome: exact match" in captured.out
    assert before_last_sequence == after_last_sequence
    assert len(before_events) == len(after_events)
    assert before_paths == after_paths


def test_cli_replay_reports_behavioral_drift_and_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
                payload=SessionCompleted(reason="forced complete for replay drift"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 10


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
            new_turn_id(),
            new_tool_call_id(),
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


def test_cli_replay_reports_manifest_drift_and_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    artifact_path = _first_replay_artifact_path(db_path, session_id)
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_payload["prepared_turn"]["user_prompt"] = "Unexpected prompt"
    artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 11
    assert "Outcome: manifest drift" in captured.out
    assert "Summary:" in captured.out


def test_cli_replay_json_output_contains_structured_report(
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
            "replay",
            str(session_id),
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "exact_match"
    assert payload["source_session_id"] == str(session_id)
    assert payload["exit_code"] == 0
    assert payload["baseline"] == payload["replay"]


def test_cli_replay_export_writes_bundle_and_bundle_replay_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    bundle_path = tmp_path / "exports" / "baseline.json"
    portable_root = tmp_path / "portable-workspace"
    portable_root.mkdir()
    _ = capsys.readouterr()

    export_exit_code = main(
        [
            "replay-export",
            str(session_id),
            str(bundle_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    export_capture = capsys.readouterr()

    replay_exit_code = main(
        [
            "replay",
            "--bundle",
            str(bundle_path),
            "--cwd",
            str(portable_root),
        ]
    )
    replay_capture = capsys.readouterr()

    assert export_exit_code == 0
    assert bundle_path.exists()
    assert (
        f"Exported replay bundle for session {session_id}: {bundle_path.resolve()}"
        in export_capture.out
    )
    assert replay_exit_code == 0
    assert f"Replay session {session_id}" in replay_capture.out
    assert "Outcome: exact match" in replay_capture.out


def test_cli_replay_requires_exactly_one_session_or_bundle_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    bundle_path = tmp_path / "baseline.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--bundle",
            str(bundle_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == "specify exactly one of session_id or --bundle"


def test_cli_eval_run_reports_mixed_outcomes_and_writes_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    manifest_bundle_path = tmp_path / "evals" / "bundles" / "drift.manifest.json"
    manifest_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    manifest_payload["model_calls"][0]["manifest"]["prepared_turn"]["user_prompt"] = (
        "Unexpected prompt"
    )
    manifest_bundle_path.write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="drift.manifest",
        title="Manifest drift",
        bundle_name=manifest_bundle_path.name,
        tags=["smoke", "provider-mode"],
    )
    output_dir = tmp_path / "eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 11
    assert "Selected cases: 2" in captured.out
    assert "Passed: 1" in captured.out
    assert "Failed: 1" in captured.out
    assert "drift.manifest: manifest drift (failed)" in captured.out
    assert str(output_dir.resolve()) in captured.out
    assert summary["selected_case_count"] == 2
    assert summary["passed_case_count"] == 1
    assert summary["failed_case_count"] == 1
    assert summary["exit_code"] == 11
    assert summary["outcome_counts"]["exact_match"] == 1
    assert summary["outcome_counts"]["manifest_drift"] == 1
    for case_payload in summary["cases"]:
        assert Path(case_payload["artifact_path"]).is_file()


def test_cli_eval_run_supports_tag_filter_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    approval_bundle_path = tmp_path / "evals" / "bundles" / "approval.patch.json"
    shutil.copyfile(bundle_path, approval_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="approval.patch",
        title="Patch approval",
        bundle_name=approval_bundle_path.name,
        tags=["approval", "tooling"],
    )
    output_dir = tmp_path / "tagged-eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "approval",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["selected_case_count"] == 1
    assert payload["passed_case_count"] == 1
    assert payload["failed_case_count"] == 0
    assert payload["cases"][0]["case_id"] == "approval.patch"
    assert payload["cases"][0]["passed"] is True
    assert Path(payload["summary_path"]).is_file()


def test_cli_eval_run_supports_profile_selection_and_tag_narrowing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    context_bundle_path = tmp_path / "evals" / "bundles" / "context.branch.json"
    shutil.copyfile(smoke_bundle_path, context_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke", "tooling"],
        release_contract={
            "owner": "runtime.replay",
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="context.branch",
        title="Context branch smoke",
        bundle_name=context_bundle_path.name,
        tags=["smoke", "context"],
        release_contract={
            "owner": "runtime.context",
            "verification_stages": ["commit-time", "push-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "branching",
                "title": "Branching",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["context.branch"],
            }
        ],
    )
    output_dir = tmp_path / "profiled-eval-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "commit-smoke",
            "--tag",
            "context",
            "--json",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["profile_id"] == "commit-smoke"
    assert payload["profile_verification_stage"] == "commit-time"
    assert payload["coverage_audit"]["covered_capability_count"] == 1
    assert payload["selected_case_count"] == 1
    assert payload["cases"][0]["case_id"] == "context.branch"


def test_cli_eval_audit_reports_uncovered_critical_capabilities(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    extra_bundle_path = tmp_path / "evals" / "bundles" / "smoke.extra.json"
    branch_bundle_path = tmp_path / "evals" / "bundles" / "branch.case.json"
    shutil.copyfile(smoke_bundle_path, extra_bundle_path)
    shutil.copyfile(smoke_bundle_path, branch_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=smoke_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["smoke_validation"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.extra",
        title="Extra smoke",
        bundle_name=extra_bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["smoke_validation"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_case(
        tmp_path,
        case_id="branch.case",
        title="Branch case",
        bundle_name=branch_bundle_path.name,
        tags=["context"],
        release_contract={
            "owner": "runtime.context",
            "capabilities": ["branching"],
            "verification_stages": ["commit-time"],
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "commit-smoke",
                "title": "Commit smoke",
                "verification_stage": "commit-time",
                "tags": ["smoke"],
                "blocking": True,
            }
        ],
    )
    _write_eval_coverage(
        tmp_path,
        profiles=[
            {
                "capability_id": "smoke_validation",
                "title": "Smoke validation",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["smoke.readme"],
            },
            {
                "capability_id": "branching",
                "title": "Branching",
                "criticality": "release-critical",
                "verification_stages": ["commit-time"],
                "expected_case_ids": ["branch.case"],
            },
        ],
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "audit",
            "--profile",
            "commit-smoke",
            "--json",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["uncovered_release_critical_capability_ids"] == ["branching"]
    assert payload["unmapped_case_ids"] == ["smoke.extra"]
    assert payload["redundant_case_ids"] == ["smoke.extra"]


def test_cli_eval_promote_creates_case_bundle_and_review_artifact(
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
            "eval",
            "promote",
            str(session_id),
            "smoke.promoted",
            "--title",
            "Promoted smoke case",
            "--tag",
            "smoke",
            "--owner",
            "runtime.replay",
            "--capability",
            "replay_portability",
            "--severity",
            "high",
            "--verification-stage",
            "commit-time",
            "--verification-stage",
            "push-time",
            "--reason",
            "Initial promotion for smoke verification.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    case_path = tmp_path / "evals" / "cases" / "smoke.promoted.json"
    bundle_path = tmp_path / "evals" / "bundles" / "smoke.promoted.json"
    report_path = (
        tmp_path / ".glassbox" / "evals" / "baseline-updates" / "smoke.promoted.json"
    )
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Operation: promote" in captured.out
    assert case_path.is_file()
    assert bundle_path.is_file()
    assert report_path.is_file()
    assert case_payload["release_contract"]["owner"] == "runtime.replay"
    assert case_payload["baseline_history"][0]["operation"] == "promote"
    assert case_payload["baseline_history"][0]["rationale"] == (
        "Initial promotion for smoke verification."
    )
    assert report_payload["operation"] == "promote"
    assert report_payload["acknowledgement_required"] is False

    run_exit_code = main(
        [
            "eval",
            "run",
            "smoke.promoted",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "promoted-output"),
        ]
    )
    run_capture = capsys.readouterr()

    assert run_exit_code == 0
    assert "smoke.promoted: exact match (passed)" in run_capture.out


def test_cli_eval_refresh_requires_acknowledgement_for_blocking_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, initial_session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    second_exit_code = main(
        [
            "run",
            "Inspect the repository again",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "owner": "runtime.replay",
            "capabilities": ["replay_portability"],
            "verification_stages": ["commit-time"],
        },
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "refresh",
            "smoke.readme",
            str(refresh_session_id),
            "--reason",
            "Intentional refresh after session capture update.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert second_exit_code == 0
    assert exit_code == 1
    assert "requires --acknowledge-policy" in captured.err


def test_cli_eval_refresh_rejects_blocking_case_without_release_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, initial_session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    second_exit_code = main(
        [
            "run",
            "Inspect the repository again",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
        release_contract={
            "verification_stages": ["commit-time"],
        },
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "refresh",
            "smoke.readme",
            str(refresh_session_id),
            "--reason",
            "Intentional refresh after session capture update.",
            "--acknowledge-policy",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert second_exit_code == 0
    assert exit_code == 1
    assert "requires owner and capabilities metadata" in captured.err


def test_cli_eval_refresh_updates_bundle_manifest_history_and_review_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, initial_session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    promote_exit_code = main(
        [
            "eval",
            "promote",
            str(initial_session_id),
            "smoke.promoted",
            "--title",
            "Promoted smoke case",
            "--tag",
            "smoke",
            "--owner",
            "runtime.replay",
            "--capability",
            "replay_portability",
            "--severity",
            "high",
            "--verification-stage",
            "commit-time",
            "--reason",
            "Initial promotion for smoke verification.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    second_exit_code = main(
        [
            "run",
            "Summarize the tests.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    refresh_session_id = next(
        session.session_id
        for session in _list_sessions(db_path)
        if session.session_id != initial_session_id
    )

    refresh_exit_code = main(
        [
            "eval",
            "refresh",
            "smoke.promoted",
            str(refresh_session_id),
            "--reason",
            "Prompt changed intentionally for a refreshed smoke baseline.",
            "--acknowledge-policy",
            "--notes",
            "Refreshed after updating the source prompt.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    case_path = tmp_path / "evals" / "cases" / "smoke.promoted.json"
    report_path = (
        tmp_path / ".glassbox" / "evals" / "baseline-updates" / "smoke.promoted.json"
    )
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert promote_exit_code == 0
    assert second_exit_code == 0
    assert refresh_exit_code == 0
    assert "Operation: refresh" in captured.out
    assert len(case_payload["baseline_history"]) == 2
    assert case_payload["baseline_history"][-1]["operation"] == "refresh"
    assert case_payload["baseline_history"][-1]["rationale"] == (
        "Prompt changed intentionally for a refreshed smoke baseline."
    )
    assert case_payload["notes"] == "Refreshed after updating the source prompt."
    assert report_payload["operation"] == "refresh"
    assert report_payload["acknowledgement_required"] is True
    assert report_payload["acknowledgement_received"] is True
    assert report_payload["baseline_history_count_after"] == 2
    assert report_payload["manifest_field_changes"]["baseline_history"]["after"]

    run_exit_code = main(
        [
            "eval",
            "run",
            "smoke.promoted",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "refreshed-output"),
        ]
    )
    run_capture = capsys.readouterr()

    assert run_exit_code == 0
    assert "smoke.promoted: exact match (passed)" in run_capture.out


def test_cli_eval_run_rejects_blocking_profile_with_advisory_case(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "context.relaxed")
    _write_eval_case(
        tmp_path,
        case_id="context.relaxed",
        title="Relaxed context advisory",
        bundle_name=bundle_path.name,
        tags=["context"],
        release_contract={
            "owner": "runtime.context",
            "verification_stages": ["advisory"],
            "baseline_refresh_policy": "advisory",
        },
    )
    _write_eval_profiles(
        tmp_path,
        profiles=[
            {
                "profile_id": "bad-blocking-context",
                "title": "Bad blocking context profile",
                "verification_stage": "advisory",
                "tags": ["context"],
                "blocking": True,
            }
        ],
    )

    exit_code = main(
        [
            "eval",
            "run",
            "--profile",
            "bad-blocking-context",
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "blocking eval profile bad-blocking-context" in captured.err


def test_cli_eval_run_allows_selected_invariants_to_ignore_behavioral_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "transcript.only")
    final_state_bundle_path = tmp_path / "evals" / "bundles" / "final-state.json"
    final_state_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    final_state_payload["baseline"]["final_state"]["status"] = "completed"
    final_state_bundle_path.write_text(
        json.dumps(final_state_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    _write_eval_case(
        tmp_path,
        case_id="transcript.only",
        title="Transcript-only expectation",
        bundle_name=final_state_bundle_path.name,
        tags=["smoke"],
        expectation={
            "mode": "selected_invariants",
            "invariants": ["transcript"],
        },
    )
    output_dir = tmp_path / "selected-invariants-output"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "eval",
            "run",
            "transcript.only",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "transcript.only: behavioral drift (passed)" in captured.out
    assert "Ignored mismatches: final_state drift" in captured.out
    assert summary["cases"][0]["replay_outcome"] == "behavioral_drift"
    assert summary["cases"][0]["passed"] is True
    assert summary["cases"][0]["ignored_mismatches"] == ["final_state drift"]


def test_cli_eval_run_refreshes_managed_output_dir_for_repeated_runs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    approval_bundle_path = tmp_path / "evals" / "bundles" / "approval.patch.json"
    shutil.copyfile(bundle_path, approval_bundle_path)

    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke", "tooling"],
    )
    _write_eval_case(
        tmp_path,
        case_id="approval.patch",
        title="Patch approval",
        bundle_name=approval_bundle_path.name,
        tags=["approval"],
    )
    output_dir = tmp_path / ".glassbox" / "evals" / "pre-commit"

    first_exit_code = main(
        [
            "eval",
            "run",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )

    stale_file = output_dir / "stale.json"
    stale_file.write_text("{}\n", encoding="utf-8")
    _ = capsys.readouterr()

    second_exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "smoke",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert "Artifacts: " + str(output_dir.resolve()) in captured.out
    assert (output_dir / "smoke.readme.json").is_file()
    assert not (output_dir / "approval.patch.json").exists()
    assert not stale_file.exists()
    assert summary["selected_case_count"] == 1
    assert summary["cases"][0]["case_id"] == "smoke.readme"


def test_cli_eval_run_rejects_refresh_outside_managed_output_tree(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path, _session_id = _export_eval_bundle(tmp_path, "smoke.readme")
    _write_eval_case(
        tmp_path,
        case_id="smoke.readme",
        title="README smoke",
        bundle_name=bundle_path.name,
        tags=["smoke"],
    )
    output_dir = tmp_path / "manual-output"

    exit_code = main(
        [
            "eval",
            "run",
            "--tag",
            "smoke",
            "--cwd",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--refresh-output-dir",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        "--refresh-output-dir requires an output directory under .glassbox/evals"
        in captured.err
    )
    assert not output_dir.exists()


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


def test_cli_chat_keeps_session_open_for_multiple_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(
        [
            "Inspect the repository",
            "Now summarize the tests.",
            "/exit",
        ]
    )

    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    exit_code = main(
        [
            "chat",
            "--no-dashboard",
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
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Started session" in captured.out
    assert "Queued user message: Inspect the repository" in captured.out
    assert "Assistant: I received your request: Inspect the repository" in captured.out
    assert "Queued user message: Now summarize the tests." in captured.out
    assert (
        "Assistant: I received your request: Now summarize the tests." in captured.out
    )
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.current_turn_id is None
    assert [message.role for message in transcript] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert transcript[0].parts[0].text == "Inspect the repository"
    assert transcript[1].parts[0].text == (
        "I received your request: Inspect the repository"
    )
    assert transcript[2].parts[0].text == "Now summarize the tests."
    assert transcript[3].parts[0].text == (
        "I received your request: Now summarize the tests."
    )


def test_cli_attach_keeps_existing_idle_session_open_for_new_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    interactive_inputs = iter(["Now summarize the tests.", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "attach",
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
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Attached to session {session_id}" in captured.out
    assert "Queued user message: Now summarize the tests." in captured.out
    assert (
        "Assistant: I received your request: Now summarize the tests." in captured.out
    )
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.current_turn_id is None
    assert transcript[-2].role == "user"
    assert transcript[-2].parts[0].text == "Now summarize the tests."
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == (
        "I received your request: Now summarize the tests."
    )


def test_cli_attach_answers_pending_question_for_existing_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(["blue", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
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

        repository = runtime_context.repositories.sessions
        session_id = repository.list_sessions()[0].session_id

        assert exit_code == 0

        exit_code = main(
            [
                "attach",
                str(session_id),
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
    assert f"Attached to session {session_id}" in captured.out
    assert "Pending question:" in captured.out
    assert "What colour should I use?" in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_chat_routes_pending_question_answers_without_question_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(["Pick a colour.", "blue", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    try:
        exit_code = main(
            [
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        repository = runtime_context.repositories.sessions
        session_id = repository.list_sessions()[0].session_id
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Interactive mode: type the next prompt" in captured.out
    assert "Question asked" in captured.out
    assert "Pending question:" in captured.out
    assert "Interactive mode: answer the pending question" in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_attach_approval_mode_requires_slash_commands_and_supports_status_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    interactive_inputs = iter(["hello", "/status", "/help", "/approve", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "attach",
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
    assert f"Attached to session {session_id}" in captured.out
    assert f"{approval_id}" in captured.out
    assert "Freeform text is disabled until you use /approve or /deny." in captured.out
    assert f"Session {session_id}" in captured.out
    assert "Interactive commands:" in captured.out
    assert "Approval resolved: approved by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"


def test_cli_attach_supports_deny_slash_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, _approval_id = _seed_pending_approval(tmp_path)
    interactive_inputs = iter(["/deny", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "attach",
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
    assert "Approval resolved: denied by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"
    assert isinstance(persisted_events[-1].payload, ApprovalResolved)
    assert persisted_events[-1].payload.decision == ApprovalDecision.DENIED


def test_cli_chat_redraws_prompt_and_routes_answer_after_question_arrives_mid_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    read_count = 0

    async def fake_read_interactive_input(prompt: str) -> str:
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            session_id = runtime_context.repositories.sessions.list_sessions()[
                0
            ].session_id
            await runtime_context.services.session_service.submit_user_message(
                session_id,
                "Pick a colour.",
            )
            await asyncio.sleep(0)
            return "blue"
        return "/exit"

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input_async",
        fake_read_interactive_input,
    )

    try:
        exit_code = main(
            [
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        session_id = runtime_context.repositories.sessions.list_sessions()[0].session_id
        state = runtime_context.repositories.sessions.get_session_state(session_id)
        transcript = runtime_context.repositories.sessions.list_transcript_messages(
            session_id
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Question asked (" in captured.out
    assert (
        "Interactive mode: type the next prompt, or use /status, /help, or /exit.\n"
        "prompt> "
    ) in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_chat_redraws_prompt_and_routes_approval_after_request_arrives_mid_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_approval_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    read_count = 0

    async def fake_read_interactive_input(prompt: str) -> str:
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            session_id = runtime_context.repositories.sessions.list_sessions()[
                0
            ].session_id
            await runtime_context.services.session_service.submit_user_message(
                session_id,
                "Apply the patch.",
            )
            await asyncio.sleep(0)
            return "/approve"
        return "/exit"

    monkeypatch.setattr(
        "glassbox.cli.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli._read_interactive_input_async",
        fake_read_interactive_input,
    )

    try:
        exit_code = main(
            [
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        session_id = runtime_context.repositories.sessions.list_sessions()[0].session_id
        state = runtime_context.repositories.sessions.get_session_state(session_id)
        persisted_events = runtime_context.repositories.sessions.read_session_events(
            session_id
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Approval requested: apply_patch (approval required:" in captured.out
    assert (
        "Interactive mode: type the next prompt, or use /status, /help, or /exit.\n"
        "prompt> "
    ) in captured.out
    assert "Approval resolved: approved by user" in captured.out
    assert "Assistant: Patch applied." in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_approval_id is None
    assert any(
        isinstance(event.payload, ApprovalResolved) for event in persisted_events
    )


def test_cli_chat_starts_dashboard_sidecar_and_records_live_dashboard_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    built_servers: list[FakeChatDashboardServer] = []

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        server = FakeChatDashboardServer(host=host, port=port)
        built_servers.append(server)
        return server

    monkeypatch.setattr(
        "glassbox.cli.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr("glassbox.cli._read_interactive_input", lambda prompt: "/exit")

    exit_code = main(
        [
            "chat",
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
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert len(built_servers) == 1
    assert built_servers[0].started is True
    assert built_servers[0].stopped is True
    assert (
        "Dashboard available at "
        f"http://127.0.0.1:8765/?session={session_id}" in captured.out
    )
    assert started_event.dashboard_url == "http://127.0.0.1:8765/"


def test_cli_chat_continues_without_dashboard_when_default_startup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        return FailingChatDashboardServer(host=host, port=port)

    monkeypatch.setattr(
        "glassbox.cli.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr("glassbox.cli._read_interactive_input", lambda prompt: "/exit")

    exit_code = main(
        [
            "chat",
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
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Warning: dashboard unavailable at http://127.0.0.1:8765/" in captured.err
    assert "Dashboard available at " not in captured.out
    assert started_event.dashboard_url is None


def test_cli_chat_fails_when_explicit_dashboard_binding_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fail_if_prompted(prompt: str) -> Any:
        raise AssertionError(f"interactive prompt should not be reached: {prompt}")

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        return FailingChatDashboardServer(host=host, port=port)

    monkeypatch.setattr(
        "glassbox.cli.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr("glassbox.cli._read_interactive_input", fail_if_prompted)

    exit_code = main(
        [
            "chat",
            "--dashboard-port",
            "9876",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        sessions = SQLiteSessionRepository(connection).list_sessions()
    finally:
        connection.close()

    assert exit_code == 1
    assert (
        "dashboard startup failed at http://127.0.0.1:9876/: web server failed to start"
        == captured.err.strip()
    )
    assert sessions == []


def test_cli_chat_can_disable_dashboard_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fail_if_built(*args, **kwargs):
        raise AssertionError("dashboard sidecar should not be built")

    monkeypatch.setattr("glassbox.cli.build_web_server", fail_if_built)
    monkeypatch.setattr("glassbox.cli._read_interactive_input", lambda prompt: "/exit")

    exit_code = main(
        [
            "chat",
            "--no-dashboard",
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
        session_id = repository.list_sessions()[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Dashboard available at " not in captured.out
    assert started_event.dashboard_url is None


def test_cli_attach_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000001")

    exit_code = main(
        [
            "attach",
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


def test_cli_attach_rejects_completed_session(
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
            "attach",
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
        f"cannot attach session {session_id} in status completed"
    )


def test_cli_attach_rejects_failed_session(
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
                    error_message="model backend unavailable",
                    retryable=True,
                ),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "attach",
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
        f"cannot attach session {session_id} in status failed"
    )


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
    assert "Dashboard URL:" not in captured.out
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
