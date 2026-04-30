"""Unit tests for review-gated workspace memory extraction."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from glassbox.core import ContextCompactionCreated
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionScope
from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import ModelToolCallRequested
from glassbox.core import RuntimeNoteRecord
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationResidualRiskAccepted
from glassbox.core import TaskVerificationStatus
from glassbox.core import ToolExecutionCompleted
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationFailureCategory
from glassbox.core import VerificationFailureDigest
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import new_artifact_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import ModelMemorySuggestion
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService


def test_automatic_extraction_suppresses_dedupes_expires_and_redacts() -> None:
    session_id = new_session_id()
    now = datetime(2026, 4, 29, 12, tzinfo=UTC)
    stable_tool_call_id = new_tool_call_id()
    first_failure_tool_call_id = new_tool_call_id()
    second_failure_tool_call_id = new_tool_call_id()
    repository = FakeMemoryCaptureRepository(
        session_id,
        runtime_notes=[
            _runtime_note(
                session_id,
                1,
                "operator",
                "Prefer uv run pytest for backend tests.",
                now,
            ),
            _runtime_note(
                session_id,
                2,
                "operator",
                "Prefer uv run pytest for backend tests.",
                now,
            ),
            _runtime_note(
                session_id,
                3,
                "debug",
                "Temporary scratch observation should not become memory.",
                now,
            ),
            _runtime_note(
                session_id,
                4,
                "operator",
                "Old convention should expire before review.",
                now - timedelta(days=45),
            ),
        ],
        events=[
            _tool_request(session_id, stable_tool_call_id, "uv run pytest tests/unit"),
            _tool_completed(session_id, stable_tool_call_id, True, "pytest passed"),
            _tool_completed(
                session_id,
                first_failure_tool_call_id,
                False,
                "provider failed token=abcdefghijklmnopqrstuvwxyz123456",
            ),
            _tool_completed(
                session_id,
                second_failure_tool_call_id,
                False,
                "provider failed token=abcdefghijklmnopqrstuvwxyz123456",
            ),
        ],
    )

    candidates = WorkspaceMemoryCaptureService(repository).list_candidates(
        session_id,
        now=now,
    )

    summaries = [candidate.summary for candidate in candidates]
    assert summaries.count("Prefer uv run pytest for backend tests.") == 1
    assert "Stable command: uv run pytest tests/unit" in summaries
    assert any(
        summary.startswith("Repeated failure:") for summary in summaries if summary
    )
    assert all("Temporary scratch" not in candidate.content for candidate in candidates)
    assert all("Old convention" not in candidate.content for candidate in candidates)
    failure_candidate = next(
        candidate
        for candidate in candidates
        if candidate.kind == WorkspaceMemoryKind.FAILURE_PATTERN
    )
    assert failure_candidate.redacted is True
    assert "<redacted>" in failure_candidate.content


def test_model_assisted_extraction_is_review_only_and_confidence_gated() -> None:
    session_id = new_session_id()
    repository = FakeMemoryCaptureRepository(session_id)
    service = WorkspaceMemoryCaptureService(repository)

    candidates = service.list_model_assisted_candidates(
        session_id,
        [
            ModelMemorySuggestion(
                kind=WorkspaceMemoryKind.CONVENTION,
                content="Prefer compact PR descriptions for release branches.",
                confidence=0.9,
            ),
            ModelMemorySuggestion(
                content="Maybe remember this vague thing.",
                confidence=0.2,
            ),
        ],
        policy=MemoryExtractionPolicy(
            allow_model_assisted=True, min_model_confidence=0.7
        ),
    )

    assert len(candidates) == 1
    assert candidates[0].kind == WorkspaceMemoryKind.CONVENTION
    assert candidates[0].tags == ["model-assisted"]
    assert repository.appended_events == []


def test_long_run_memory_candidates_preserve_review_gate_and_provenance() -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    artifact_id = new_artifact_id()
    stale_artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    failed_a = new_task_verification_id()
    failed_b = new_task_verification_id()
    risk_id = new_task_verification_id()
    now = datetime(2026, 4, 29, 12, tzinfo=UTC)
    repository = FakeMemoryCaptureRepository(
        session_id,
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=10,
                created_at=now,
                payload=TaskCheckpointCreated(
                    checkpoint_id=new_task_checkpoint_id(),
                    task_id=task_id,
                    objective="Finish provider recovery safely",
                    current_phase=LongRunPhase.VERIFYING,
                    completed_step="captured retry state",
                    next_action="rerun focused tests",
                    recovery_guidance="resume from checkpoint after approval",
                    verification_status="pytest passed",
                    source_start_sequence=1,
                    source_end_sequence=9,
                    artifact_id=artifact_id,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=11,
                created_at=now,
                payload=ContextCompactionCreated(
                    compaction_id=new_context_compaction_id(),
                    scope=ContextCompactionScope.TASK,
                    source_start_sequence=1,
                    source_end_sequence=10,
                    summary="Provider retry findings should be reviewed before resume.",
                    artifact_id=artifact_id,
                    freshness=ContextCompactionFreshness.FRESH,
                    task_id=task_id,
                    limitations=["network canary was skipped"],
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=12,
                created_at=now,
                payload=ContextCompactionCreated(
                    compaction_id=new_context_compaction_id(),
                    scope=ContextCompactionScope.TASK,
                    source_start_sequence=1,
                    source_end_sequence=10,
                    summary="Stale compaction should not become active memory.",
                    artifact_id=stale_artifact_id,
                    freshness=ContextCompactionFreshness.STALE,
                    task_id=task_id,
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=13,
                created_at=now,
                payload=TaskVerificationPlanned(
                    task_id=task_id,
                    verification=VerificationPlanEntry(
                        verification_id=verification_id,
                        check_name="pytest provider recovery",
                        kind=VerificationCheckKind.TEST,
                        command=["uv", "run", "pytest", "tests/unit"],
                        source=VerificationPlanSource.OPERATOR,
                        rationale="focused long-run recovery proof",
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=14,
                created_at=now,
                payload=TaskVerificationCompleted(
                    task_id=task_id,
                    verification_id=verification_id,
                    status=TaskVerificationStatus.PASSED,
                    summary="provider recovery tests passed",
                    artifact_id=artifact_id,
                ),
            ),
            _verification_failed(
                session_id,
                task_id,
                failed_a,
                "provider token=abcdefghijklmnopqrstuvwxyz123456 failed",
                15,
                now,
                artifact_id,
            ),
            _verification_failed(
                session_id,
                task_id,
                failed_b,
                "provider token=abcdefghijklmnopqrstuvwxyz123456 failed",
                16,
                now,
                artifact_id,
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=17,
                created_at=now,
                payload=TaskVerificationResidualRiskAccepted(
                    task_id=task_id,
                    verification_id=risk_id,
                    reason="live canary skipped until credentials are available",
                    residual_risks=["provider behavior remains advisory"],
                ),
            ),
        ],
    )

    service = WorkspaceMemoryCaptureService(repository)
    candidates = service.list_candidates(session_id, now=now)

    assert repository.appended_events == []
    assert any("checkpoint" in candidate.tags for candidate in candidates)
    assert any("compaction" in candidate.tags for candidate in candidates)
    assert any("last-known-good" in candidate.tags for candidate in candidates)
    assert any("accepted-risk" in candidate.tags for candidate in candidates)
    assert all("Stale compaction" not in candidate.content for candidate in candidates)
    repeated = next(
        candidate
        for candidate in candidates
        if candidate.tags == ["long-run", "failure-pattern", "verification"]
    )
    assert repeated.redacted is True
    assert "<redacted>" in repeated.content or "<redacted-token>" in repeated.content
    assert repeated.provenance.session_id == session_id
    assert repeated.provenance.source_sequence == 16
    assert repeated.provenance.note == f"artifact_id={artifact_id}"


def _runtime_note(
    session_id,
    sequence: int,
    category: str,
    message: str,
    created_at: datetime,
) -> RuntimeNoteRecord:
    return RuntimeNoteRecord(
        source_session_id=session_id,
        source_sequence=sequence,
        category=category,
        message=message,
        created_at=created_at,
    )


def _tool_request(session_id, tool_call_id, command: str) -> EventEnvelope:
    turn_id = new_turn_id()
    return EventEnvelope(
        session_id=session_id,
        sequence=0,
        payload=ModelToolCallRequested(
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            tool_name="run_command",
            arguments_json=f'{{"command": "{command}"}}',
        ),
    )


def _tool_completed(
    session_id,
    tool_call_id,
    success: bool,
    summary: str,
) -> EventEnvelope:
    return EventEnvelope(
        session_id=session_id,
        sequence=0,
        payload=ToolExecutionCompleted(
            turn_id=new_turn_id(),
            tool_call_id=tool_call_id,
            success=success,
            exit_code=0 if success else 1,
            summary=summary,
        ),
    )


def _verification_failed(
    session_id,
    task_id,
    verification_id,
    summary: str,
    sequence: int,
    created_at: datetime,
    artifact_id,
) -> EventEnvelope:
    return EventEnvelope(
        session_id=session_id,
        sequence=sequence,
        created_at=created_at,
        payload=TaskVerificationFailed(
            task_id=task_id,
            verification_id=verification_id,
            failure=VerificationFailureDigest(
                category=VerificationFailureCategory.INFRASTRUCTURE,
                summary=summary,
                exit_code=1,
                artifact_id=artifact_id,
            ),
        ),
    )


class FakeMemoryCaptureRepository:
    def __init__(
        self,
        session_id,
        *,
        runtime_notes=None,
        events=None,
    ) -> None:
        self.session = SessionRecord(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            created_at=datetime(2026, 4, 29, 12, tzinfo=UTC),
            updated_at=datetime(2026, 4, 29, 12, tzinfo=UTC),
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=0,
        )
        self.session_state = SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=0,
        )
        self.runtime_notes = list(runtime_notes or [])
        self.events = list(events or [])
        self.appended_events: list[EventEnvelope] = []

    def get_session(self, session_id):
        return self.session if self.session.session_id == session_id else None

    def list_runtime_notes(self, session_id, *, include_inherited=True):
        return list(self.runtime_notes)

    def list_tasks(self, *, session_id=None, limit=None, offset=0):
        return []

    def read_session_events(self, session_id):
        return list(self.events)

    def append_event(self, event):
        self.appended_events.append(event)
        return event

    def append_events(self, events):
        self.appended_events.extend(events)
        return list(events)

    def get_workspace_memory(self, memory_id):
        return None
