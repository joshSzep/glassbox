"""Checkpoint resume posture helpers for long-running work."""

from pathlib import Path

from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.types import LongRunPhase
from glassbox.runtime.context_models import CheckpointResumeSnapshot


def build_checkpoint_resume_snapshot(
    checkpoint: TaskCheckpointRecord | None,
    *,
    latest_session_sequence: int,
    workspace_root: Path,
) -> CheckpointResumeSnapshot | None:
    """Classify whether a checkpoint can safely guide resumed work."""

    if checkpoint is None:
        return None

    drift_paths = _missing_touched_files(checkpoint, workspace_root)
    if checkpoint.current_phase == LongRunPhase.FAILED:
        status = "non_resumable"
        safe_to_use = False
        context_source = "replay"
        reason = (
            "latest checkpoint is in failed phase; replay-derived transcript and "
            "recovery evidence are authoritative"
        )
        limitations = [
            "checkpoint recovery guidance may explain the failure but should not "
            "be treated as an active continuation point"
        ]
    elif checkpoint.last_sequence < latest_session_sequence:
        status = "stale"
        safe_to_use = False
        context_source = "replay"
        reason = (
            "events were recorded after the latest checkpoint; replay-derived "
            "context is authoritative until a fresh checkpoint is created"
        )
        limitations = [
            "checkpoint source range does not include the latest session events"
        ]
    elif drift_paths:
        status = "workspace_drift"
        safe_to_use = False
        context_source = "replay"
        reason = (
            "checkpoint touched files no longer match the workspace; inspect "
            "workspace drift before trusting checkpoint continuation"
        )
        limitations = [
            "one or more checkpoint touched files are missing from the workspace"
        ]
    elif checkpoint.blockers:
        status = "blocked"
        safe_to_use = False
        context_source = "replay"
        reason = (
            "latest checkpoint records unresolved blockers; operator action is "
            "required before checkpoint-derived continuation is safe"
        )
        limitations = [
            "checkpoint is retained as handoff evidence but blocked for active "
            "resume context"
        ]
    else:
        status = "usable"
        safe_to_use = True
        context_source = "checkpoint"
        reason = (
            "latest checkpoint covers the current session tail and has no known "
            "resume blockers"
        )
        limitations = []

    return CheckpointResumeSnapshot(
        checkpoint_id=checkpoint.checkpoint_id,
        task_id=checkpoint.task_id,
        turn_id=checkpoint.turn_id,
        objective=checkpoint.objective,
        current_phase=checkpoint.current_phase,
        completed_step=checkpoint.completed_step,
        next_action=checkpoint.next_action,
        blockers=list(checkpoint.blockers),
        touched_files=list(checkpoint.touched_files),
        verification_status=checkpoint.verification_status,
        budget_status=checkpoint.budget_status,
        recovery_guidance=checkpoint.recovery_guidance,
        source_start_sequence=checkpoint.source_start_sequence,
        source_end_sequence=checkpoint.source_end_sequence,
        checkpoint_sequence=checkpoint.last_sequence,
        latest_session_sequence=latest_session_sequence,
        status=status,
        safe_to_use=safe_to_use,
        context_source=context_source,
        reason=reason,
        limitations=limitations,
        workspace_drift_paths=drift_paths,
    )


def _missing_touched_files(
    checkpoint: TaskCheckpointRecord,
    workspace_root: Path,
) -> list[str]:
    root = workspace_root.resolve()
    missing: list[str] = []
    for raw_path in checkpoint.touched_files:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            missing.append(raw_path)
            continue
        try:
            resolved = (root / candidate).resolve()
            resolved.relative_to(root)
        except ValueError:
            missing.append(raw_path)
            continue
        if not resolved.exists():
            missing.append(raw_path)
    return missing


__all__ = ["build_checkpoint_resume_snapshot"]
