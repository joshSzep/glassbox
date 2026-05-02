"""CLI coverage for branch-candidate adoption into changesets."""

import json
import subprocess
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_branch_candidate_adoption_preview_and_confirmed_adoption(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    _init_git_repo(tmp_path)
    _seed_session(db_path, tmp_path, session_id)

    start_exit = main(
        [
            "branch-search",
            "start",
            str(session_id),
            "--objective",
            "Try candidate adoption",
            "--strategy",
            "targeted fix",
            "--max-candidates",
            "1",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    started = json.loads(capsys.readouterr().out)
    search_id = started["search_id"]
    candidate_id = started["candidate_ids"][0]

    select_exit = main(
        [
            "branch-search",
            "select",
            search_id,
            candidate_id,
            "--reason",
            "best candidate evidence",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    selected = json.loads(capsys.readouterr().out)

    preview_exit = main(
        [
            "changeset",
            "adoption-preview",
            "--branch-search",
            search_id,
            "--candidate",
            candidate_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    preview = json.loads(capsys.readouterr().out)

    worktree_exit = main(
        [
            "worktree",
            "create",
            "--session",
            str(session_id),
            "--source",
            "branch-search-candidate",
            "--branch-search",
            search_id,
            "--candidate",
            candidate_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    worktree = json.loads(capsys.readouterr().out)["worktree"]
    worktree_id = worktree["worktree_id"]
    worktree_path = Path(worktree["path"])
    (worktree_path / "app.py").write_text(
        "print('candidate dirty')\n", encoding="utf-8"
    )

    worktree_preview_exit = main(
        [
            "changeset",
            "adoption-preview",
            "--branch-search",
            search_id,
            "--candidate",
            candidate_id,
            "--worktree",
            worktree_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    worktree_preview = json.loads(capsys.readouterr().out)

    unconfirmed_exit = main(
        [
            "changeset",
            "adopt-candidate",
            "--branch-search",
            search_id,
            "--candidate",
            candidate_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    unconfirmed = capsys.readouterr()

    adopt_exit = main(
        [
            "changeset",
            "adopt-candidate",
            "--branch-search",
            search_id,
            "--candidate",
            candidate_id,
            "--worktree",
            worktree_id,
            "--confirm",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    adopted = json.loads(capsys.readouterr().out)
    changeset_id = adopted["changeset"]["changeset_id"]

    show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    detail = json.loads(capsys.readouterr().out)
    cleanup_exit = main(
        [
            "worktree",
            "cleanup",
            worktree_id,
            "--confirm",
            "--discard-user-changes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    capsys.readouterr()

    assert start_exit == 0
    assert select_exit == 0
    assert selected["state"] == "select"
    assert preview_exit == 0
    assert preview["selected"] is True
    assert preview["changeset_ready"] is True
    assert "candidate diff inventory is not retained" in preview["limitations"]
    assert "no worktree state was provided" in preview["limitations"][-1]
    assert worktree_exit == 0
    assert worktree_preview_exit == 0
    assert worktree_preview["worktree"]["worktree_id"] == worktree_id
    assert worktree_preview["conflicts"] == [
        "worktree has local changes that must be inspected before cleanup"
    ]
    assert unconfirmed_exit == 1
    assert "requires --confirm" in unconfirmed.err
    assert adopt_exit == 0
    assert adopted["safe_copy"].startswith("Glassbox recorded candidate adoption")
    assert adopted["changeset"]["stored_events"][-1]["payload"]["event_type"] == (
        "ChangesetCandidateAdopted"
    )
    assert adopted["preview"]["workspace_mutation_performed"] is False
    assert show_exit == 0
    assert detail["changeset"]["branch_search_id"] == search_id
    assert detail["changeset"]["branch_candidate_id"] == candidate_id
    assert detail["sources"][0]["source_kind"] == "branch_search_candidate"
    assert cleanup_exit == 0


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


def _seed_session(db_path: Path, tmp_path: Path, session_id) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )
        )
    finally:
        connection.close()
