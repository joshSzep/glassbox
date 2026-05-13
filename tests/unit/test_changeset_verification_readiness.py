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
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationRequirement,
)
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendation_models import EvalReleaseSurfaceRecommendation
from glassbox.runtime.eval_recommendation_models import EvalTestTargetRecommendation
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.verification_plan_builder import MAX_VERIFICATION_PLAN_ENTRIES
from glassbox.runtime.verification_plan_builder import (
    MAX_VERIFICATION_PLAN_SKIPPED_CHECKS,
)
from glassbox.runtime.verification_plan_builder import build_verification_plan_entries
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


def test_readiness_surfaces_stale_repository_intelligence_recommendations() -> None:
    inventory = _inventory("src/glassbox/runtime/repository_index.py")
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=["src/glassbox/runtime/repository_index.py"],
        warnings=[
            "Repository intelligence snapshot is stale; eval recommendation "
            "source metadata and command recipes are degraded until rebuild."
        ],
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id="repo-intelligence-runtime",
                title="Repository intelligence runtime",
                confidence="degraded",
                source="repository-intelligence",
                freshness="stale",
                matched_paths=["src/glassbox/runtime/repository_index.py"],
                commands=["uv run pytest tests/unit/test_repository_index.py -q"],
                safe_next_commands=[
                    "uv run pytest tests/unit/test_repository_index.py -q"
                ],
            )
        ],
    )

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        eval_recommendation=recommendation,
    )

    requirement_ids = [
        requirement.requirement_id for requirement in readiness.requirements
    ]
    assert readiness.state == ChangesetVerificationState.STALE
    assert "repository-intelligence-stale" in requirement_ids
    assert "recipe-stale:repo-intelligence-runtime" in requirement_ids
    assert any(
        "glassbox repo index build" in action for action in readiness.safe_next_actions
    )


def test_readiness_bounds_repository_intelligence_requirement_ids() -> None:
    command = (
        "uv run pytest "
        "tests/unit/test_changeset_derivation.py "
        "tests/unit/test_change_inventory.py "
        "tests/unit/test_changeset_verification_readiness.py "
        "tests/unit/test_review_briefs.py "
        "tests/unit/test_commit_readiness.py "
        "tests/integration/test_cli_changeset_commands.py "
        "tests/integration/test_web_changeset_routes.py -q"
    )
    inventory = _inventory("src/glassbox/runtime/changeset_verification_readiness.py")
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=["src/glassbox/runtime/changeset_verification_readiness.py"],
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id="repo-intelligence-recipe-eval-recipe-changeset-runtime-0",
                title="Changeset runtime checks",
                source="repository-intelligence",
                matched_paths=[
                    "src/glassbox/runtime/changeset_verification_readiness.py"
                ],
                commands=[command],
            )
        ],
    )

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        eval_recommendation=recommendation,
    )

    requirement = readiness.requirements[0]
    assert len(requirement.requirement_id) <= 200
    assert requirement.requirement_id.startswith("recipe:repo-intelligence")
    assert ":sha256:" in requirement.requirement_id
    assert requirement.command == command.split()


def test_readiness_bounds_aggregate_safe_next_actions() -> None:
    inventory = _inventory("src/glassbox/runtime/changeset_verification_readiness.py")
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=["src/glassbox/runtime/changeset_verification_readiness.py"],
        suggested_commands=[
            f"uv run glassbox eval run synthetic.case.{index} --cwd ."
            for index in range(30)
        ],
    )

    readiness = derive_changeset_verification_readiness(
        inventory=inventory,
        inventory_freshness=ChangesetInventoryFreshness.FRESH,
        eval_recommendation=recommendation,
    )

    assert len(readiness.requirements) == 30
    assert len(readiness.safe_next_actions) == 20
    assert readiness.safe_next_actions[0].startswith("glassbox eval recommend ")


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


