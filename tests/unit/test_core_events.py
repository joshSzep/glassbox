"""Unit tests for Glassbox core event models."""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from glassbox.core import ApprovalDecision
from glassbox.core import ApprovalRequested
from glassbox.core import ApprovalResolved
from glassbox.core import AssistantMessageCompleted
from glassbox.core import BackgroundJobAbandoned
from glassbox.core import BackgroundJobCancellationRequested
from glassbox.core import BackgroundJobCancelled
from glassbox.core import BackgroundJobClaimed
from glassbox.core import BackgroundJobCompleted
from glassbox.core import BackgroundJobCreated
from glassbox.core import BackgroundJobFailed
from glassbox.core import BackgroundJobFailureKind
from glassbox.core import BackgroundJobHeartbeat
from glassbox.core import BackgroundJobKind
from glassbox.core import BackgroundJobPaused
from glassbox.core import BackgroundJobProgressRecorded
from glassbox.core import BackgroundJobRecoveryReason
from glassbox.core import BackgroundJobRecoveryRecorded
from glassbox.core import BackgroundJobRetryExhausted
from glassbox.core import BackgroundJobRetryRequested
from glassbox.core import BackgroundJobStarted
from glassbox.core import BackgroundJobState
from glassbox.core import CancellationAcknowledged
from glassbox.core import CancellationFailed
from glassbox.core import CancellationRequested
from glassbox.core import ContextCompactionCreated
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionFreshnessChanged
from glassbox.core import ContextCompactionScope
from glassbox.core import ContinuationWindowExpired
from glassbox.core import ContinuationWindowRequested
from glassbox.core import ContinuationWindowResolved
from glassbox.core import ErrorRecorded
from glassbox.core import EventEnvelope
from glassbox.core import EventPayloadType
from glassbox.core import LongRunPhase
from glassbox.core import LongRunPhaseChanged
from glassbox.core import LongRunPhaseState
from glassbox.core import MessagePart
from glassbox.core import PauseWindowCancelled
from glassbox.core import PauseWindowPolicy
from glassbox.core import PauseWindowScheduled
from glassbox.core import PauseWindowTriggered
from glassbox.core import ProviderRecoveryAction
from glassbox.core import ProviderRecoveryKind
from glassbox.core import ProviderRecoveryRecorded
from glassbox.core import RecoveryDecision
from glassbox.core import RecoveryDecisionRecorded
from glassbox.core import ResumeOutcomeRecorded
from glassbox.core import ResumeOutcomeStatus
from glassbox.core import SessionStarted
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskCreated
from glassbox.core import TaskPaused
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepCompleted
from glassbox.core import TaskStepFailed
from glassbox.core import TaskStepStarted
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationStarted
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptStatus
from glassbox.core import ToolOutputChunk
from glassbox.core import TranscriptMessageImported
from glassbox.core import TurnCancelled
from glassbox.core import TurnStatus
from glassbox.core import TurnStatusChanged
from glassbox.core import UserMessageReceived
from glassbox.core import WorkspaceMemoryCandidateRejected
from glassbox.core import WorkspaceMemoryConfirmed
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryImported
from glassbox.core import WorkspaceMemoryInvalidated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemoryPruned
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryState
from glassbox.core import WorkspaceMemoryUpdated
from glassbox.core import WorkspaceMemoryUsedInContext
from glassbox.core import new_approval_id
from glassbox.core import new_artifact_id
from glassbox.core import new_background_job_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_message_id
from glassbox.core import new_pause_window_id
from glassbox.core import new_recovery_decision_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id


def test_event_envelope_round_trip() -> None:
    payload = SessionStarted(
        cwd="/tmp/glassbox",
        dashboard_url="http://127.0.0.1:8765",
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        parent_session_id=new_session_id(),
        forked_from_turn_id=new_turn_id(),
        forked_from_sequence=7,
        branch_label="alt-branch",
    )
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=1,
        payload=payload,
    )

    restored = EventEnvelope.model_validate(envelope.model_dump(mode="python"))

    assert restored == envelope
    assert restored.event_type == "SessionStarted"
    assert restored.event_version == 1


def test_session_started_payload_remains_backward_compatible_without_lineage() -> None:
    payload = SessionStarted.model_validate(
        {
            "event_type": "SessionStarted",
            "cwd": "/tmp/glassbox",
            "model_name": "openai:gpt-5.4",
            "approval_mode": "confirm",
        }
    )

    assert payload.parent_session_id is None
    assert payload.forked_from_turn_id is None
    assert payload.forked_from_sequence is None
    assert payload.branch_label is None


