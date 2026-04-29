"""Convert eval recommendations into executable verification plans."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_task_verification_id
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_runner_models import EvalSuiteResult


class EvalVerificationSkippedCheck(BaseModel):
    """Recommended eval check that was intentionally not planned."""

    model_config = ConfigDict(extra="forbid")

    target_type: str
    target_id: str
    reason: str


class EvalVerificationExecutedCheck(BaseModel):
    """Result from one executed eval verification plan entry."""

    model_config = ConfigDict(extra="forbid")

    check_name: str
    target_type: str
    target_id: str
    passed: bool
    exit_code: int = Field(ge=0)
    artifact_path: Path


class EvalVerificationPlanReport(BaseModel):
    """Recommendation-to-verification conversion report."""

    model_config = ConfigDict(extra="forbid")

    recommendation: EvalRecommendationReport
    plan_entries: list[VerificationPlanEntry] = Field(default_factory=list)
    skipped_checks: list[EvalVerificationSkippedCheck] = Field(default_factory=list)
    executed_checks: list[EvalVerificationExecutedCheck] = Field(default_factory=list)


def build_eval_verification_plan(
    recommendation: EvalRecommendationReport,
    *,
    include_low_confidence: bool = False,
    include_live_provider_canary: bool = False,
) -> EvalVerificationPlanReport:
    """Build explicit verification entries from eval recommendation rows."""

    entries: list[VerificationPlanEntry] = []
    skipped: list[EvalVerificationSkippedCheck] = []
    for profile in recommendation.profiles:
        if profile.track != "deterministic" and not include_live_provider_canary:
            skipped.append(
                EvalVerificationSkippedCheck(
                    target_type="profile",
                    target_id=profile.profile_id,
                    reason=("live-provider canary profiles require explicit selection"),
                )
            )
            continue
        if profile.confidence == "fallback" and not include_low_confidence:
            skipped.append(
                EvalVerificationSkippedCheck(
                    target_type="profile",
                    target_id=profile.profile_id,
                    reason="fallback-confidence recommendations remain optional",
                )
            )
            continue
        entries.append(
            VerificationPlanEntry(
                verification_id=new_task_verification_id(),
                check_name=f"eval profile {profile.profile_id}",
                kind=VerificationCheckKind.EVAL,
                command=[
                    "uv",
                    "run",
                    "glassbox",
                    "eval",
                    "run",
                    "--profile",
                    profile.profile_id,
                ],
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                rationale=_rationale([reason.summary for reason in profile.reasons]),
                blocking=profile.blocking,
                timeout_seconds=300,
                eval_profile_id=profile.profile_id,
            )
        )
    for case in recommendation.cases:
        if case.confidence == "fallback" and not include_low_confidence:
            skipped.append(
                EvalVerificationSkippedCheck(
                    target_type="case",
                    target_id=case.case_id,
                    reason="fallback-confidence recommendations remain optional",
                )
            )
            continue
        entries.append(
            VerificationPlanEntry(
                verification_id=new_task_verification_id(),
                check_name=f"eval case {case.case_id}",
                kind=VerificationCheckKind.EVAL,
                command=["uv", "run", "glassbox", "eval", "run", case.case_id],
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                rationale=_rationale([reason.summary for reason in case.reasons]),
                blocking=True,
                timeout_seconds=300,
                eval_case_id=case.case_id,
            )
        )
    return EvalVerificationPlanReport(
        recommendation=recommendation,
        plan_entries=entries,
        skipped_checks=skipped,
    )


def executed_check_from_suite_result(
    entry: VerificationPlanEntry,
    result: EvalSuiteResult,
) -> EvalVerificationExecutedCheck:
    """Summarize one executed eval suite as verification evidence."""

    target_type = "profile" if entry.eval_profile_id is not None else "case"
    target_id = entry.eval_profile_id or entry.eval_case_id or entry.check_name
    return EvalVerificationExecutedCheck(
        check_name=entry.check_name,
        target_type=target_type,
        target_id=target_id,
        passed=result.exit_code == 0,
        exit_code=result.exit_code,
        artifact_path=result.summary_path,
    )


def _rationale(reasons: list[str]) -> str:
    compact = [reason for reason in reasons if reason.strip()]
    if not compact:
        return "Selected by eval recommendation."
    return "; ".join(compact)[:2000]


__all__ = [
    "EvalVerificationExecutedCheck",
    "EvalVerificationPlanReport",
    "EvalVerificationSkippedCheck",
    "build_eval_verification_plan",
    "executed_check_from_suite_result",
]
