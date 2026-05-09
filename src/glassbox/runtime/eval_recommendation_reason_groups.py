"""Reason-group construction for eval recommendation reports."""

from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReasonGroup
from glassbox.runtime.eval_recommendation_models import (
    EvalRecommendationReasonGroupKind,
)
from glassbox.runtime.eval_recommendation_models import EvalReleaseSurfaceRecommendation


def build_reason_groups(
    *,
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    release_surfaces: list[EvalReleaseSurfaceRecommendation],
) -> list[EvalRecommendationReasonGroup]:
    groups: dict[EvalRecommendationReasonGroupKind, EvalRecommendationReasonGroup] = {}
    for case in case_recommendations:
        for reason in case.reasons:
            group = _ensure_reason_group(groups, reason.group)
            _append_unique(group.summaries, reason.summary)
            _append_optional_unique(group.matched_paths, reason.matched_path)
            _append_optional_unique(group.rule_ids, reason.rule_id)
            _append_unique(group.recommended_case_ids, case.case_id)

    for profile in profile_recommendations:
        for reason in profile.reasons:
            group = _ensure_reason_group(groups, reason.group)
            _append_unique(group.summaries, reason.summary)
            _append_optional_unique(group.matched_paths, reason.matched_path)
            _append_optional_unique(group.rule_ids, reason.rule_id)
            _append_unique(group.recommended_profile_ids, profile.profile_id)

    release_gate_commands: list[str] = []
    release_gate_summaries: list[str] = []
    for surface in release_surfaces:
        for command in surface.release_gate_commands:
            _append_unique(release_gate_commands, command)
        for note in surface.release_gate_notes:
            _append_unique(release_gate_summaries, note)
    if release_gate_commands:
        group = _ensure_reason_group(groups, "release-gate-recommendation")
        for command in release_gate_commands:
            _append_unique(group.release_gate_commands, command)
        for summary in release_gate_summaries:
            _append_unique(group.summaries, summary)

    return [
        groups[group]
        for group in (
            "direct-path",
            "owner-derived-rule",
            "capability-derived-rule",
            "repository-intelligence",
            "stage-derived-profile",
            "release-gate-recommendation",
            "fallback-policy",
        )
        if group in groups
    ]


def _ensure_reason_group(
    groups: dict[EvalRecommendationReasonGroupKind, EvalRecommendationReasonGroup],
    group: EvalRecommendationReasonGroupKind,
) -> EvalRecommendationReasonGroup:
    existing = groups.get(group)
    if existing is not None:
        return existing
    created = EvalRecommendationReasonGroup(
        group=group,
        title=_reason_group_title(group),
    )
    groups[group] = created
    return created


def _reason_group_title(group: EvalRecommendationReasonGroupKind) -> str:
    if group == "direct-path":
        return "Direct path matches"
    if group == "owner-derived-rule":
        return "Owner-derived rule matches"
    if group == "capability-derived-rule":
        return "Capability-derived rule matches"
    if group == "repository-intelligence":
        return "Repository intelligence matches"
    if group == "stage-derived-profile":
        return "Stage-derived profile matches"
    if group == "release-gate-recommendation":
        return "Release gate recommendations"
    return "Fallback policy guidance"


def _append_optional_unique(values: list[str], value: str | None) -> None:
    if value is not None:
        _append_unique(values, value)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