def test_event_envelope_populates_event_type_from_payload() -> None:
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=2,
        payload=UserMessageReceived(
            message_id=new_message_id(),
            text="Inspect the repository",
        ),
    )

    assert envelope.event_type == "UserMessageReceived"
    assert envelope.message_id is not None


def test_event_envelope_rejects_mismatched_event_type() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {
                "session_id": new_session_id(),
                "sequence": 3,
                "event_type": "SessionCompleted",
                "payload": {
                    "event_type": "SessionStarted",
                    "cwd": "/tmp/glassbox",
                    "model_name": "openai:gpt-5.4",
                    "approval_mode": "confirm",
                },
            }
        )


def test_event_payload_union_validates_representative_payloads() -> None:
    adapter = TypeAdapter(EventPayloadType)

    tool_chunk = adapter.validate_python(
        {
            "event_type": "ToolOutputChunk",
            "turn_id": new_turn_id(),
            "tool_call_id": new_tool_call_id(),
            "stream": "stdout",
            "chunk": "hello\n",
        }
    )
    approval_resolved = adapter.validate_python(
        {
            "event_type": "ApprovalResolved",
            "approval_id": new_approval_id(),
            "decision": "approved",
            "decided_by": "user",
        }
    )

    assert isinstance(tool_chunk, ToolOutputChunk)
    assert isinstance(approval_resolved, ApprovalResolved)
    assert approval_resolved.decision == ApprovalDecision.APPROVED


def test_continuation_window_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    approval_id = new_approval_id()
    approved_until = datetime(2026, 4, 30, 12, 15, tzinfo=UTC)

    requested = adapter.validate_python(
        {
            "event_type": "ContinuationWindowRequested",
            "approval_id": approval_id,
            "scope": "task",
            "task_id": task_id,
            "requested_minutes": 15,
            "requested_by": "operator",
            "reason": "continue through focused tests",
        }
    )
    resolved = adapter.validate_python(
        {
            "event_type": "ContinuationWindowResolved",
            "approval_id": approval_id,
            "decision": "approved",
            "decided_by": "operator",
            "approved_minutes": 15,
            "approved_until": approved_until,
            "task_id": task_id,
        }
    )
    expired = adapter.validate_python(
        {
            "event_type": "ContinuationWindowExpired",
            "approval_id": approval_id,
            "scope": "task",
            "task_id": task_id,
            "expired_at": approved_until,
            "stop_reason": "window expired",
        }
    )

    assert isinstance(requested, ContinuationWindowRequested)
    assert isinstance(resolved, ContinuationWindowResolved)
    assert isinstance(expired, ContinuationWindowExpired)
    assert resolved.decision == ApprovalDecision.APPROVED


def test_pause_window_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    pause_window_id = new_pause_window_id()
    pause_before = datetime(2026, 4, 30, 12, tzinfo=UTC)

    scheduled = adapter.validate_python(
        {
            "event_type": "PauseWindowScheduled",
            "pause_window_id": pause_window_id,
            "scope": "task",
            "policy": "before_time",
            "task_id": task_id,
            "pause_before": pause_before,
            "reason": "pause before local stop window",
        }
    )
    triggered = adapter.validate_python(
        {
            "event_type": "PauseWindowTriggered",
            "pause_window_id": pause_window_id,
            "scope": "task",
            "policy": "before_time",
            "task_id": task_id,
            "triggered_at": pause_before,
            "stop_reason": "pause window triggered",
        }
    )
    cancelled = adapter.validate_python(
        {
            "event_type": "PauseWindowCancelled",
            "pause_window_id": pause_window_id,
            "task_id": task_id,
            "cancelled_by": "operator",
            "reason": "manual override",
        }
    )

    assert isinstance(scheduled, PauseWindowScheduled)
    assert isinstance(triggered, PauseWindowTriggered)
    assert isinstance(cancelled, PauseWindowCancelled)
    assert scheduled.policy == PauseWindowPolicy.BEFORE_TIME


def test_event_payload_union_rejects_unknown_event_type() -> None:
    adapter = TypeAdapter(EventPayloadType)

    with pytest.raises(ValidationError):
        adapter.validate_python({"event_type": "UnknownEvent"})


