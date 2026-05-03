"""Integration coverage for TUI review-loop command client actions."""

import asyncio
import subprocess
from pathlib import Path

from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.core import ChangesetSourceKind
from glassbox.core import SessionConfig
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
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
        status = await client.run_review_action(
            ReviewLoopAction.STATUS,
            changeset_id=result.changeset_id,
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

        assert result.changeset_id is not None
        assert "Created review changeset" in result.headline
        assert result.dashboard_path == f"/app/changesets/{result.changeset_id}"
        assert any("workspace diff has" in item for item in result.limitations)
        assert changesets[0].session_id == state.session_id
        assert changesets[0].objective == "Review current terminal UX work"
        assert sources[0].source_kind == ChangesetSourceKind.WORKSPACE_DIFF
        assert sources[0].source_session_id == state.session_id
        assert status.changeset_id == result.changeset_id
        assert "Review status" in status.headline
    finally:
        connection.close()


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    (path / "app.py").write_text("print('review loop')\n", encoding="utf-8")
