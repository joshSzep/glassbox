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
from glassbox.core import ChangesetArchived
from glassbox.core import ChangesetCandidateAdopted
from glassbox.core import ChangesetCreated
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRefreshed
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import ChangesetVerificationState
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
from glassbox.core import ManualEvidenceArchived
from glassbox.core import ManualEvidenceAttached
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceRejected
from glassbox.core import ManualEvidenceSuperseded
from glassbox.core import ManualEvidenceTargetKind
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
from glassbox.core import ReviewFeedbackArchived
from glassbox.core import ReviewFeedbackCreated
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackDispositionUpdated
from glassbox.core import ReviewFeedbackFixupInventoryAttached
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackReopened
from glassbox.core import ReviewFeedbackResolved
from glassbox.core import ReviewFeedbackRiskAccepted
from glassbox.core import ReviewFeedbackScopeAttached
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import ReviewFixupSourceKind
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
from glassbox.core import WorktreeCleanupRecorded
from glassbox.core import WorktreeCreated
from glassbox.core import WorktreeSourceKind
from glassbox.core import WorktreeState
from glassbox.core import WorktreeStatusRecorded
from glassbox.core import new_approval_id
from glassbox.core import new_artifact_id
from glassbox.core import new_background_job_id
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_changeset_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_manual_evidence_id
from glassbox.core import new_message_id
from glassbox.core import new_pause_window_id
from glassbox.core import new_recovery_decision_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id
from glassbox.core import new_worktree_id


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


def test_worktree_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    worktree_id = new_worktree_id()
    changeset_id = new_changeset_id()

    created = adapter.validate_python(
        {
            "event_type": "WorktreeCreated",
            "worktree_id": worktree_id,
            "path": "/tmp/repo/.glassbox/worktrees/wt",
            "branch_name": "glassbox/worktree/wt",
            "base_revision": "abc123",
            "source_kind": "changeset",
            "source_id": str(changeset_id),
            "changeset_id": changeset_id,
            "owner_process": "pid:123",
            "state": "active",
            "created_by": "operator",
        }
    )
    status = adapter.validate_python(
        {
            "event_type": "WorktreeStatusRecorded",
            "worktree_id": worktree_id,
            "state": "dirty",
            "path_exists": True,
            "dirty": True,
            "current_branch": "glassbox/worktree/wt",
            "head_revision": "abc123",
            "git_status_short": [" M app.py"],
            "safe_next_actions": ["git worktree list --porcelain"],
        }
    )
    cleanup = adapter.validate_python(
        {
            "event_type": "WorktreeCleanupRecorded",
            "worktree_id": worktree_id,
            "state": "cleanup_blocked",
            "path": "/tmp/repo/.glassbox/worktrees/wt",
            "confirmed_by": "operator",
            "dirty": True,
            "removed": False,
            "reason": "cleanup blocked because the worktree has local changes",
        }
    )

    assert isinstance(created, WorktreeCreated)
    assert isinstance(status, WorktreeStatusRecorded)
    assert isinstance(cleanup, WorktreeCleanupRecorded)
    assert created.source_kind == WorktreeSourceKind.CHANGESET
    assert status.state == WorktreeState.DIRTY


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