def test_turn_status_changed_uses_shared_turn_status_type() -> None:
    payload = TurnStatusChanged(
        turn_id=new_turn_id(),
        status=TurnStatus.EXECUTING_TOOL,
    )

    assert payload.status == TurnStatus.EXECUTING_TOOL


def test_cancellation_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()

    requested = adapter.validate_python(
        {
            "event_type": "CancellationRequested",
            "turn_id": turn_id,
            "requested_by": "terminal",
            "reason": "operator pressed Ctrl+C",
        }
    )
    acknowledged = adapter.validate_python(
        {
            "event_type": "CancellationAcknowledged",
            "turn_id": turn_id,
            "repeated": True,
        }
    )
    turn_cancelled = adapter.validate_python(
        {
            "event_type": "TurnCancelled",
            "turn_id": turn_id,
            "reason": "operator requested cancellation",
            "stage": "model_call",
        }
    )
    tool_cancelled = adapter.validate_python(
        {
            "event_type": "ToolExecutionCancelled",
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "summary": "cancelled by operator",
        }
    )
    failed = adapter.validate_python(
        {
            "event_type": "CancellationFailed",
            "turn_id": turn_id,
            "reason": "turn already completed",
        }
    )

    assert isinstance(requested, CancellationRequested)
    assert isinstance(acknowledged, CancellationAcknowledged)
    assert isinstance(turn_cancelled, TurnCancelled)
    assert tool_cancelled.tool_call_id == tool_call_id
    assert isinstance(failed, CancellationFailed)


def test_turn_cancelled_rejects_unknown_stage() -> None:
    with pytest.raises(ValidationError):
        TurnCancelled.model_validate(
            {
                "event_type": "TurnCancelled",
                "turn_id": new_turn_id(),
                "reason": "operator requested cancellation",
                "stage": "approval_queue",
            }
        )


def test_background_job_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    job_id = new_background_job_id()
    worker_id = "daemon:1234"
    claim_token = "claim-token"
    lease_expires_at = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    created = adapter.validate_python(
        {
            "event_type": "BackgroundJobCreated",
            "job_id": job_id,
            "kind": "read_only_maintenance",
            "job_type": "projection-health-refresh",
            "title": "Refresh projection health",
            "payload": {"scope": "all"},
        }
    )
    claimed = adapter.validate_python(
        {
            "event_type": "BackgroundJobClaimed",
            "job_id": job_id,
            "worker_id": worker_id,
            "claim_token": claim_token,
            "attempt": 1,
            "lease_expires_at": lease_expires_at,
        }
    )
    started = adapter.validate_python(
        {
            "event_type": "BackgroundJobStarted",
            "job_id": job_id,
            "worker_id": worker_id,
            "claim_token": claim_token,
            "attempt": 1,
        }
    )
    heartbeat = adapter.validate_python(
        {
            "event_type": "BackgroundJobHeartbeat",
            "job_id": job_id,
            "worker_id": worker_id,
            "claim_token": claim_token,
            "lease_expires_at": lease_expires_at,
            "message": "still scanning",
        }
    )
    progress = adapter.validate_python(
        {
            "event_type": "BackgroundJobProgressRecorded",
            "job_id": job_id,
            "message": "scanned projections",
            "completed_units": 3,
            "total_units": 5,
        }
    )
    paused = adapter.validate_python(
        {
            "event_type": "BackgroundJobPaused",
            "job_id": job_id,
            "reason": "approval_required",
        }
    )
    completed = adapter.validate_python(
        {
            "event_type": "BackgroundJobCompleted",
            "job_id": job_id,
            "summary": "projection health refreshed",
        }
    )
    failed = adapter.validate_python(
        {
            "event_type": "BackgroundJobFailed",
            "job_id": job_id,
            "failure_kind": "storage_error",
            "message": "database locked",
            "retryable": True,
            "attempt": 1,
            "artifact_path": ".glassbox/sessions/session/artifacts/failure.log",
        }
    )
    cancellation_requested = adapter.validate_python(
        {
            "event_type": "BackgroundJobCancellationRequested",
            "job_id": job_id,
            "requested_by": "operator",
            "reason": "no longer needed",
        }
    )
    cancelled = adapter.validate_python(
        {
            "event_type": "BackgroundJobCancelled",
            "job_id": job_id,
            "reason": "operator requested cancellation",
        }
    )
    recovery = adapter.validate_python(
        {
            "event_type": "BackgroundJobRecoveryRecorded",
            "job_id": job_id,
            "reason": "stale_claim",
            "previous_state": "running",
            "detail": "worker process exited",
        }
    )
    retry_requested = adapter.validate_python(
        {
            "event_type": "BackgroundJobRetryRequested",
            "job_id": job_id,
            "requested_by": "operator",
            "reason": "transient provider outage",
        }
    )
    retry_exhausted = adapter.validate_python(
        {
            "event_type": "BackgroundJobRetryExhausted",
            "job_id": job_id,
            "retry_budget": 3,
            "reason": "retry budget exhausted",
        }
    )
    abandoned = adapter.validate_python(
        {
            "event_type": "BackgroundJobAbandoned",
            "job_id": job_id,
            "abandoned_by": "operator",
            "reason": "superseded",
        }
    )

    assert isinstance(created, BackgroundJobCreated)
    assert created.kind == BackgroundJobKind.READ_ONLY_MAINTENANCE
    assert isinstance(claimed, BackgroundJobClaimed)
    assert isinstance(started, BackgroundJobStarted)
    assert isinstance(heartbeat, BackgroundJobHeartbeat)
    assert heartbeat.state == BackgroundJobState.RUNNING
    assert isinstance(progress, BackgroundJobProgressRecorded)
    assert isinstance(paused, BackgroundJobPaused)
    assert isinstance(completed, BackgroundJobCompleted)
    assert isinstance(failed, BackgroundJobFailed)
    assert failed.failure_kind == BackgroundJobFailureKind.STORAGE_ERROR
    assert failed.artifact_path == ".glassbox/sessions/session/artifacts/failure.log"
    assert isinstance(cancellation_requested, BackgroundJobCancellationRequested)
    assert isinstance(cancelled, BackgroundJobCancelled)
    assert isinstance(recovery, BackgroundJobRecoveryRecorded)
    assert recovery.reason == BackgroundJobRecoveryReason.STALE_CLAIM
    assert isinstance(retry_requested, BackgroundJobRetryRequested)
    assert isinstance(retry_exhausted, BackgroundJobRetryExhausted)
    assert isinstance(abandoned, BackgroundJobAbandoned)


