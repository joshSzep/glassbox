"""Tests for read-only changeset workup previews."""

import subprocess
from pathlib import Path

from glassbox.runtime.changeset_workup import ChangesetWorkupPreviewService
from glassbox.runtime.operator_queue_changeset_items import build_changeset_queue_items


def test_changeset_workup_preview_is_non_mutating_action_map(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "review.md").write_text("review flow\n", encoding="utf-8")

    preview = ChangesetWorkupPreviewService().preview_sync(tmp_path)

    assert preview.inspected_only is True
    assert preview.changeset_created is False
    assert preview.source_mutation_performed is False
    assert preview.command_execution_performed is False
    assert sorted(preview.changed_paths) == ["app.py", "docs/review.md"]
    assert preview.candidate_groupings[0].source_kind == "workspace-diff"
    assert preview.candidate_groupings[0].changed_path_count == 2
    assert preview.inventory.summary.docs_path_count == 1
    assert preview.verification_plan.plan_entries
    assert any(
        "changeset create --from workspace-diff" in action
        for action in preview.safe_next_actions
    )
    assert any(
        candidate.source == "changed-docs" for candidate in preview.memory_candidates
    )
    assert "no changeset was created" in preview.non_claims


def test_changeset_queue_source_is_an_explicit_refactor_gap() -> None:
    assert build_changeset_queue_items() == []


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
