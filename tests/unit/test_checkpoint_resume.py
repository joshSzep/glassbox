"""Tests for checkpoint-derived resume posture."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import TaskCheckpointRecord
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core.types import LongRunPhase
from glassbox.runtime.checkpoints import build_checkpoint_resume_snapshot


def _checkpoint(
    *,
    workspace_root: Path,
    touched_files: list[str] | None = None,
    blockers: list[str] | None = None,
    current_phase: LongRunPhase | None = LongRunPhase.CHECKPOINTING,
    last_sequence: int = 5,
) -> TaskCheckpointRecord:
    session_id = new_session_id()
    if touched_files is None:
        touched_files = ["README.md"]
        (workspace_root / "README.md").write_text("hello\n", encoding="utf-8")
    return TaskCheckpointRecord(
        checkpoint_id=new_task_checkpoint_id(),
        session_id=session_id,
        objective="Finish the long task",
        current_phase=current_phase,
        completed_step="Wrote checkpoint model",
        next_action="Resume from checkpoint",
        recovery_guidance="Inspect checkpoint and continue",
        blockers=list(blockers or []),
        touched_files=touched_files,
        source_start_sequence=1,
        source_end_sequence=4,
        created_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        last_sequence=last_sequence,
    )


def test_checkpoint_resume_snapshot_marks_current_checkpoint_usable(
    tmp_path: Path,
) -> None:
    snapshot = build_checkpoint_resume_snapshot(
        _checkpoint(workspace_root=tmp_path),
        latest_session_sequence=5,
        workspace_root=tmp_path,
    )

    assert snapshot is not None
    assert snapshot.status == "usable"
    assert snapshot.safe_to_use is True
    assert snapshot.context_source == "checkpoint"
    assert snapshot.workspace_drift_paths == []


def test_checkpoint_resume_snapshot_rejects_stale_checkpoint(
    tmp_path: Path,
) -> None:
    snapshot = build_checkpoint_resume_snapshot(
        _checkpoint(workspace_root=tmp_path, last_sequence=5),
        latest_session_sequence=8,
        workspace_root=tmp_path,
    )

    assert snapshot is not None
    assert snapshot.status == "stale"
    assert snapshot.safe_to_use is False
    assert snapshot.context_source == "replay"
    assert "events were recorded after the latest checkpoint" in snapshot.reason


def test_checkpoint_resume_snapshot_rejects_blocked_checkpoint(
    tmp_path: Path,
) -> None:
    snapshot = build_checkpoint_resume_snapshot(
        _checkpoint(workspace_root=tmp_path, blockers=["approval required"]),
        latest_session_sequence=5,
        workspace_root=tmp_path,
    )

    assert snapshot is not None
    assert snapshot.status == "blocked"
    assert snapshot.safe_to_use is False
    assert snapshot.context_source == "replay"
    assert "unresolved blockers" in snapshot.reason


def test_checkpoint_resume_snapshot_rejects_workspace_drift(
    tmp_path: Path,
) -> None:
    snapshot = build_checkpoint_resume_snapshot(
        _checkpoint(workspace_root=tmp_path, touched_files=["missing.py"]),
        latest_session_sequence=5,
        workspace_root=tmp_path,
    )

    assert snapshot is not None
    assert snapshot.status == "workspace_drift"
    assert snapshot.safe_to_use is False
    assert snapshot.workspace_drift_paths == ["missing.py"]


def test_checkpoint_resume_snapshot_rejects_failed_phase(
    tmp_path: Path,
) -> None:
    snapshot = build_checkpoint_resume_snapshot(
        _checkpoint(workspace_root=tmp_path, current_phase=LongRunPhase.FAILED),
        latest_session_sequence=5,
        workspace_root=tmp_path,
    )

    assert snapshot is not None
    assert snapshot.status == "non_resumable"
    assert snapshot.safe_to_use is False
    assert snapshot.context_source == "replay"