def test_changeset_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    changeset_id = new_changeset_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    source_session_id = new_session_id()
    branch_search_id = new_branch_search_id()
    branch_candidate_id = new_branch_candidate_id()
    verification_id = new_task_verification_id()
    inventory_artifact_id = new_artifact_id()
    brief_artifact_id = new_artifact_id()

    created = adapter.validate_python(
        {
            "event_type": "ChangesetCreated",
            "changeset_id": changeset_id,
            "objective": "Review local changes",
            "task_id": task_id,
            "turn_id": turn_id,
            "branch_search_id": branch_search_id,
            "branch_candidate_id": branch_candidate_id,
        }
    )
    source = adapter.validate_python(
        {
            "event_type": "ChangesetSourceAttached",
            "changeset_id": changeset_id,
            "source_kind": "branch_search_candidate",
            "source_session_id": source_session_id,
            "task_id": task_id,
            "turn_id": turn_id,
            "branch_search_id": branch_search_id,
            "branch_candidate_id": branch_candidate_id,
            "verification_id": verification_id,
            "artifact_id": inventory_artifact_id,
            "reason": "candidate selected after review",
            "limitation": "candidate diff inventory is degraded",
        }
    )
    inventory = adapter.validate_python(
        {
            "event_type": "ChangesetInventoryRefreshed",
            "changeset_id": changeset_id,
            "artifact_id": inventory_artifact_id,
            "freshness": "fresh",
            "changed_path_count": 4,
            "source_digest": "sha256:inventory",
            "task_id": task_id,
            "turn_id": turn_id,
            "branch_search_id": branch_search_id,
            "branch_candidate_id": branch_candidate_id,
        }
    )
    verification = adapter.validate_python(
        {
            "event_type": "ChangesetVerificationPostureUpdated",
            "changeset_id": changeset_id,
            "state": "stale",
            "summary": "unit tests passed before inventory refresh",
            "verification_id": verification_id,
            "artifact_id": new_artifact_id(),
            "task_id": task_id,
            "turn_id": turn_id,
            "stale_count": 1,
        }
    )
    brief = adapter.validate_python(
        {
            "event_type": "ChangesetReviewBriefCreated",
            "changeset_id": changeset_id,
            "artifact_id": brief_artifact_id,
            "render_targets": ["markdown", "json"],
            "inventory_artifact_id": inventory_artifact_id,
            "verification_id": verification_id,
            "redacted": True,
        }
    )
    readiness = adapter.validate_python(
        {
            "event_type": "ChangesetReadinessDecided",
            "changeset_id": changeset_id,
            "readiness_kind": "commit",
            "state": "needs_verification",
            "reason": "verification evidence is stale",
            "blockers": ["stale verification"],
            "safe_next_actions": ["refresh inventory", "rerun focused tests"],
            "inventory_artifact_id": inventory_artifact_id,
            "review_brief_artifact_id": brief_artifact_id,
            "verification_id": verification_id,
            "accepted_risk_count": 1,
        }
    )
    adoption = adapter.validate_python(
        {
            "event_type": "ChangesetCandidateAdopted",
            "changeset_id": changeset_id,
            "branch_search_id": branch_search_id,
            "branch_candidate_id": branch_candidate_id,
            "candidate_session_id": source_session_id,
            "preview_artifact_id": new_artifact_id(),
            "inventory_artifact_id": inventory_artifact_id,
            "verification_id": verification_id,
            "reason": "selected low-risk candidate",
            "workspace_mutation_performed": False,
        }
    )
    archived = adapter.validate_python(
        {
            "event_type": "ChangesetArchived",
            "changeset_id": changeset_id,
            "reason": "superseded by a refreshed changeset",
            "replacement_changeset_id": new_changeset_id(),
        }
    )

    assert isinstance(created, ChangesetCreated)
    assert created.changeset_id == changeset_id
    assert isinstance(source, ChangesetSourceAttached)
    assert source.source_kind == ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE
    assert source.source_session_id == source_session_id
    assert isinstance(inventory, ChangesetInventoryRefreshed)
    assert inventory.freshness == ChangesetInventoryFreshness.FRESH
    assert inventory.changed_path_count == 4
    assert isinstance(verification, ChangesetVerificationPostureUpdated)
    assert verification.state == ChangesetVerificationState.STALE
    assert verification.stale_count == 1
    assert isinstance(brief, ChangesetReviewBriefCreated)
    assert brief.render_targets == ["markdown", "json"]
    assert brief.redacted is True
    assert isinstance(readiness, ChangesetReadinessDecided)
    assert readiness.readiness_kind == ChangesetReadinessKind.COMMIT
    assert readiness.state == ChangesetReadinessState.NEEDS_VERIFICATION
    assert isinstance(adoption, ChangesetCandidateAdopted)
    assert adoption.workspace_mutation_performed is False
    assert isinstance(archived, ChangesetArchived)
    assert archived.changeset_id == changeset_id


def test_changeset_envelope_exposes_correlation_ids() -> None:
    changeset_id = new_changeset_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=24,
        payload=ChangesetVerificationPostureUpdated(
            changeset_id=changeset_id,
            state=ChangesetVerificationState.FAILED,
            summary="focused tests failed",
            verification_id=verification_id,
            artifact_id=artifact_id,
            task_id=task_id,
            turn_id=turn_id,
            failed_count=1,
        ),
    )

    assert envelope.event_type == "ChangesetVerificationPostureUpdated"
    assert envelope.changeset_id == changeset_id
    assert envelope.artifact_id == artifact_id
    assert envelope.verification_id == verification_id
    assert envelope.task_id == task_id
    assert envelope.turn_id == turn_id


