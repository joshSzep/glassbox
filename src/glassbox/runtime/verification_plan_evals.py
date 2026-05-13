"""Verification-plan entries derived from eval and release recommendations."""

from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview
from glassbox.runtime.changeset_verification_preview import is_safe_verification_command
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.verification_plan_entries import build_verification_entry
from glassbox.runtime.verification_plan_entries import command_parts
from glassbox.runtime.verification_plan_entries import join_reasons
from glassbox.runtime.verification_plan_manual import build_manual_only_profile_entry
from glassbox.runtime.verification_plan_skips import (
    operator_selection_required_skipped_row,
)


def build_eval_verification_entries(
    recommendation: EvalRecommendationReport,
    *,
    changed_paths: list[str],
) -> tuple[list[VerificationPlanEntry], list[ChangesetVerificationSkippedCheckPreview]]:
    """Build eval profile, eval case, and release surface plan entries."""

    entries: list[VerificationPlanEntry] = []
    skipped: list[ChangesetVerificationSkippedCheckPreview] = []
    for profile in recommendation.profiles:
        if profile.track != "deterministic":
            skipped.append(
                operator_selection_required_skipped_row(
                    target_id=profile.profile_id,
                    track=profile.track,
                    matched_paths=profile.matched_paths,
                    safe_next_actions=profile.safe_next_commands,
                )
            )
            entries.append(
                build_manual_only_profile_entry(profile, changed_paths=changed_paths)
            )
            continue
        command = (
            profile.safe_next_commands[0]
            if profile.safe_next_commands
            else f"uv run glassbox eval run --profile {profile.profile_id} --cwd ."
        )
        entries.append(
            build_verification_entry(
                seed=f"eval-profile:{profile.profile_id}:{command}",
                check_name=f"Eval profile {profile.profile_id}",
                kind=VerificationCheckKind.EVAL,
                command=command_parts(command),
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                target_id=profile.profile_id,
                target_label=profile.title,
                rationale=join_reasons(
                    [reason.summary for reason in profile.reasons],
                    fallback="Eval recommendation selected this profile.",
                ),
                selection_rationale=(
                    f"{profile.confidence} confidence for "
                    f"{profile.verification_stage} verification"
                ),
                blocking=profile.blocking,
                changed_paths=profile.matched_paths or changed_paths,
                eval_profile_id=profile.profile_id,
                release_surfaces=[profile.verification_stage],
            )
        )
    for case in recommendation.cases:
        command = f"uv run glassbox eval run {case.case_id} --cwd ."
        entries.append(
            build_verification_entry(
                seed=f"eval-case:{case.case_id}:{command}",
                check_name=f"Eval case {case.case_id}",
                kind=VerificationCheckKind.EVAL,
                command=command_parts(command),
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                target_id=case.case_id,
                target_label=case.title,
                rationale=join_reasons(
                    [reason.summary for reason in case.reasons],
                    fallback="Eval recommendation selected this case.",
                ),
                selection_rationale=f"{case.confidence} confidence eval case",
                changed_paths=case.matched_paths or changed_paths,
                eval_case_id=case.case_id,
            )
        )
    for surface in recommendation.release_surfaces:
        if not surface.impacted:
            continue
        for command in surface.release_gate_commands:
            if not is_safe_verification_command(command):
                continue
            entries.append(
                build_verification_entry(
                    seed=f"release:{surface.verification_stage}:{command}",
                    check_name=f"{surface.verification_stage} release gate",
                    kind=VerificationCheckKind.PACKAGE,
                    command=command_parts(command),
                    source=VerificationPlanSource.RELEASE_GATE,
                    target_id=f"release:{surface.verification_stage}",
                    target_label=f"{surface.verification_stage} release surface",
                    rationale=(
                        "Changed paths affect this release verification surface."
                    ),
                    selection_rationale="release surface impact",
                    changed_paths=changed_paths,
                    release_surfaces=[surface.verification_stage],
                )
            )
    return entries, skipped


__all__ = ["build_eval_verification_entries"]
