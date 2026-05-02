"""Tests for advisory changeset commit readiness."""

from datetime import UTC
from datetime import datetime

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetVerificationState
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changesets import ChangesetInventoryStatus
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.commit_readiness import derive_commit_readiness
from glassbox.tools.workflow import DiffFileSummary
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import GitStatusResult
from glassbox.tools.workflow import PatchRiskSummary


def test_commit_readiness_ready_with_staged_clean_evidence() -> None:
    fixture = _fixture()

    assessment = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=fixture.inventory.artifact_id,
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[_review_readiness(fixture, ChangesetReadinessState.READY)],
        git_status=GitStatusResult(branch="main", staged=["src/app.py"]),
        workspace_diff=_diff(["src/app.py"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )

    assert assessment.state == ChangesetReadinessState.READY
    assert assessment.blockers == []
    assert assessment.git.staged_paths == ["src/app.py"]
    assert "git status --short" in assessment.safe_next_actions


def test_commit_readiness_blocks_dirty_untracked_ambiguity() -> None:
    fixture = _fixture()

    assessment = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=fixture.inventory.artifact_id,
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[_review_readiness(fixture, ChangesetReadinessState.READY)],
        git_status=GitStatusResult(
            branch="main",
            staged=["src/app.py"],
            modified=["src/app.py"],
            untracked=["notes.txt"],
        ),
        workspace_diff=_diff(["src/app.py", "notes.txt"], untracked=["notes.txt"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )

    assert assessment.state == ChangesetReadinessState.DIRTY_UNTRACKED_RISK
    assert "ambiguous" in assessment.reason
    assert assessment.git.untracked_paths == ["notes.txt"]


def test_commit_readiness_maps_failed_verification_to_failed_checks() -> None:
    fixture = _fixture()

    assessment = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.FAILED,
            summary="pytest failed for changed paths",
            verification_id=fixture.verification_id,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=fixture.inventory.artifact_id,
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[_review_readiness(fixture, ChangesetReadinessState.READY)],
        git_status=GitStatusResult(branch="main", staged=["src/app.py"]),
        workspace_diff=_diff(["src/app.py"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )

    assert assessment.state == ChangesetReadinessState.FAILED_CHECKS
    assert assessment.blockers == ["pytest failed for changed paths"]


def test_commit_readiness_requires_fresh_review_brief() -> None:
    fixture = _fixture()

    missing = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
        ),
        review_briefs=[],
        readiness=[],
        git_status=GitStatusResult(branch="main", staged=["src/app.py"]),
        workspace_diff=_diff(["src/app.py"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )
    stale = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=new_artifact_id(),
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[_review_readiness(fixture, ChangesetReadinessState.READY)],
        git_status=GitStatusResult(branch="main", staged=["src/app.py"]),
        workspace_diff=_diff(["src/app.py"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )

    assert missing.state == ChangesetReadinessState.NEEDS_REVIEW
    assert stale.state == ChangesetReadinessState.NEEDS_REVIEW
    assert "glassbox changeset brief CHANGESET --cwd ." in missing.safe_next_actions


def test_commit_readiness_surfaces_policy_sensitive_paths_and_accepted_risk() -> None:
    fixture = _fixture(accepted_risk_count=1)

    assessment = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
            accepted_risk_count=1,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=fixture.inventory.artifact_id,
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[_review_readiness(fixture, ChangesetReadinessState.READY)],
        git_status=GitStatusResult(
            branch="main",
            staged=["docs/tasks-v12.md", "frontend/generated/api.ts"],
        ),
        workspace_diff=_diff(
            ["docs/tasks-v12.md", "frontend/generated/api.ts"],
            generated=["frontend/generated/api.ts"],
            policy_sensitive=True,
        ),
        staged_diff=_diff(
            ["docs/tasks-v12.md", "frontend/generated/api.ts"],
            scope=DiffSummaryScope.STAGED,
            generated=["frontend/generated/api.ts"],
            policy_sensitive=True,
        ),
    )

    assert assessment.state == ChangesetReadinessState.NEEDS_REVIEW
    assert assessment.accepted_risk_count == 2
    assert assessment.git.generated_paths == ["frontend/generated/api.ts"]
    assert assessment.git.policy_sensitive_paths == [
        "docs/tasks-v12.md",
        "frontend/generated/api.ts",
    ]
    assert any(signal.signal_id == "accepted-risk" for signal in assessment.signals)
    assert any(signal.signal_id == "generated-paths" for signal in assessment.signals)


def test_commit_readiness_cites_failed_retained_precommit_evidence() -> None:
    fixture = _fixture()

    assessment = derive_commit_readiness(
        changeset=fixture.changeset,
        inventory=fixture.inventory,
        inventory_status=_fresh_inventory_status(),
        verification_plan=_verification_plan(
            fixture.changeset.changeset_id,
            fixture.changeset.session_id,
            state=ChangesetVerificationState.PASSED,
            verification_id=fixture.verification_id,
        ),
        review_briefs=[
            _review_brief(
                fixture,
                inventory_artifact_id=fixture.inventory.artifact_id,
                verification_id=fixture.verification_id,
            )
        ],
        readiness=[
            _review_readiness(fixture, ChangesetReadinessState.READY),
            _commit_readiness_record(fixture, ChangesetReadinessState.FAILED_CHECKS),
        ],
        git_status=GitStatusResult(branch="main", staged=["src/app.py"]),
        workspace_diff=_diff(["src/app.py"]),
        staged_diff=_diff(["src/app.py"], scope=DiffSummaryScope.STAGED),
    )

    assert assessment.state == ChangesetReadinessState.FAILED_CHECKS
    assert any(
        signal.signal_id == "retained-precommit-evidence"
        for signal in assessment.signals
    )
    assert "pre-commit failed" in assessment.reason


class _Fixture:
    def __init__(self, *, accepted_risk_count: int = 0) -> None:
        now = datetime.now(UTC)
        self.verification_id = new_task_verification_id()
        self.changeset = ChangesetRecord(
            session_id=new_session_id(),
            changeset_id=new_changeset_id(),
            objective="Prepare commit readiness",
            summary="Change updates runtime readiness logic",
            status="active",
            created_by="operator",
            task_id=new_task_id(),
            latest_verification_id=self.verification_id,
            risk_level=ChangesetRiskLevel.LOW,
            accepted_risk_count=accepted_risk_count,
            created_at=now,
            updated_at=now,
            last_sequence=10,
        )
        self.inventory = ChangesetInventoryRecord(
            session_id=self.changeset.session_id,
            changeset_id=self.changeset.changeset_id,
            artifact_id=new_artifact_id(),
            artifact_schema_version=1,
            freshness=ChangesetInventoryFreshness.FRESH,
            changed_path_count=1,
            source_digest="sha256:abc123",
            refreshed_by="operator",
            risk_level=ChangesetRiskLevel.LOW,
            updated_at=now,
            last_sequence=11,
        )


def _fixture(*, accepted_risk_count: int = 0) -> _Fixture:
    return _Fixture(accepted_risk_count=accepted_risk_count)


def _fresh_inventory_status() -> ChangesetInventoryStatus:
    return ChangesetInventoryStatus(
        freshness=ChangesetInventoryFreshness.FRESH,
        stale=False,
        recorded_source_digest="sha256:abc123",
        current_source_digest="sha256:abc123",
    )


def _verification_plan(
    changeset_id,
    session_id,
    *,
    state: ChangesetVerificationState,
    summary: str = "verification passed",
    verification_id=None,
    accepted_risk_count: int = 0,
) -> ChangesetVerificationPlanPreview:
    return ChangesetVerificationPlanPreview(
        changeset_id=changeset_id,
        session_id=session_id,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        changed_paths=["src/app.py"],
        recommended_commands=["uv run pytest tests/unit/test_app.py"],
        readiness=ChangesetVerificationReadiness(
            state=state,
            summary=summary,
            accepted_risk_count=accepted_risk_count,
        ),
        retained_artifact_ids=[],
        safe_next_actions=["uv run pytest tests/unit/test_app.py"],
    )


def _review_brief(
    fixture: _Fixture,
    *,
    inventory_artifact_id,
    verification_id,
) -> ChangesetReviewBriefRecord:
    now = datetime.now(UTC)
    return ChangesetReviewBriefRecord(
        session_id=fixture.changeset.session_id,
        changeset_id=fixture.changeset.changeset_id,
        artifact_id=new_artifact_id(),
        artifact_schema_version=1,
        render_targets=["markdown", "json"],
        inventory_artifact_id=inventory_artifact_id,
        verification_id=verification_id,
        created_by="operator",
        redacted=True,
        local_only=True,
        created_at=now,
        last_sequence=12,
    )


def _review_readiness(
    fixture: _Fixture,
    state: ChangesetReadinessState,
) -> ChangesetReadinessRecord:
    now = datetime.now(UTC)
    return ChangesetReadinessRecord(
        session_id=fixture.changeset.session_id,
        changeset_id=fixture.changeset.changeset_id,
        readiness_kind=ChangesetReadinessKind.REVIEW,
        state=state,
        reason="review ready",
        accepted_risk_count=0,
        decided_by="operator",
        updated_at=now,
        last_sequence=13,
    )


def _commit_readiness_record(
    fixture: _Fixture,
    state: ChangesetReadinessState,
) -> ChangesetReadinessRecord:
    now = datetime.now(UTC)
    return ChangesetReadinessRecord(
        session_id=fixture.changeset.session_id,
        changeset_id=fixture.changeset.changeset_id,
        readiness_kind=ChangesetReadinessKind.COMMIT,
        state=state,
        reason="pre-commit failed",
        blockers=["pre-commit failed"],
        accepted_risk_count=0,
        decided_by="operator",
        updated_at=now,
        last_sequence=14,
    )


def _diff(
    paths: list[str],
    *,
    scope: DiffSummaryScope = DiffSummaryScope.WORKSPACE,
    generated: list[str] | None = None,
    untracked: list[str] | None = None,
    policy_sensitive: bool = False,
) -> DiffSummaryResult:
    files = [
        DiffFileSummary(
            path=path,
            change_kind="untracked" if path in (untracked or []) else "modified",
            insertions=1,
            deletions=0,
            generated=path in (generated or []),
            policy_sensitive=policy_sensitive,
        )
        for path in paths
    ]
    return DiffSummaryResult(
        scope=scope,
        clean=not paths,
        files=files,
        risk_summary=PatchRiskSummary(
            touched_files=len(paths),
            insertions=len(paths),
            generated_files=generated or [],
            policy_sensitive_paths=paths if policy_sensitive else [],
            untracked_files=untracked or [],
        ),
    )
