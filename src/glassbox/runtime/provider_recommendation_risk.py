"""Risk, posture, reason, and unknown scoring for provider recommendations."""

from glassbox.core.types import AutonomyMode
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_recommendation_models import ProviderFailurePosture
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationConfidence,
)
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationEvidence,
)
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationPosture,
)
from glassbox.runtime.provider_recommendation_models import ProviderRiskPosture
from glassbox.runtime.provider_recommendation_models import ProviderTaskKind


def provider_recommendation_reasons(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> tuple[list[str], list[str]]:
    """Build stable operator-facing recommendation reasons and warnings."""

    reasons = [
        f"selected model source resolved to {diagnostics.selected_model_source}",
        (
            f"task kind {task_kind.value} requires "
            f"{', '.join(evidence.relevant_scenarios)} evidence"
        ),
        f"autonomy mode is {autonomy_mode.value}",
    ]
    warnings: list[str] = []
    if diagnostics.runtime_mode == "local":
        reasons.append("deterministic local runtime remains valid for offline work")
        if autonomy_mode != AutonomyMode.MANUAL:
            warnings.append(
                "local fallback does not exercise live provider tool-call behavior"
            )
    elif diagnostics.state != "ready":
        warnings.append(f"provider diagnostics state is {diagnostics.state}")
    if evidence.canary_status == "missing" or evidence.freshness_status == "missing":
        warnings.append(
            "provider evidence is missing; run provider canaries before relying "
            "on live-provider confidence"
        )
    elif evidence.canary_status == "skipped":
        warnings.append("provider canary evidence was skipped and remains advisory")
    if evidence.freshness_status == "stale":
        warnings.append(
            "provider evidence is stale; refresh retained canary evidence before "
            "long-running work"
        )
    elif evidence.freshness_status != "fresh":
        warnings.append(f"provider evidence freshness is {evidence.freshness_status}")
    if evidence.model_identity_matches_config is False:
        warnings.append("retained provider evidence was captured for a different model")
    if evidence.relevant_skipped_or_missing:
        warnings.append(
            "missing relevant scenario evidence: "
            + ", ".join(evidence.relevant_skipped_or_missing)
        )
    if evidence.relevant_preflight:
        warnings.append(
            "partial provider evidence: preflight-only scenarios are "
            + ", ".join(evidence.relevant_preflight)
        )
    if evidence.relevant_passed:
        reasons.append(
            "observed passed scenarios: " + ", ".join(evidence.relevant_passed)
        )
    if evidence.relevant_preflight:
        reasons.append(
            "preflight-only scenarios: " + ", ".join(evidence.relevant_preflight)
        )
    if failure_posture.state != "none":
        warnings.append(f"current provider failure posture is {failure_posture.state}")
    if failure_posture.state in {"blocked", "degraded", "repeated_failure"}:
        warnings.append(
            "known provider failure posture requires inspection before provider "
            "or model changes"
        )
    return reasons, warnings


def provider_posture_and_confidence(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> tuple[ProviderRecommendationPosture, ProviderRecommendationConfidence]:
    """Score provider recommendation posture and confidence."""

    if failure_posture.state in {"blocked", "degraded", "repeated_failure"}:
        return (
            ProviderRecommendationPosture.RISKY,
            ProviderRecommendationConfidence.LOW,
        )
    if diagnostics.runtime_mode == "local":
        confidence = (
            ProviderRecommendationConfidence.MEDIUM
            if task_kind == ProviderTaskKind.INSPECTION
            and autonomy_mode == AutonomyMode.MANUAL
            else ProviderRecommendationConfidence.LOW
        )
        return ProviderRecommendationPosture.LOCAL_FALLBACK, confidence
    if diagnostics.state != "ready":
        return (
            ProviderRecommendationPosture.RISKY,
            ProviderRecommendationConfidence.LOW,
        )
    if evidence.model_identity_matches_config is False:
        return (
            ProviderRecommendationPosture.RISKY,
            ProviderRecommendationConfidence.LOW,
        )
    if evidence.freshness_status in {"stale", "incompatible", "failed"}:
        return (
            ProviderRecommendationPosture.RISKY,
            ProviderRecommendationConfidence.LOW,
        )
    if (
        evidence.canary_status == "passed"
        and not evidence.canary_stale
        and not evidence.relevant_skipped_or_missing
        and len(evidence.relevant_passed) == len(evidence.relevant_scenarios)
    ):
        return (
            ProviderRecommendationPosture.RECOMMENDED,
            ProviderRecommendationConfidence.HIGH,
        )
    if evidence.relevant_passed and not evidence.canary_stale:
        return (
            ProviderRecommendationPosture.USABLE,
            ProviderRecommendationConfidence.MEDIUM,
        )
    if evidence.relevant_preflight and evidence.canary_status != "missing":
        return (
            ProviderRecommendationPosture.USABLE,
            ProviderRecommendationConfidence.MEDIUM,
        )
    return ProviderRecommendationPosture.RISKY, ProviderRecommendationConfidence.LOW


def provider_risk_posture(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
) -> ProviderRiskPosture:
    """Score risk for using the selected provider in the workflow."""

    if failure_posture.state in {"blocked", "degraded", "repeated_failure"}:
        return ProviderRiskPosture.HIGH
    if failure_posture.state == "retryable":
        return ProviderRiskPosture.MEDIUM
    if diagnostics.state in {
        "local_fallback",
        "missing_credentials",
        "unsupported_model",
        "invalid_workspace_profile",
        "invalid_provider_config",
    }:
        return ProviderRiskPosture.HIGH
    if diagnostics.runtime_mode == "local":
        return ProviderRiskPosture.MEDIUM
    if evidence.model_identity_matches_config is False:
        return ProviderRiskPosture.HIGH
    if evidence.freshness_status in {"stale", "incompatible", "failed"}:
        return ProviderRiskPosture.HIGH
    if evidence.freshness_status in {"missing", "credentialless", "warning"}:
        return ProviderRiskPosture.MEDIUM
    if evidence.relevant_preflight:
        return ProviderRiskPosture.MEDIUM
    if evidence.relevant_skipped_or_missing:
        return ProviderRiskPosture.MEDIUM
    return ProviderRiskPosture.LOW


def provider_recommendation_unknowns(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
    """Build stable operator-facing unknowns for provider recommendations."""

    unknowns: list[str] = []
    if diagnostics.state != "ready":
        unknowns.append(f"provider diagnostics state is {diagnostics.state}")
    if evidence.freshness_status in {"missing", "stale", "incompatible"}:
        unknowns.append(f"provider evidence freshness is {evidence.freshness_status}")
    if evidence.model_identity_matches_config is False:
        unknowns.append("retained canary evidence does not match the selected model")
    if evidence.relevant_skipped_or_missing:
        unknowns.append(
            "scenario coverage is missing for "
            + ", ".join(evidence.relevant_skipped_or_missing)
        )
    if evidence.relevant_preflight:
        unknowns.append(
            "scenario coverage is preflight-only for "
            + ", ".join(evidence.relevant_preflight)
        )
    if task_kind == ProviderTaskKind.BACKGROUND or autonomy_mode in {
        AutonomyMode.AUTONOMOUS_LOCAL,
        AutonomyMode.RELEASE_CANDIDATE,
    }:
        unknowns.append("live provider behavior remains advisory for long-running work")
    if failure_posture.state == "repeated_failure":
        unknowns.append("repeated provider failures may indicate provider degradation")
    if failure_posture.state == "blocked":
        unknowns.append("latest provider recovery evidence says continuation is unsafe")
    return unknowns