def test_background_job_envelope_exposes_job_id() -> None:
    job_id = new_background_job_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=12,
        payload=BackgroundJobCreated(
            job_id=job_id,
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="repo-index-refresh",
            title="Refresh repository index",
        ),
    )

    assert envelope.event_type == "BackgroundJobCreated"
    assert envelope.job_id == job_id


def test_long_run_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    tool_attempt_id = new_tool_attempt_id()
    checkpoint_id = new_task_checkpoint_id()
    compaction_id = new_context_compaction_id()
    recovery_decision_id = new_recovery_decision_id()

    phase = adapter.validate_python(
        {
            "event_type": "LongRunPhaseChanged",
            "phase": "tool_execution",
            "state": "entered",
            "task_id": task_id,
            "turn_id": turn_id,
            "tool_attempt_id": tool_attempt_id,
            "reason": "running tests",
        }
    )
    checkpoint = adapter.validate_python(
        {
            "event_type": "TaskCheckpointCreated",
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "turn_id": turn_id,
            "objective": "finish the release task",
            "current_phase": "checkpointing",
            "completed_step": "updated docs",
            "next_action": "run focused tests",
            "recovery_guidance": "resume from the next test command",
            "blockers": ["provider unavailable"],
            "touched_files": ["docs/tasks-v10.md"],
            "verification_status": "pending",
            "budget_status": "within budget",
            "source_start_sequence": 10,
            "source_end_sequence": 14,
        }
    )
    compaction = adapter.validate_python(
        {
            "event_type": "ContextCompactionCreated",
            "compaction_id": compaction_id,
            "scope": "transcript",
            "source_start_sequence": 3,
            "source_end_sequence": 9,
            "summary": "summarized earlier work",
            "artifact_id": new_artifact_id(),
            "freshness": "fresh",
            "checkpoint_id": checkpoint_id,
        }
    )
    compaction_freshness = adapter.validate_python(
        {
            "event_type": "ContextCompactionFreshnessChanged",
            "compaction_id": compaction_id,
            "freshness": "invalidated",
            "reason": "operator rejected the summary",
            "changed_by": "operator",
        }
    )
    heartbeat = adapter.validate_python(
        {
            "event_type": "ToolAttemptHeartbeat",
            "tool_attempt_id": tool_attempt_id,
            "status": "running",
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "tool_name": "run_tests",
            "message": "pytest still running",
            "completed_units": 3,
            "total_units": 10,
            "safe_to_retry": False,
            "retry_classification": "already_running",
            "retry_requires_approval": False,
        }
    )
    decision = adapter.validate_python(
        {
            "event_type": "RecoveryDecisionRecorded",
            "recovery_decision_id": recovery_decision_id,
            "decision": "retry",
            "reason": "tool attempt timed out before completion",
            "safe_to_resume": False,
            "next_action": "rerun the failed command from checkpoint",
            "tool_attempt_id": tool_attempt_id,
            "checkpoint_id": checkpoint_id,
        }
    )
    outcome = adapter.validate_python(
        {
            "event_type": "ResumeOutcomeRecorded",
            "outcome": "resumed",
            "summary": "continued from checkpoint",
            "checkpoint_id": checkpoint_id,
            "recovery_decision_id": recovery_decision_id,
        }
    )
    provider_recovery = adapter.validate_python(
        {
            "event_type": "ProviderRecoveryRecorded",
            "provider": "openai",
            "model_name": "gpt-5.4",
            "failure_kind": "rate_limit",
            "action": "retry_scheduled",
            "reason": "rate limit exceeded",
            "retryable": True,
            "safe_to_continue": True,
            "operator_next_action": "wait for bounded retry",
            "turn_id": turn_id,
            "attempt": 1,
            "max_attempts": 3,
            "backoff_seconds": 4,
        }
    )

    assert isinstance(phase, LongRunPhaseChanged)
    assert phase.phase == LongRunPhase.TOOL_EXECUTION
    assert phase.state == LongRunPhaseState.ENTERED
    assert isinstance(checkpoint, TaskCheckpointCreated)
    assert checkpoint.checkpoint_id == checkpoint_id
    assert checkpoint.current_phase == LongRunPhase.CHECKPOINTING
    assert checkpoint.touched_files == ["docs/tasks-v10.md"]
    assert checkpoint.source_start_sequence == 10
    assert checkpoint.source_end_sequence == 14
    assert isinstance(compaction, ContextCompactionCreated)
    assert compaction.scope == ContextCompactionScope.TRANSCRIPT
    assert compaction.freshness == ContextCompactionFreshness.FRESH
    assert isinstance(compaction_freshness, ContextCompactionFreshnessChanged)
    assert compaction_freshness.freshness == ContextCompactionFreshness.INVALIDATED
    assert isinstance(heartbeat, ToolAttemptHeartbeat)
    assert heartbeat.status == ToolAttemptStatus.RUNNING
    assert heartbeat.retry_classification == "already_running"
    assert heartbeat.retry_requires_approval is False
    assert isinstance(decision, RecoveryDecisionRecorded)
    assert decision.decision == RecoveryDecision.RETRY
    assert isinstance(outcome, ResumeOutcomeRecorded)
    assert outcome.outcome == ResumeOutcomeStatus.RESUMED
    assert isinstance(provider_recovery, ProviderRecoveryRecorded)
    assert provider_recovery.failure_kind == ProviderRecoveryKind.RATE_LIMIT
    assert provider_recovery.action == ProviderRecoveryAction.RETRY_SCHEDULED


