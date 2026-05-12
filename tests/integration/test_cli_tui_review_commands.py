"""Integration coverage for TUI review-loop command client actions."""

import asyncio
import subprocess
from pathlib import Path
from typing import cast
from uuid import UUID

from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.core import ChangesetSourceKind
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import SessionConfig
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ReviewFeedbackActionService
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def test_local_tui_review_create_defaults_to_current_session_workspace_diff(
    tmp_path: Path,
) -> None:
    asyncio.run(_run_local_tui_review_create_test(tmp_path))


async def _run_local_tui_review_create_test(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    try:
        runtime_context = _build_runtime_context(connection, tmp_path)
        state = await runtime_context.services.session_service.start_session(
            SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
        )
        client = LocalInteractiveSessionClient(
            runtime_context=runtime_context,
            session_id=state.session_id,
            dashboard_url="http://127.0.0.1:8765/",
        )

        result = await client.create_review_changeset(
            objective="Review current terminal UX work"
        )
        assert result.changeset_id is not None
        feedback = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).add_feedback(
            UUID(result.changeset_id),
            feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
            provenance=ReviewFeedbackProvenance.REVIEWER,
            summary="Explain the terminal review copy",
            created_by="tester",
            scope_kind=ReviewFeedbackScopeKind.FILE,
            file_path="app.py",
        )
        missing_status = await client.run_review_action(
            ReviewLoopAction.SHOW_FEEDBACK_STATUS,
            changeset_id=result.changeset_id,
        )
        fixup = await client.run_review_action(
            ReviewLoopAction.RECORD_FEEDBACK_FIXUP,
            changeset_id=str(feedback.feedback.feedback_id),
        )
        status = await client.run_review_action(
            ReviewLoopAction.STATUS,
            changeset_id=result.changeset_id,
        )
        queue = await client.run_review_action(ReviewLoopAction.OPERATOR_QUEUE)
        next_actions = await client.run_review_action(ReviewLoopAction.NEXT_ACTIONS)
        evidence_graph = await client.run_review_action(
            ReviewLoopAction.EVIDENCE_GRAPH,
            changeset_id=result.changeset_id,
        )
        maintenance = await client.run_review_action(
            ReviewLoopAction.MAINTENANCE_CHECKS
        )

        changesets = runtime_context.repositories.sessions.list_changesets(
            session_id=state.session_id,
            include_archived=False,
            limit=10,
        )
        sources = runtime_context.repositories.sessions.list_changeset_sources(
            state.session_id,
            changesets[0].changeset_id,
        )

        assert "Created review changeset" in result.headline
        assert result.dashboard_path == f"/app/changesets/{result.changeset_id}"
        assert any("workspace diff has" in item for item in result.limitations)
        assert changesets[0].session_id == state.session_id
        assert changesets[0].objective == "Review current terminal UX work"
        assert sources[0].source_kind == ChangesetSourceKind.WORKSPACE_DIFF
        assert sources[0].source_session_id == state.session_id
        assert status.changeset_id == result.changeset_id
        assert "Review status" in status.headline
        assert queue.headline == "Operator queue"
        assert any("Counts:" in detail for detail in queue.details)
        assert queue.safe_next_actions[0] == (
            "glassbox queue list --view action-needed --cwd ."
        )
        assert next_actions.headline == "Next actions"
        assert "glassbox queue list --view action-needed --cwd ." in (
            next_actions.safe_next_actions
        )
        assert evidence_graph.changeset_id == result.changeset_id
        assert "Evidence graph summary" in evidence_graph.headline
        assert any("Claim posture:" in detail for detail in evidence_graph.details)
        assert maintenance.headline == "Maintenance checks"
        assert "glassbox observability status --cwd ." in maintenance.safe_next_actions
        assert any("Missing fixup inventory" in item for item in missing_status.details)
        assert any(
            f"glassbox changeset feedback fixup {feedback.feedback.feedback_id} --cwd ."
            in item
            for item in missing_status.details
        )
        assert fixup.changeset_id == result.changeset_id
        assert "Recorded fixup inventory" in fixup.headline
        assert any("No tests, staging" in detail for detail in fixup.details)
    finally:
        connection.close()


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    (path / "app.py").write_text("print('review loop')\n", encoding="utf-8")
