"""Tests for deterministic changeset verification readiness derivation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.workspace_profile import WorkspaceProfile
from glassbox.runtime.workspace_profile import WorkspaceVerificationDefaults
from glassbox.tools.workflow import DiffFileSummary
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope


def test_readiness_requires_inventory_before_verification_claims() -> None:
    readiness = derive_changeset_verification_readiness(
        inventory=None,
        inventory_freshness=ChangesetInventoryFreshness.UNKNOWN,
    )

    assert readiness.state == ChangesetVerificationState.MISSING
    assert readiness.missing_count == 1
    assert "glassbox changeset refresh" in readiness.safe_next_actions[0]


def test_readiness_marks_stale_inventory_before_old_checks() -> None:
    inventory = _inventory("src/glassbox/runtime/changesets.py")
    ledger = [
        _ledger(
            status=TaskVerificationStatus.PASSED,
            changed_paths=["src/glassbox/runtime/changesets.py"],
        )
    ]

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.STALE,
        task_ledger=ledger,
    )

    assert readiness.state == ChangesetVerificationState.STALE
    assert readiness.stale_count == 1
    assert any(
        requirement.state == ChangesetVerificationState.PASSED
        for requirement in readiness.requirements
    )


def test_readiness_marks_passed_check_stale_when_inventory_is_newer() -> None:
    inventory = _inventory("src/glassbox/runtime/changesets.py")
    ledger = [
        _ledger(
            status=TaskVerificationStatus.PASSED,
            changed_paths=["src/glassbox/runtime/changesets.py"],
            last_success_sequence=4,
            last_sequence=5,
        )
    ]

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        inventory_sequence=10,
        task_ledger=ledger,
    )

    assert readiness.state == ChangesetVerificationState.STALE
    assert readiness.stale_count == 1
    assert "predates the latest inventory" in readiness.requirements[0].reason


def test_readiness_keeps_passed_check_fresh_for_non_overlapping_paths() -> None:
    inventory = _inventory("src/glassbox/runtime/changesets.py")
    ledger = [
        _ledger(
            status=TaskVerificationStatus.PASSED,
            changed_paths=["docs/change-inventory.md"],
            last_success_sequence=4,
            last_sequence=5,
        )
    ]

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        inventory_sequence=10,
        task_ledger=ledger,
    )

    assert readiness.state == ChangesetVerificationState.MISSING
    assert readiness.missing_count == 1


def test_readiness_uses_eval_recipe_recommendations_and_passed_ledger() -> None:
    command_parts = [
        "uv",
        "run",
        "pytest",
        "tests/unit/test_changeset_verification_readiness.py",
    ]
    command = " ".join(command_parts)
    inventory = _inventory("src/glassbox/runtime/changeset_verification_readiness.py")
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=["src/glassbox/runtime/changeset_verification_readiness.py"],
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id="changeset-readiness",
                title="Changeset readiness tests",
                matched_paths=[
                    "src/glassbox/runtime/changeset_verification_readiness.py"
                ],
                commands=[command],
            )
        ],
    )
    ledger = [
        _ledger(
            status=TaskVerificationStatus.PASSED,
            command=command_parts,
            kind=VerificationCheckKind.COMMAND,
            source=VerificationPlanSource.EVAL_RECOMMENDATION,
        )
    ]

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        task_ledger=ledger,
        eval_recommendation=recommendation,
    )

    assert readiness.state == ChangesetVerificationState.PASSED
    assert readiness.failed_count == 0
    assert readiness.requirements[0].verification_id == ledger[0].verification_id


def test_readiness_failed_ledger_blocks_review_posture() -> None:
    inventory = _inventory("src/glassbox/runtime/changesets.py")
    ledger = [
        _ledger(
            status=TaskVerificationStatus.FAILED,
            changed_paths=["src/glassbox/runtime/changesets.py"],
            latest_failed_summary="unit test failed",
        )
    ]

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        task_ledger=ledger,
    )

    assert readiness.state == ChangesetVerificationState.FAILED
    assert readiness.failed_count == 1
    assert readiness.requirements[0].evidence_summary == "unit test failed"


def test_readiness_workspace_profile_adds_missing_eval_requirement() -> None:
    inventory = _inventory("src/glassbox/runtime/changesets.py")
    profile = WorkspaceProfile(
        verification=WorkspaceVerificationDefaults(eval_profile="commit-smoke")
    )

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        workspace_profile=profile,
    )

    assert readiness.state == ChangesetVerificationState.MISSING
    assert any(
        requirement.source == VerificationPlanSource.WORKSPACE_PROFILE
        for requirement in readiness.requirements
    )


def test_readiness_no_changed_paths_is_not_applicable() -> None:
    inventory = change_inventory_from_diff_summary(
        DiffSummaryResult(scope=DiffSummaryScope.WORKSPACE, clean=True)
    )

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
    )

    assert readiness.state == ChangesetVerificationState.NOT_APPLICABLE
    assert readiness.requirements[0].blocking is False


def _inventory(path: str) -> ChangeInventoryArtifact:
    return change_inventory_from_diff_summary(
        DiffSummaryResult(
            scope=DiffSummaryScope.WORKSPACE,
            files=[
                DiffFileSummary(
                    path=path,
                    change_kind="modified",
                    insertions=3,
                    deletions=1,
                )
            ],
        )
    )


def _ledger(
    *,
    status: TaskVerificationStatus,
    command: list[str] | None = None,
    changed_paths: list[str] | None = None,
    kind: VerificationCheckKind = VerificationCheckKind.TEST,
    source: VerificationPlanSource = VerificationPlanSource.CHANGED_PATHS,
    latest_failed_summary: str | None = None,
    last_success_sequence: int | None = None,
    last_sequence: int = 10,
) -> TaskVerificationLedgerRecord:
    return TaskVerificationLedgerRecord(
        session_id=new_session_id(),
        task_id=new_task_id(),
        verification_id=new_task_verification_id(),
        status=status,
        check_name="focused check",
        kind=kind,
        source=source,
        command=command or ["uv", "run", "pytest"],
        changed_paths=[Path(path) for path in changed_paths or []],
        last_success_sequence=last_success_sequence,
        latest_failed_summary=latest_failed_summary,
        updated_at=datetime.now(UTC),
        last_sequence=last_sequence,
    )