def test_long_run_envelope_exposes_correlation_ids() -> None:
    checkpoint_id = new_task_checkpoint_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=18,
        payload=TaskCheckpointCreated(
            checkpoint_id=checkpoint_id,
            objective="ship v10 event vocabulary",
            next_action="run event tests",
            recovery_guidance="resume with the focused validation command",
        ),
    )

    assert envelope.event_type == "TaskCheckpointCreated"
    assert envelope.checkpoint_id == checkpoint_id


def test_context_compaction_rejects_inverted_source_range() -> None:
    with pytest.raises(ValidationError):
        ContextCompactionCreated(
            compaction_id=new_context_compaction_id(),
            scope=ContextCompactionScope.TRANSCRIPT,
            source_start_sequence=10,
            source_end_sequence=3,
            summary="bad source range",
            artifact_id=new_artifact_id(),
        )


def test_task_checkpoint_rejects_inverted_source_range() -> None:
    with pytest.raises(ValidationError):
        TaskCheckpointCreated(
            checkpoint_id=new_task_checkpoint_id(),
            objective="bad checkpoint",
            next_action="fix source range",
            recovery_guidance="create a checkpoint with an ordered event range",
            source_start_sequence=12,
            source_end_sequence=3,
        )


def test_workspace_memory_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    memory_id = new_workspace_memory_id()
    session_id = new_session_id()
    turn_id = new_turn_id()
    provenance = {
        "source_type": "session_event",
        "session_id": str(session_id),
        "source_sequence": 9,
        "source_label": "operator note",
    }

    created = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryCreated",
            "memory_id": memory_id,
            "kind": "command",
            "content": "Use uv run pytest for backend validation.",
            "summary": "backend validation command",
            "provenance": provenance,
            "tags": ["testing"],
        }
    )
    confirmed = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryConfirmed",
            "memory_id": memory_id,
            "confirmed_by": "operator",
        }
    )
    updated = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryUpdated",
            "memory_id": memory_id,
            "content": "Use uv run pytest tests/unit/test_core_events.py.",
            "reason": "narrower command",
        }
    )
    invalidated = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryInvalidated",
            "memory_id": memory_id,
            "reason": "command changed",
        }
    )
    imported = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryImported",
            "memory_id": new_workspace_memory_id(),
            "kind": "fact",
            "content": "Imported memory is redacted by default.",
            "provenance": {"source_type": "import", "source_label": "bundle"},
            "import_source": "portable-session-export",
        }
    )
    used = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryUsedInContext",
            "memory_id": memory_id,
            "turn_id": turn_id,
            "prompt_section": "workspace_memory",
            "reason": "matches backend test request",
        }
    )
    pruned = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryPruned",
            "memory_id": memory_id,
            "reason": "superseded",
        }
    )
    rejected = adapter.validate_python(
        {
            "event_type": "WorkspaceMemoryCandidateRejected",
            "candidate_id": "candidate-1",
            "kind": "command",
            "content_summary": "backend validation command",
            "provenance": provenance,
            "reason": "too noisy",
        }
    )

    assert isinstance(created, WorkspaceMemoryCreated)
    assert created.kind == WorkspaceMemoryKind.COMMAND
    assert isinstance(created.provenance, WorkspaceMemoryProvenance)
    assert created.provenance.source_type == WorkspaceMemorySourceType.SESSION_EVENT
    assert isinstance(confirmed, WorkspaceMemoryConfirmed)
    assert isinstance(updated, WorkspaceMemoryUpdated)
    assert isinstance(invalidated, WorkspaceMemoryInvalidated)
    assert isinstance(imported, WorkspaceMemoryImported)
    assert isinstance(used, WorkspaceMemoryUsedInContext)
    assert used.state_at_use == WorkspaceMemoryState.ACTIVE
    assert isinstance(pruned, WorkspaceMemoryPruned)
    assert isinstance(rejected, WorkspaceMemoryCandidateRejected)


