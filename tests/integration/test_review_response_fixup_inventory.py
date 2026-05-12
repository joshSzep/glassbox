"""Integration tests for response-linked review feedback inventory evidence."""

import asyncio
import subprocess
from pathlib import Path
from typing import cast

from glassbox.core import EventEnvelope
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStatusChanged
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ReviewFeedbackActionService
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryService
from glassbox.store import SQLiteSessionRepository


def test_fixup_inventory_links_feedback_paths_and_detects_drift(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    _init_git_repo(tmp_path)

    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        assert isinstance(repository, SQLiteSessionRepository)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCreated(
                        task_id=task_id,
                        title="Respond to review feedback",
                        goal="Attach fixup inventory evidence",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskStatusChanged(
                        task_id=task_id,
                        status=TaskPlanStatus.COMPLETED,
                    ),
                ),
            ]
        )
        changeset_repository = runtime_context.repositories.sessions
        changeset_repository = cast(ChangesetRepository, changeset_repository)
        changeset_id = (
            ChangesetDerivationService(
                changeset_repository,
            )
            .create_from_task(task_id)
            .changeset_id
        )
        (tmp_path / "app.py").write_text("print('changed')\n", encoding="utf-8")
        inventory_result = asyncio.run(
            ChangesetActionService(
                changeset_repository,
                runtime_context.repositories.artifacts,
            ).refresh_inventory(
                changeset_id,
                tmp_path,
            )
        )
        feedback = (
            ReviewFeedbackActionService(changeset_repository)
            .add_feedback(
                changeset_id,
                feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
                provenance=ReviewFeedbackProvenance.REVIEWER,
                summary="Please add response-linked inventory.",
                file_path="app.py",
            )
            .feedback
        )
        verification_id = new_task_verification_id()
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=VerificationPlanEntry(
                            verification_id=verification_id,
                            check_name="focused app verification",
                            kind=VerificationCheckKind.COMMAND,
                            command=["uv", "run", "pytest", "tests/test_app.py"],
                            source=VerificationPlanSource.EVAL_RECOMMENDATION,
                            rationale="operator ran focused app verification",
                            changed_paths=[Path("app.py")],
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=verification_id,
                        status=TaskVerificationStatus.PASSED,
                        summary="focused app verification passed before fixup",
                    ),
                ),
            ]
        )
        (tmp_path / "app.py").write_text(
            "print('changed after feedback')\n",
            encoding="utf-8",
        )
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text(
            "def test_app():\n    assert True\n",
            encoding="utf-8",
        )

        fixup_service = ReviewFeedbackFixupInventoryService(
            changeset_repository,
            runtime_context.repositories.artifacts,
        )
        result = asyncio.run(
            fixup_service.record_workspace_inventory(
                feedback.feedback_id,
                tmp_path,
                source_summary=(
                    "operator says this inventory responds to review feedback"
                ),
            )
        )
        query = ChangesetQueryService(changeset_repository)
        inventories = query.list_review_feedback_fixup_inventories(
            session_id,
            feedback.feedback_id,
        )
        paths = query.list_review_feedback_fixup_paths(
            session_id,
            feedback.feedback_id,
            result.artifact.artifact_id,
        )
        fresh_summary = query.get_review_response_summary(
            changeset_id,
            workspace_root=tmp_path,
        )
        (tmp_path / "app.py").write_text(
            "print('drift after response')\n",
            encoding="utf-8",
        )
        stale_status = fixup_service.assess_record_freshness(inventories[0], tmp_path)
        stale_summary = query.get_review_response_summary(
            changeset_id,
            workspace_root=tmp_path,
        )

    assert result.inventory.latest_changeset_inventory_artifact_id == str(
        inventory_result.artifact.artifact_id
    )
    assert result.status.stale is False
    assert result.artifact.absolute_path.exists()
    assert inventories[0].artifact_id == result.artifact.artifact_id
    assert inventories[0].changed_path_count == 2
    assert inventories[0].matched_scope_path_count == 1
    assert {path.path for path in paths} == {"app.py", "tests/test_app.py"}
    assert any(path.matches_feedback_scope for path in paths if path.path == "app.py")
    assert any(path.test_file for path in paths if path.path == "tests/test_app.py")
    assert fresh_summary.responded_count == 0
    assert fresh_summary.stale_response_count == 1
    assert fresh_summary.blocked_count == 1
    assert fresh_summary.items[0].response_state.value == "blocked"
    assert fresh_summary.items[0].verification_state.value == "stale"
    assert "passed before response-linked fixup" in (
        fresh_summary.items[0].verification_reason or ""
    )
    assert fresh_summary.items[0].stale_plan_entry_count == 1
    assert fresh_summary.items[0].newly_required_check_count == 0
    assert fresh_summary.items[0].verification_plan_entries[0].relationship == "stale"
    assert (
        fresh_summary.items[0].verification_plan_entries[0].verification_id
        == verification_id
    )
    assert (
        "rerun uv run pytest"
        in (fresh_summary.items[0].verification_safe_next_actions[0])
    )
    assert fresh_summary.items[0].path_summaries[0].startswith("app.py:")
    assert stale_status.stale is True
    assert "source digest changed" in (stale_status.reason or "")
    assert stale_summary.stale_response_count == 1
    assert stale_summary.blocked_count == 1
    assert stale_summary.items[0].response_state.value == "blocked"


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "app.py").write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