def test_review_feedback_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    feedback_id = new_review_feedback_id()
    changeset_id = new_changeset_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    source_session_id = new_session_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    branch_search_id = new_branch_search_id()
    branch_candidate_id = new_branch_candidate_id()

    created = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackCreated",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "feedback_kind": "requested_change",
            "provenance": "reviewer",
            "summary": "Add regression coverage for stale verification.",
            "body": "The change updates runtime behavior without a focused test.",
            "source_label": "local-review-pass",
            "reviewer_label": "reviewer-a",
            "source_session_id": source_session_id,
            "task_id": task_id,
            "turn_id": turn_id,
            "artifact_id": artifact_id,
            "verification_id": verification_id,
        }
    )
    scope = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackScopeAttached",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "scope_kind": "file",
            "reason": "comment points at the changed readiness code",
            "file_path": "src/glassbox/runtime/changeset_verification_readiness.py",
            "line_start": 40,
            "line_end": 45,
            "source_session_id": source_session_id,
            "task_id": task_id,
            "turn_id": turn_id,
            "artifact_id": artifact_id,
            "verification_id": verification_id,
            "branch_search_id": branch_search_id,
            "branch_candidate_id": branch_candidate_id,
        }
    )
    disposition = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackDispositionUpdated",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "disposition": "responded",
            "reason": "fixup response artifact was attached",
            "task_id": task_id,
            "turn_id": turn_id,
            "artifact_id": artifact_id,
            "verification_id": verification_id,
        }
    )
    resolved = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackResolved",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "resolution_summary": "Added the stale verification unit test.",
            "task_id": task_id,
            "turn_id": turn_id,
            "artifact_id": artifact_id,
            "verification_id": verification_id,
        }
    )
    reopened = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackReopened",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "reason": "new fixup made the verification evidence stale again",
            "task_id": task_id,
        }
    )
    accepted = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackRiskAccepted",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "risk_summary": "Browser evidence is advisory only.",
            "acceptance_reason": "Deterministic tests cover the blocking claim.",
            "verification_id": verification_id,
        }
    )
    fixup_inventory = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackFixupInventoryAttached",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "artifact_id": artifact_id,
            "artifact_schema_version": 1,
            "source_kind": "manual_workspace_edit",
            "source_summary": "operator recorded response-linked workspace edits",
            "source_digest": "sha256:abc",
            "inventory_freshness": "fresh",
            "changed_path_count": 1,
            "matched_scope_path_count": 1,
            "paths": [
                {
                    "path": "src/glassbox/runtime/changesets.py",
                    "change_kind": "modified",
                    "generated": False,
                    "test_file": False,
                    "docs_file": False,
                    "policy_sensitive": False,
                    "risk_level": "high",
                    "provenance_confidence": "unknown",
                    "matches_feedback_scope": True,
                    "summary": (
                        "src/glassbox/runtime/changesets.py: matches feedback "
                        "scope, high risk"
                    ),
                }
            ],
            "task_id": task_id,
            "turn_id": turn_id,
            "verification_id": verification_id,
        }
    )
    archived = adapter.validate_python(
        {
            "event_type": "ReviewFeedbackArchived",
            "feedback_id": feedback_id,
            "changeset_id": changeset_id,
            "reason": "superseded by a narrower feedback record",
            "replacement_feedback_id": new_review_feedback_id(),
        }
    )

    assert isinstance(created, ReviewFeedbackCreated)
    assert created.feedback_kind == ReviewFeedbackKind.REQUESTED_CHANGE
    assert created.provenance == ReviewFeedbackProvenance.REVIEWER
    assert created.source_session_id == source_session_id
    assert isinstance(scope, ReviewFeedbackScopeAttached)
    assert scope.scope_kind == ReviewFeedbackScopeKind.FILE
    assert scope.file_path == "src/glassbox/runtime/changeset_verification_readiness.py"
    assert scope.line_start == 40
    assert scope.line_end == 45
    assert isinstance(disposition, ReviewFeedbackDispositionUpdated)
    assert disposition.disposition == ReviewFeedbackDisposition.RESPONDED
    assert isinstance(resolved, ReviewFeedbackResolved)
    assert resolved.resolution_summary.startswith("Added")
    assert isinstance(reopened, ReviewFeedbackReopened)
    assert reopened.feedback_id == feedback_id
    assert isinstance(accepted, ReviewFeedbackRiskAccepted)
    assert accepted.verification_id == verification_id
    assert isinstance(fixup_inventory, ReviewFeedbackFixupInventoryAttached)
    assert fixup_inventory.source_kind == ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT
    assert fixup_inventory.paths[0].matches_feedback_scope is True
    assert isinstance(archived, ReviewFeedbackArchived)
    assert archived.changeset_id == changeset_id


def test_review_feedback_scope_rejects_invalid_file_ranges() -> None:
    with pytest.raises(ValidationError):
        ReviewFeedbackScopeAttached(
            feedback_id=new_review_feedback_id(),
            changeset_id=new_changeset_id(),
            scope_kind=ReviewFeedbackScopeKind.FILE,
            reason="line range is inverted",
            file_path="src/glassbox/runtime/changesets.py",
            line_start=12,
            line_end=10,
        )

    with pytest.raises(ValidationError):
        ReviewFeedbackScopeAttached(
            feedback_id=new_review_feedback_id(),
            changeset_id=new_changeset_id(),
            scope_kind=ReviewFeedbackScopeKind.FILE,
            reason="file scopes need path metadata",
        )