def test_workspace_memory_envelope_exposes_memory_id() -> None:
    memory_id = new_workspace_memory_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=4,
        payload=WorkspaceMemoryCreated(
            memory_id=memory_id,
            kind=WorkspaceMemoryKind.FACT,
            content="Glassbox memory is workspace scoped.",
            provenance=WorkspaceMemoryProvenance(
                source_type=WorkspaceMemorySourceType.OPERATOR,
                source_label="manual note",
            ),
        ),
    )

    assert envelope.event_type == "WorkspaceMemoryCreated"
    assert envelope.memory_id == memory_id


def test_background_job_created_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        BackgroundJobCreated.model_validate(
            {
                "event_type": "BackgroundJobCreated",
                "job_id": new_background_job_id(),
                "kind": "remote_worker",
                "job_type": "remote",
                "title": "Remote work",
            }
        )


def test_assistant_message_completed_uses_message_parts() -> None:
    payload = AssistantMessageCompleted(
        message_id=new_message_id(),
        parts=[MessagePart(kind="text", text="done")],
    )

    assert payload.parts[0].kind == "text"


def test_event_envelope_exposes_correlation_fields() -> None:
    turn_id = new_turn_id()
    approval_id = new_approval_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=4,
        payload=ApprovalRequested(
            approval_id=approval_id,
            turn_id=turn_id,
            reason="Command writes files",
            subject="apply_patch",
        ),
    )

    assert envelope.turn_id == turn_id
    assert envelope.approval_id == approval_id


