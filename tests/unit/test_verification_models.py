"""Tests for v8 verification plan models and failure digests."""

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from glassbox.core import EventPayloadType
from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationPlanned
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlan
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.verification import classify_verification_failure


def test_verification_plan_requires_eval_target_for_eval_checks() -> None:
    with pytest.raises(ValidationError):
        VerificationPlanEntry(
            verification_id=new_task_verification_id(),
            check_name="Run selected eval",
            kind=VerificationCheckKind.EVAL,
            command=["uv", "run", "glassbox", "eval", "run", "smoke.hello"],
            source=VerificationPlanSource.EVAL_RECOMMENDATION,
            rationale="Changed replay runtime paths matched smoke evals.",
        )


def test_verification_plan_accepts_command_and_unique_entries() -> None:
    task_id = new_task_id()
    entry = VerificationPlanEntry(
        verification_id=new_task_verification_id(),
        check_name="Targeted pytest",
        kind=VerificationCheckKind.TEST,
        command=["uv", "run", "pytest", "tests/unit/test_model_loop.py"],
        source=VerificationPlanSource.CHANGED_PATHS,
        rationale="Changed runtime model loop code.",
        expected_exit_codes=[0, 0],
    )

    plan = VerificationPlan(task_id=task_id, entries=[entry])

    assert plan.task_id == task_id
    assert entry.expected_exit_codes == [0]


def test_verification_plan_rejects_duplicate_verification_ids() -> None:
    verification_id = new_task_verification_id()
    entry = VerificationPlanEntry(
        verification_id=verification_id,
        check_name="Lint",
        kind=VerificationCheckKind.LINT,
        command=["uv", "run", "ruff", "check", "src/glassbox"],
        source=VerificationPlanSource.WORKSPACE_PROFILE,
        rationale="Workspace profile requires linting.",
    )

    with pytest.raises(ValidationError):
        VerificationPlan(task_id=new_task_id(), entries=[entry, entry])


def test_verification_plan_entry_carries_v16_lifecycle_metadata() -> None:
    entry = VerificationPlanEntry(
        verification_id=new_task_verification_id(),
        check_name="Commit smoke profile",
        kind=VerificationCheckKind.EVAL,
        lifecycle_state=VerificationPlanLifecycleState.PROPOSED,
        target=NextActionTarget(
            kind=NextActionTargetKind.VERIFICATION,
            target_id="commit-smoke",
            label="Commit smoke profile",
        ),
        command_recipe=NextActionCommandRecipe(
            command=["uv", "run", "glassbox", "eval", "run", "--profile", "commit"],
            display="uv run glassbox eval run --profile commit --cwd .",
            purpose="Run deterministic commit-time smoke checks.",
            requires_approval=False,
        ),
        source=VerificationPlanSource.EVAL_RECOMMENDATION,
        rationale="Changed runtime paths matched commit-time eval metadata.",
        selection_rationale=(
            "Cheapest deterministic profile with changed-path coverage."
        ),
        eval_profile_id="commit",
        release_surfaces=["commit-time"],
        evidence_references=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                ref_id="repo-index",
                summary="Repository intelligence mapped the changed path.",
            )
        ],
        stale_reasons=["previous eval summary predates changed paths"],
    )

    payload = entry.model_dump(mode="json")

    assert payload["lifecycle_state"] == "proposed"
    assert payload["command_recipe"]["requires_approval"] is False
    assert payload["target"]["kind"] == "verification"
    assert payload["release_surfaces"] == ["commit-time"]
    assert payload["selection_rationale"].startswith("Cheapest deterministic")
    assert payload["evidence_references"][0]["kind"] == "repository_intelligence"
    assert payload["stale_reasons"] == ["previous eval summary predates changed paths"]


def test_verification_plan_allows_manual_only_checks_without_commands() -> None:
    entry = VerificationPlanEntry(
        verification_id=new_task_verification_id(),
        check_name="Browser smoke evidence",
        kind=VerificationCheckKind.CUSTOM,
        lifecycle_state=VerificationPlanLifecycleState.MANUAL_ONLY,
        source=VerificationPlanSource.MANUAL_EVIDENCE,
        rationale="Dashboard behavior requires retained manual browser evidence.",
        manual_evidence_required=True,
        blocking=False,
    )

    assert entry.command == []
    assert entry.lifecycle_state == VerificationPlanLifecycleState.MANUAL_ONLY


def test_verification_plan_rejects_executable_entry_without_command() -> None:
    with pytest.raises(ValidationError, match="command or command_recipe"):
        VerificationPlanEntry(
            verification_id=new_task_verification_id(),
            check_name="Missing command",
            kind=VerificationCheckKind.TEST,
            lifecycle_state=VerificationPlanLifecycleState.SELECTED,
            source=VerificationPlanSource.CHANGED_PATHS,
            rationale="Selected tests must name the command to review.",
        )


def test_verification_events_round_trip_through_union() -> None:
    adapter = TypeAdapter(EventPayloadType)
    task_id = new_task_id()
    verification_id = new_task_verification_id()
    entry = VerificationPlanEntry(
        verification_id=verification_id,
        check_name="Package smoke",
        kind=VerificationCheckKind.PACKAGE,
        command=["uv", "build"],
        source=VerificationPlanSource.OPERATOR,
        rationale="Operator requested package validation.",
    )
    failure = classify_verification_failure("build failed: missing package data")

    planned = adapter.validate_python(
        TaskVerificationPlanned(task_id=task_id, verification=entry).model_dump(
            mode="python"
        )
    )
    failed = adapter.validate_python(
        TaskVerificationFailed(
            task_id=task_id,
            verification_id=verification_id,
            failure=failure,
        ).model_dump(mode="python")
    )

    assert isinstance(planned, TaskVerificationPlanned)
    assert isinstance(failed, TaskVerificationFailed)
    assert failed.failure.category.value == "package"


def test_failure_classifier_uses_specific_categories() -> None:
    assert (
        classify_verification_failure("mypy: type error", exit_code=1).category.value
        == "typecheck"
    )
    assert (
        classify_verification_failure(
            "policy blocked command", exit_code=1
        ).category.value
        == "policy"
    )
    assert (
        classify_verification_failure("", exit_code=124, timed_out=True).category.value
        == "timeout"
    )