def test_review_feedback_envelope_exposes_correlation_ids() -> None:
    feedback_id = new_review_feedback_id()
    changeset_id = new_changeset_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=25,
        payload=ReviewFeedbackResolved(
            feedback_id=feedback_id,
            changeset_id=changeset_id,
            resolution_summary="Recorded fixup response and focused verification.",
            artifact_id=artifact_id,
            verification_id=verification_id,
            task_id=task_id,
            turn_id=turn_id,
        ),
    )

    assert envelope.event_type == "ReviewFeedbackResolved"
    assert envelope.feedback_id == feedback_id
    assert envelope.changeset_id == changeset_id
    assert envelope.artifact_id == artifact_id
    assert envelope.verification_id == verification_id
    assert envelope.task_id == task_id
    assert envelope.turn_id == turn_id


def test_manual_evidence_payloads_round_trip_through_event_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    evidence_id = new_manual_evidence_id()
    replacement_id = new_manual_evidence_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    observed_at = datetime.now(UTC)

    attached = adapter.validate_python(
        {
            "event_type": "ManualEvidenceAttached",
            "evidence_id": evidence_id,
            "evidence_kind": "manual_command",
            "target_kind": "feedback",
            "target_id": str(feedback_id),
            "changeset_id": changeset_id,
            "feedback_id": feedback_id,
            "artifact_id": artifact_id,
            "artifact_schema_version": 1,
            "summary": "operator says local pytest passed outside Glassbox",
            "source_label": "operator shell",
            "observed_at": observed_at,
            "redaction_status": "passed",
            "freshness": "current",
            "verification_id": verification_id,
            "limitations": ["manual summary only"],
            "non_claims": ["not retained command evidence"],
        }
    )
    rejected = adapter.validate_python(
        {
            "event_type": "ManualEvidenceRejected",
            "evidence_id": new_manual_evidence_id(),
            "evidence_kind": "sanitized_log",
            "summary": "raw log rejected before retention",
            "reason": "secret-looking assignment detected",
            "redaction_findings": ["secret-looking-value"],
        }
    )
    superseded = adapter.validate_python(
        {
            "event_type": "ManualEvidenceSuperseded",
            "evidence_id": evidence_id,
            "replacement_evidence_id": replacement_id,
            "reason": "newer bounded summary replaced this note",
        }
    )
    archived = adapter.validate_python(
        {
            "event_type": "ManualEvidenceArchived",
            "evidence_id": replacement_id,
            "reason": "local-only reference no longer applies",
        }
    )

    assert isinstance(attached, ManualEvidenceAttached)
    assert attached.evidence_kind == ManualEvidenceKind.MANUAL_COMMAND
    assert attached.target_kind == ManualEvidenceTargetKind.FEEDBACK
    assert attached.redaction_status == ManualEvidenceRedactionStatus.PASSED
    assert attached.freshness == ManualEvidenceFreshness.CURRENT
    assert isinstance(rejected, ManualEvidenceRejected)
    assert rejected.redaction_status == ManualEvidenceRedactionStatus.REJECTED
    assert isinstance(superseded, ManualEvidenceSuperseded)
    assert superseded.replacement_evidence_id == replacement_id
    assert isinstance(archived, ManualEvidenceArchived)


def test_manual_evidence_envelope_exposes_correlation_ids() -> None:
    evidence_id = new_manual_evidence_id()
    changeset_id = new_changeset_id()
    artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
    envelope = EventEnvelope(
        session_id=new_session_id(),
        sequence=31,
        payload=ManualEvidenceAttached(
            evidence_id=evidence_id,
            evidence_kind=ManualEvidenceKind.EXTERNAL_CHECK,
            target_kind=ManualEvidenceTargetKind.CHANGESET,
            target_id=str(changeset_id),
            changeset_id=changeset_id,
            summary="external CI reported green on the operator's branch",
            source_label="external-ci",
            artifact_id=artifact_id,
            artifact_schema_version=1,
            redaction_status=ManualEvidenceRedactionStatus.PASSED,
            verification_id=verification_id,
        ),
    )

    assert envelope.event_type == "ManualEvidenceAttached"
    assert envelope.evidence_id == evidence_id
    assert envelope.changeset_id == changeset_id
    assert envelope.artifact_id == artifact_id
    assert envelope.verification_id == verification_id


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