def test_error_recorded_rejects_invalid_scope() -> None:
    with pytest.raises(ValidationError):
        ErrorRecorded.model_validate(
            {
                "event_type": "ErrorRecorded",
                "scope": "worker",
                "message": "bad scope",
            }
        )


def test_event_envelope_preserves_created_at() -> None:
    created_at = datetime(2026, 4, 16, tzinfo=UTC)
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=5,
        created_at=created_at,
        payload=UserMessageReceived(
            message_id=new_message_id(),
            text="hello",
        ),
    )

    assert envelope.created_at == created_at


def test_transcript_message_imported_round_trip() -> None:
    payload = TranscriptMessageImported(
        message_id=new_message_id(),
        source_session_id=new_session_id(),
        source_message_id=new_message_id(),
        source_turn_id=new_turn_id(),
        role="assistant",
        parts=[MessagePart(kind="text", text="imported answer")],
        source_created_at=datetime(2026, 4, 16, 12, 4, tzinfo=UTC),
    )
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=6,
        payload=payload,
    )

    restored = EventEnvelope.model_validate(envelope.model_dump(mode="python"))

    assert restored == envelope
    assert restored.message_id == payload.message_id


def test_task_plan_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    step_id = new_task_step_id()
    verification_id = new_task_verification_id()

    created = adapter.validate_python(
        {
            "event_type": "TaskCreated",
            "task_id": task_id,
            "title": "Implement task models",
            "goal": "Persist durable task-plan payloads",
            "source_turn_id": new_turn_id(),
        }
    )
    proposed = adapter.validate_python(
        {
            "event_type": "TaskPlanProposed",
            "task_id": task_id,
            "plan": {
                "task_id": task_id,
                "title": "Implement task models",
                "goal": "Persist durable task-plan payloads",
                "steps": [
                    {
                        "step_id": step_id,
                        "title": "Add core events",
                        "order": 0,
                    }
                ],
            },
        }
    )
    step_started = adapter.validate_python(
        {
            "event_type": "TaskStepStarted",
            "task_id": task_id,
            "step_id": step_id,
            "turn_id": new_turn_id(),
        }
    )
    step_completed = adapter.validate_python(
        {
            "event_type": "TaskStepCompleted",
            "task_id": task_id,
            "step_id": step_id,
            "summary": "Core events added",
        }
    )
    verification_started = adapter.validate_python(
        {
            "event_type": "TaskVerificationStarted",
            "task_id": task_id,
            "verification_id": verification_id,
            "step_id": step_id,
            "check_name": "pytest",
        }
    )
    verification_completed = adapter.validate_python(
        {
            "event_type": "TaskVerificationCompleted",
            "task_id": task_id,
            "verification_id": verification_id,
            "status": "passed",
            "summary": "Focused tests passed",
        }
    )

    assert isinstance(created, TaskCreated)
    assert isinstance(proposed, TaskPlanProposed)
    assert proposed.plan.steps[0].step_id == step_id
    assert isinstance(step_started, TaskStepStarted)
    assert isinstance(step_completed, TaskStepCompleted)
    assert isinstance(verification_started, TaskVerificationStarted)
    assert isinstance(verification_completed, TaskVerificationCompleted)


def test_task_plan_event_envelope_exposes_task_id() -> None:
    task_id = new_task_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=7,
        payload=TaskPaused(task_id=task_id, reason=TaskBlockedReason.MANUAL_PAUSE),
    )

    assert envelope.task_id == task_id


def test_task_plan_proposal_rejects_mismatched_task_id() -> None:
    with pytest.raises(ValidationError):
        TaskPlanProposed(
            task_id=new_task_id(),
            plan=TaskPlanSnapshot(
                task_id=new_task_id(),
                title="Mismatch",
                goal="Should be rejected",
                steps=[],
            ),
        )


def test_task_step_failure_rejects_unknown_blocked_reason() -> None:
    with pytest.raises(ValidationError):
        TaskStepFailed.model_validate(
            {
                "event_type": "TaskStepFailed",
                "task_id": new_task_id(),
                "step_id": new_task_step_id(),
                "reason": "blocked",
                "blocked_reason": "approval_queue",
            }
        )
