"""Verification posture and recommendations for branch-search decisions."""

from pathlib import Path

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchSearchRecord
from glassbox.runtime.branch_decision_models import (
    BranchCandidateVerificationRecommendation,
)
from glassbox.runtime.branch_decision_models import BranchPosture
from glassbox.runtime.eval_recommendation_engine import recommend_eval_change_impact


def verification_posture(
    verification_status: BranchCandidateVerificationStatus,
) -> BranchPosture:
    if verification_status == BranchCandidateVerificationStatus.PASSED:
        return "strong"
    if verification_status in {
        BranchCandidateVerificationStatus.FAILED,
        BranchCandidateVerificationStatus.TIMED_OUT,
    }:
        return "risky"
    if verification_status == BranchCandidateVerificationStatus.BLOCKED:
        return "blocked"
    if verification_status == BranchCandidateVerificationStatus.INCONCLUSIVE:
        return "review"
    return "unknown"


def verification_recommendations(
    *,
    search: BranchSearchRecord,
    candidate: BranchCandidateRecord,
    changed_files: list[str],
    workspace_root: Path | None,
) -> list[BranchCandidateVerificationRecommendation]:
    if changed_files and workspace_root is not None:
        report = recommend_eval_change_impact(
            workspace_root,
            touched_paths=changed_files,
        )
        commands = _dedupe(
            [
                *(
                    [report.cheapest_next_command]
                    if report.cheapest_next_command
                    else []
                ),
                *[command for recipe in report.recipes for command in recipe.commands],
                *report.suggested_commands,
            ]
        )
        return [
            BranchCandidateVerificationRecommendation(
                source="changed-files",
                rationale=(
                    "Candidate changed files matched repository verification "
                    "recommendations."
                ),
                commands=commands,
                recipe_ids=[recipe.recipe_id for recipe in report.recipes],
                case_ids=[case.case_id for case in report.cases],
                profile_ids=[profile.profile_id for profile in report.profiles],
                warnings=report.warnings,
            )
        ]
    if candidate.verification_status == BranchCandidateVerificationStatus.PASSED:
        return [
            BranchCandidateVerificationRecommendation(
                source="existing-evidence",
                rationale=(
                    "Candidate already has passed verification evidence; inspect "
                    "the retained summary before selection."
                ),
            )
        ]
    return [
        BranchCandidateVerificationRecommendation(
            source="missing-changed-files",
            rationale=(
                f"Branch search {search.search_id} does not retain changed-file "
                "evidence for this candidate yet; inspect the candidate session "
                "and run focused verification before selecting it."
            ),
        )
    ]


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


__all__ = [
    "verification_posture",
    "verification_recommendations",
]
