"""Tests for executable eval recommendation verification plans."""

from pathlib import Path

from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_verification import build_eval_verification_plan


def test_eval_recommendations_convert_to_verification_entries(tmp_path: Path) -> None:
    report = EvalRecommendationReport(
        workspace_root=tmp_path,
        touched_paths=["src/glassbox/runtime/replay.py"],
        cases=[
            EvalCaseRecommendation(
                case_id="smoke.hello",
                title="Smoke",
                confidence="direct",
                reasons=[
                    EvalRecommendationReason(
                        confidence="direct",
                        group="direct-path",
                        summary="runtime replay path matched smoke.hello",
                    )
                ],
            )
        ],
        profiles=[
            EvalProfileRecommendation(
                profile_id="commit-smoke",
                title="Commit smoke",
                confidence="stage-derived",
                verification_stage="commit-time",
                track="deterministic",
                blocking=True,
            )
        ],
    )

    plan = build_eval_verification_plan(report)

    assert [entry.eval_profile_id for entry in plan.plan_entries] == [
        "commit-smoke",
        None,
    ]
    assert plan.plan_entries[1].eval_case_id == "smoke.hello"
    assert "smoke.hello" in plan.plan_entries[1].command


def test_eval_verification_plan_skips_fallback_and_canary_by_default(
    tmp_path: Path,
) -> None:
    report = EvalRecommendationReport(
        workspace_root=tmp_path,
        profiles=[
            EvalProfileRecommendation(
                profile_id="provider-canary",
                title="Provider canary",
                confidence="direct",
                verification_stage="advisory",
                track="live-provider-canary",
                blocking=False,
            )
        ],
        cases=[
            EvalCaseRecommendation(
                case_id="maybe.case",
                title="Maybe",
                confidence="fallback",
            )
        ],
    )

    plan = build_eval_verification_plan(report)

    assert plan.plan_entries == []
    assert {skipped.target_id for skipped in plan.skipped_checks} == {
        "provider-canary",
        "maybe.case",
    }