def test_verification_plan_builder_proposes_entries_and_keeps_advisory_separate() -> (
    None
):
    changed_paths = ["frontend/app/changesets/page.tsx"]
    command = "pnpm --dir frontend test -- changeset-console.test.tsx"
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=changed_paths,
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id="frontend-changeset-console",
                title="Frontend changeset console",
                source="repository-intelligence",
                matched_paths=changed_paths,
                commands=[command],
            )
        ],
        profiles=[
            EvalProfileRecommendation(
                profile_id="live-provider-canary",
                title="Live provider canary",
                confidence="direct",
                verification_stage="advisory",
                track="live-provider-canary",
                blocking=False,
                matched_paths=changed_paths,
            )
        ],
    )

    entries, skipped = build_verification_plan_entries(
        changed_paths=changed_paths,
        recommendation=recommendation,
    )

    command_entries = [entry for entry in entries if entry.command == command.split()]
    manual_entries = [entry for entry in entries if entry.manual_evidence_required]
    assert command_entries
    assert command_entries[0].source == VerificationPlanSource.REPOSITORY_INTELLIGENCE
    assert command_entries[0].lifecycle_state.value == "proposed"
    assert command_entries[0].command_recipe is not None
    assert any(entry.check_name == "Advisory browser evidence" for entry in entries)
    assert any(
        entry.check_name == "Advisory accessibility evidence" for entry in entries
    )
    assert manual_entries
    assert skipped[0].target_id == "live-provider-canary"
    assert "explicitly selects" in skipped[0].explanation


def test_verification_plan_builder_keeps_recommendation_source_entries() -> None:
    changed_paths = ["src/glassbox/runtime/model_loop.py"]
    test_command = "uv run pytest tests/unit/test_runtime_transport.py -q"
    profile_command = "uv run glassbox eval run --profile commit-smoke --cwd ."
    case_command = "uv run glassbox eval run smoke.hello --cwd ."
    release_command = "uv run pytest tests/unit/test_release_candidate_docs.py -q"
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=changed_paths,
        test_targets=[
            EvalTestTargetRecommendation(
                target_id="runtime-transport-tests",
                title="Runtime transport tests",
                confidence="direct",
                source="repository-intelligence",
                matched_paths=changed_paths,
                command=test_command,
                reasons=["runtime path maps to transport coverage"],
            )
        ],
        profiles=[
            EvalProfileRecommendation(
                profile_id="commit-smoke",
                title="Commit smoke",
                confidence="direct",
                verification_stage="commit-time",
                track="deterministic",
                blocking=True,
                matched_paths=changed_paths,
                safe_next_commands=[profile_command],
            )
        ],
        cases=[
            EvalCaseRecommendation(
                case_id="smoke.hello",
                title="Smoke hello",
                confidence="direct",
                matched_paths=changed_paths,
            )
        ],
        release_surfaces=[
            EvalReleaseSurfaceRecommendation(
                verification_stage="release-candidate",
                impacted=True,
                release_gate_commands=[release_command],
            )
        ],
    )

    entries, skipped = build_verification_plan_entries(
        changed_paths=changed_paths,
        recommendation=recommendation,
    )

    assert skipped == []
    by_command = {tuple(entry.command): entry for entry in entries if entry.command}
    test_entry = by_command[tuple(test_command.split())]
    assert test_entry.kind == VerificationCheckKind.TEST
    assert test_entry.source == VerificationPlanSource.REPOSITORY_INTELLIGENCE
    assert "runtime path maps" in test_entry.rationale
    profile_entry = by_command[tuple(profile_command.split())]
    assert profile_entry.eval_profile_id == "commit-smoke"
    assert profile_entry.release_surfaces == ["commit-time"]
    case_entry = by_command[tuple(case_command.split())]
    assert case_entry.eval_case_id == "smoke.hello"
    release_entry = by_command[tuple(release_command.split())]
    assert release_entry.kind == VerificationCheckKind.PACKAGE
    assert release_entry.source == VerificationPlanSource.RELEASE_GATE
    assert release_entry.release_surfaces == ["release-candidate"]


