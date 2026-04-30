"""Tests for read-time verification drift assessment."""

import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.verification_drift import assess_verification_drift


def test_verification_drift_reports_fresh_clean_workspace(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    task_id = new_task_id()
    ledger = [_ledger(task_id, changed_paths=["src/app.py"])]

    assessment = assess_verification_drift(
        tmp_path,
        task_id=task_id,
        ledger=ledger,
    )

    assert assessment.posture == "fresh"
    assert assessment.workspace_clean is True
    assert assessment.changed_path_digest is None


def test_verification_drift_detects_edit_after_test(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    task_id = new_task_id()
    ledger = [_ledger(task_id, changed_paths=["src/app.py"])]
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")

    assessment = assess_verification_drift(
        tmp_path,
        task_id=task_id,
        ledger=ledger,
    )

    assert assessment.posture == "stale"
    assert assessment.workspace_clean is False
    assert assessment.material_changed_paths == ["src/app.py"]
    assert assessment.stale_verification_ids == [ledger[0].verification_id]
    assert assessment.stale_changed_paths == ["src/app.py"]
    assert assessment.changed_path_digest is not None


def test_verification_drift_classifies_docs_only_drift(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    task_id = new_task_id()
    ledger = [_ledger(task_id, changed_paths=["src/app.py"])]
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")

    assessment = assess_verification_drift(
        tmp_path,
        task_id=task_id,
        ledger=ledger,
    )

    assert assessment.posture == "docs_only_drift"
    assert assessment.docs_only_changed_paths == ["docs/guide.md"]
    assert assessment.material_changed_paths == []
    assert assessment.stale_verification_ids == []


def test_verification_drift_classifies_generated_file_drift(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    task_id = new_task_id()
    ledger = [_ledger(task_id, changed_paths=["src/app.py"])]
    generated_path = tmp_path / "frontend" / "generated" / "api-types.ts"
    generated_path.parent.mkdir(parents=True)
    generated_path.write_text("export type Generated = string;\n", encoding="utf-8")

    assessment = assess_verification_drift(
        tmp_path,
        task_id=task_id,
        ledger=ledger,
    )

    assert assessment.posture == "generated_drift"
    assert assessment.generated_changed_paths == ["frontend/generated/api-types.ts"]
    assert assessment.material_changed_paths == []
    assert assessment.stale_verification_ids == []


def _ledger(
    task_id,
    *,
    changed_paths: list[str],
) -> TaskVerificationLedgerRecord:
    return TaskVerificationLedgerRecord(
        session_id=new_session_id(),
        task_id=task_id,
        verification_id=new_task_verification_id(),
        status=TaskVerificationStatus.PASSED,
        check_name="pytest",
        kind=VerificationCheckKind.TEST,
        source=VerificationPlanSource.OPERATOR,
        command=["uv", "run", "pytest"],
        changed_paths=[Path(path) for path in changed_paths],
        attempt_count=1,
        latest_attempt=1,
        last_success_sequence=3,
        summary="passed",
        updated_at=datetime.now(UTC),
        last_sequence=3,
    )


def _init_git_repo(path: Path) -> None:
    (path / "src").mkdir()
    (path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tests"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        check=True,
        capture_output=True,
    )
