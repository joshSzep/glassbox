"""Focused redaction coverage for portable session export helpers."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_task_checkpoint_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import LongRunPhase
from glassbox.runtime.session_export_redaction import REDACTION_PLACEHOLDER
from glassbox.runtime.session_export_redaction import WORKSPACE_PLACEHOLDER
from glassbox.runtime.session_export_redaction import RedactionContext
from glassbox.runtime.session_export_redaction import portable_artifact_path
from glassbox.runtime.session_export_redaction import redact_checkpoints
from glassbox.runtime.session_export_redaction import redact_json_value
from glassbox.runtime.session_export_redaction import redact_pending_approvals
from glassbox.runtime.session_export_redaction import redact_text


def test_session_export_redacts_workspace_paths_and_secret_like_tokens(
    tmp_path: Path,
) -> None:
    context = RedactionContext(workspace_root=tmp_path.resolve())

    redacted = redact_text(
        f"Run in {tmp_path}/app with OPENAI_API_KEY=sk-test-secret-value",
        context,
    )

    assert str(tmp_path) not in redacted
    assert WORKSPACE_PLACEHOLDER in redacted
    assert "sk-test-secret-value" not in redacted
    assert f"OPENAI_API_KEY={REDACTION_PLACEHOLDER}" in redacted


def test_session_export_redacts_nested_json_values(tmp_path: Path) -> None:
    context = RedactionContext(workspace_root=tmp_path.resolve())

    redacted = redact_json_value(
        {
            "cwd": str(tmp_path),
            "steps": ["inspect", f"ANTHROPIC_API_KEY=secret-{tmp_path.name}"],
            "safe": 42,
        },
        context,
    )

    assert redacted == {
        "cwd": WORKSPACE_PLACEHOLDER,
        "steps": ["inspect", f"ANTHROPIC_API_KEY={REDACTION_PLACEHOLDER}"],
        "safe": 42,
    }


def test_session_export_rejects_parent_relative_artifact_paths(
    tmp_path: Path,
) -> None:
    context = RedactionContext(workspace_root=tmp_path.resolve())

    assert portable_artifact_path("../outside.txt", context) == REDACTION_PLACEHOLDER
    assert portable_artifact_path("artifacts/output.txt", context) == (
        "artifacts/output.txt"
    )
    assert portable_artifact_path(str(tmp_path / "artifact.txt"), context) == (
        f"{WORKSPACE_PLACEHOLDER}/artifact.txt"
    )


def test_session_export_redacts_approval_and_checkpoint_records(
    tmp_path: Path,
) -> None:
    context = RedactionContext(workspace_root=tmp_path.resolve())
    now = datetime(2026, 5, 1, 12, tzinfo=UTC)

    approvals = redact_pending_approvals(
        [
            ApprovalRecord(
                approval_id=new_approval_id(),
                turn_id=new_turn_id(),
                subject=f"run {tmp_path}/script.sh",
                reason="needs OPENAI_API_KEY=sk-approval-secret",
                policy_source_label=f"policy from {tmp_path}",
                status=ApprovalStatus.PENDING,
                requested_at=now,
            )
        ],
        context,
    )
    checkpoints = redact_checkpoints(
        [
            TaskCheckpointRecord(
                checkpoint_id=new_task_checkpoint_id(),
                session_id=uuid4(),
                objective=f"Review {tmp_path}",
                current_phase=LongRunPhase.CHECKPOINTING,
                completed_step=f"Checked {tmp_path}/README.md",
                next_action="Continue with ANTHROPIC_API_KEY=secret-value",
                touched_files=[str(tmp_path / "README.md")],
                recovery_guidance=f"Resume inside {tmp_path}",
                source_start_sequence=1,
                source_end_sequence=2,
                created_at=now,
                last_sequence=2,
            )
        ],
        context,
    )

    assert approvals[0].subject == f"run {WORKSPACE_PLACEHOLDER}/script.sh"
    assert approvals[0].reason == f"needs OPENAI_API_KEY={REDACTION_PLACEHOLDER}"
    assert approvals[0].policy_source_label == f"policy from {WORKSPACE_PLACEHOLDER}"
    assert checkpoints[0].objective == f"Review {WORKSPACE_PLACEHOLDER}"
    assert checkpoints[0].completed_step == f"Checked {WORKSPACE_PLACEHOLDER}/README.md"
    assert checkpoints[0].next_action == (
        f"Continue with ANTHROPIC_API_KEY={REDACTION_PLACEHOLDER}"
    )
    assert checkpoints[0].touched_files == [f"{WORKSPACE_PLACEHOLDER}/README.md"]