def test_verification_plan_builder_skips_unsafe_recipes_and_caps_skipped_rows() -> None:
    changed_paths = ["src/glassbox/runtime/verification_plan_builder.py"]
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=changed_paths,
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id=f"unsafe-{index}",
                title=f"Unsafe recipe {index}",
                matched_paths=changed_paths,
                commands=[f"git push origin unsafe-{index}"],
            )
            for index in range(MAX_VERIFICATION_PLAN_SKIPPED_CHECKS + 5)
        ],
    )

    entries, skipped = build_verification_plan_entries(
        changed_paths=changed_paths,
        recommendation=recommendation,
    )

    assert all(not entry.command for entry in entries)
    assert len(skipped) == MAX_VERIFICATION_PLAN_SKIPPED_CHECKS
    assert skipped[0].reason == "unsafe-command"
    assert skipped[-1].reason == "skipped-check-limit"
    assert "capped" in skipped[-1].explanation


def test_verification_plan_builder_adds_plan_entry_limit_row() -> None:
    changed_paths = ["src/glassbox/runtime/verification_plan_builder.py"]
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=changed_paths,
        test_targets=[
            EvalTestTargetRecommendation(
                target_id=f"target-{index}",
                title=f"Target {index}",
                confidence="direct",
                source="repository-intelligence",
                matched_paths=changed_paths,
                command=(
                    "uv run pytest tests/unit/test_changeset_verification_readiness.py "
                    f"-q --target-{index}"
                ),
            )
            for index in range(MAX_VERIFICATION_PLAN_ENTRIES + 5)
        ],
    )

    entries, skipped = build_verification_plan_entries(
        changed_paths=changed_paths,
        recommendation=recommendation,
    )

    assert len(entries) == MAX_VERIFICATION_PLAN_ENTRIES
    assert skipped[-1].reason == "plan-entry-limit"
    assert "entry summaries" in skipped[-1].explanation


def test_verification_plan_builder_characterizes_recipe_and_readiness_duplicates() -> (
    None
):
    changed_paths = ["src/glassbox/runtime/verification_plan_builder.py"]
    command_parts = [
        "uv",
        "run",
        "pytest",
        "tests/unit/test_changeset_verification_readiness.py",
        "-q",
    ]
    command = " ".join(command_parts)
    recommendation = EvalRecommendationReport(
        workspace_root=Path("."),
        touched_paths=changed_paths,
        recipes=[
            EvalVerificationRecipeRecommendation(
                recipe_id="verification-plan-builder",
                title="Verification plan builder",
                source="repository-intelligence",
                matched_paths=changed_paths,
                commands=[command],
            )
        ],
    )
    readiness_verification_id = new_task_verification_id()
    readiness = ChangesetVerificationReadiness(
        state=ChangesetVerificationState.MISSING,
        summary="verification readiness is missing",
        requirements=[
            ChangesetVerificationRequirement(
                requirement_id="readiness:verification-plan-builder",
                state=ChangesetVerificationState.MISSING,
                check_name="Verification plan builder readiness",
                reason="readiness still asks for the same focused command",
                source=VerificationPlanSource.CHANGED_PATHS,
                kind=VerificationCheckKind.TEST,
                command=command_parts,
                changed_paths=changed_paths,
                verification_id=readiness_verification_id,
            )
        ],
        missing_count=1,
    )

    entries, skipped = build_verification_plan_entries(
        changed_paths=changed_paths,
        readiness=readiness,
        recommendation=recommendation,
    )

    command_entries = [entry for entry in entries if entry.command == command_parts]
    assert skipped == []
    assert len(command_entries) == 1
    assert command_entries[0].source == VerificationPlanSource.CHANGED_PATHS
    assert command_entries[0].verification_id == readiness_verification_id
    assert {ref.kind.value for ref in command_entries[0].evidence_references} == {
        "repository_intelligence",
        "verification",
    }
    assert any(
        "Verification recipe verification-plan-builder" in ref.summary
        for ref in command_entries[0].evidence_references
    )


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
