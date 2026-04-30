"""Provider-aware model recommendation helpers."""

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.types import AutonomyMode
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.provider_canary import ProviderCanarySummary
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME


class ProviderTaskKind(StrEnum):
    """Workflow categories used for provider recommendations."""

    INSPECTION = "inspection"
    CODING = "coding"
    VERIFICATION = "verification"
    BRANCH_SEARCH = "branch-search"
    BACKGROUND = "background"
    RELEASE = "release"


class ProviderRecommendationConfidence(StrEnum):
    """Confidence levels for advisory provider recommendations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProviderRecommendationPosture(StrEnum):
    """Recommendation posture for the selected provider/model."""

    RECOMMENDED = "recommended"
    USABLE = "usable"
    RISKY = "risky"
    LOCAL_FALLBACK = "local_fallback"


class ProviderCapabilityFit(StrEnum):
    """How well retained evidence covers the workflow capabilities."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class ProviderRiskPosture(StrEnum):
    """Risk posture for using the selected provider in the workflow."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ProviderCredentialReadiness(StrEnum):
    """Credential readiness for provider-backed work."""

    READY = "ready"
    MISSING = "missing"
    NOT_REQUIRED = "not_required"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class ProviderRecommendationEvidence(BaseModel):
    """Evidence inputs used for one recommendation."""

    model_config = ConfigDict(extra="forbid")

    diagnostics_state: str
    runtime_mode: str
    canary_status: str
    freshness_status: str
    canary_stale: bool = False
    model_identity_matches_config: bool | None = None
    scenario_count: int = 0
    matrix_entry_count: int = 0
    relevant_scenarios: list[str] = Field(default_factory=list)
    relevant_passed: list[str] = Field(default_factory=list)
    relevant_preflight: list[str] = Field(default_factory=list)
    relevant_skipped_or_missing: list[str] = Field(default_factory=list)


class ProviderRecommendation(BaseModel):
    """Non-authoritative provider/model recommendation for a workflow."""

    model_config = ConfigDict(extra="forbid")

    advisory: bool = True
    auto_applied: bool = False
    task_kind: ProviderTaskKind
    autonomy_mode: AutonomyMode
    recommended_model_name: str
    provider: str
    posture: ProviderRecommendationPosture
    confidence: ProviderRecommendationConfidence
    capability_fit: ProviderCapabilityFit
    risk_posture: ProviderRiskPosture
    evidence_freshness: str
    credential_readiness: ProviderCredentialReadiness
    required_capabilities: list[str]
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence: ProviderRecommendationEvidence
    next_actions: list[str] = Field(default_factory=list)


_TASK_SCENARIOS: dict[ProviderTaskKind, list[str]] = {
    ProviderTaskKind.INSPECTION: ["streaming-text", "long-context-continuity"],
    ProviderTaskKind.CODING: [
        "streaming-text",
        "tool-call",
        "tool-call-streaming",
        "multi-step-plan-following",
    ],
    ProviderTaskKind.VERIFICATION: [
        "tool-call",
        "verification-loop-interaction",
        "retry-behavior",
    ],
    ProviderTaskKind.BRANCH_SEARCH: [
        "tool-call",
        "multi-step-plan-following",
        "verification-loop-interaction",
    ],
    ProviderTaskKind.BACKGROUND: [
        "streaming-text",
        "retry-behavior",
        "cancellation-during-retry",
    ],
    ProviderTaskKind.RELEASE: [
        "streaming-text",
        "tool-call",
        "verification-loop-interaction",
        "rate-limit-handling",
    ],
}


def recommend_provider(
    workspace_root: Path,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
    model_name: str | None = None,
) -> ProviderRecommendation:
    """Build a non-authoritative provider recommendation for a workflow."""

    diagnostics = build_provider_diagnostics_report(
        workspace_root,
        explicit_model_name=model_name,
    )
    evidence = load_provider_canary_evidence(
        workspace_root,
        expected_model_name=model_name,
    )
    summary = _load_latest_summary(evidence)
    relevant_scenarios = _workflow_scenarios(task_kind, autonomy_mode)
    recommendation_evidence = _recommendation_evidence(
        diagnostics,
        evidence,
        summary,
        relevant_scenarios,
    )
    required_capabilities = _required_capabilities(task_kind, autonomy_mode)
    reasons, warnings = _recommendation_reasons(
        diagnostics,
        recommendation_evidence,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    posture, confidence = _posture_and_confidence(
        diagnostics,
        recommendation_evidence,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    capability_fit = _capability_fit(diagnostics, recommendation_evidence)
    risk_posture = _risk_posture(diagnostics, recommendation_evidence)
    credential_readiness = _credential_readiness(diagnostics)
    unknowns = _recommendation_unknowns(
        diagnostics,
        recommendation_evidence,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    selected_model = diagnostics.selected_model_name or model_name or DEFAULT_MODEL_NAME
    return ProviderRecommendation(
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
        recommended_model_name=selected_model,
        provider=diagnostics.selected_provider,
        posture=posture,
        confidence=confidence,
        capability_fit=capability_fit,
        risk_posture=risk_posture,
        evidence_freshness=evidence.freshness_status,
        credential_readiness=credential_readiness,
        required_capabilities=required_capabilities,
        reasons=reasons,
        warnings=warnings,
        unknowns=unknowns,
        evidence=recommendation_evidence,
        next_actions=[*diagnostics.next_actions, *evidence.next_actions],
    )


def _load_latest_summary(
    evidence: ProviderCanaryEvidenceSummary,
) -> ProviderCanarySummary | None:
    if evidence.latest_summary_path is None:
        return None
    path = Path(evidence.latest_summary_path)
    try:
        return ProviderCanarySummary.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except OSError, ValueError, json.JSONDecodeError:
        return None


def _recommendation_evidence(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderCanaryEvidenceSummary,
    summary: ProviderCanarySummary | None,
    relevant_scenarios: list[str],
) -> ProviderRecommendationEvidence:
    passed: list[str] = []
    preflight: list[str] = []
    skipped_or_missing = list(relevant_scenarios)
    if summary is not None and evidence.identity_matches_current_config is not False:
        rows = {entry.scenario_id: entry for entry in summary.capability_matrix.entries}
        skipped_or_missing = []
        for scenario_id in relevant_scenarios:
            row = rows.get(scenario_id)
            if row is None:
                skipped_or_missing.append(scenario_id)
            elif row.scenario_confidence == "observed" and row.result == "passed":
                passed.append(scenario_id)
            elif row.scenario_confidence == "preflight":
                preflight.append(scenario_id)
            else:
                skipped_or_missing.append(scenario_id)

    return ProviderRecommendationEvidence(
        diagnostics_state=diagnostics.state,
        runtime_mode=diagnostics.runtime_mode,
        canary_status=evidence.latest_status,
        freshness_status=evidence.freshness_status,
        canary_stale=evidence.stale,
        model_identity_matches_config=evidence.identity_matches_current_config,
        scenario_count=evidence.scenario_count,
        matrix_entry_count=evidence.matrix_entry_count,
        relevant_scenarios=list(relevant_scenarios),
        relevant_passed=passed,
        relevant_preflight=preflight,
        relevant_skipped_or_missing=skipped_or_missing,
    )


def _required_capabilities(
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
    capabilities = ["streaming text"]
    if task_kind in {
        ProviderTaskKind.CODING,
        ProviderTaskKind.VERIFICATION,
        ProviderTaskKind.BRANCH_SEARCH,
        ProviderTaskKind.RELEASE,
    }:
        capabilities.append("reliable tool calls")
    if autonomy_mode in {
        AutonomyMode.TEST_DRIVEN,
        AutonomyMode.AUTONOMOUS_LOCAL,
        AutonomyMode.RELEASE_CANDIDATE,
    }:
        capabilities.append("retry and cancellation posture")
    if task_kind in {ProviderTaskKind.VERIFICATION, ProviderTaskKind.RELEASE}:
        capabilities.append("verification-loop interaction")
    if task_kind == ProviderTaskKind.BRANCH_SEARCH:
        capabilities.append("multi-step plan following")
    return capabilities


def _workflow_scenarios(
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
    if (
        autonomy_mode == AutonomyMode.INSPECT
        or task_kind == ProviderTaskKind.INSPECTION
    ):
        return ["streaming-text", "long-context-continuity"]
    if autonomy_mode == AutonomyMode.EDIT_SAFE:
        return [
            "streaming-text",
            "tool-call",
            "tool-call-streaming",
            "multi-step-plan-following",
        ]
    if autonomy_mode == AutonomyMode.TEST_DRIVEN:
        return [
            "streaming-text",
            "tool-call",
            "verification-loop-interaction",
            "retry-behavior",
        ]
    if (
        autonomy_mode == AutonomyMode.RELEASE_CANDIDATE
        or task_kind == ProviderTaskKind.RELEASE
    ):
        return [
            "streaming-text",
            "tool-call",
            "verification-loop-interaction",
            "rate-limit-handling",
            "retry-behavior",
        ]
    if (
        autonomy_mode == AutonomyMode.AUTONOMOUS_LOCAL
        or task_kind == ProviderTaskKind.BACKGROUND
    ):
        return [
            "streaming-text",
            "retry-behavior",
            "cancellation-during-retry",
            "multi-step-plan-following",
        ]
    return _TASK_SCENARIOS[task_kind]


def _recommendation_reasons(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> tuple[list[str], list[str]]:
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
    if evidence.canary_status in {"missing", "skipped"}:
        warnings.append("provider canary evidence is missing or skipped")
    if evidence.freshness_status != "fresh":
        warnings.append(f"provider evidence freshness is {evidence.freshness_status}")
    if evidence.model_identity_matches_config is False:
        warnings.append("retained provider evidence was captured for a different model")
    if evidence.relevant_skipped_or_missing:
        warnings.append(
            "missing relevant scenario evidence: "
            + ", ".join(evidence.relevant_skipped_or_missing)
        )
    if evidence.relevant_passed:
        reasons.append(
            "observed passed scenarios: " + ", ".join(evidence.relevant_passed)
        )
    if evidence.relevant_preflight:
        reasons.append(
            "preflight-only scenarios: " + ", ".join(evidence.relevant_preflight)
        )
    return reasons, warnings


def _posture_and_confidence(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> tuple[ProviderRecommendationPosture, ProviderRecommendationConfidence]:
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


def _capability_fit(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
) -> ProviderCapabilityFit:
    if diagnostics.state != "ready":
        return ProviderCapabilityFit.INSUFFICIENT
    if evidence.model_identity_matches_config is False:
        return ProviderCapabilityFit.UNKNOWN
    if evidence.freshness_status in {"missing", "stale", "incompatible", "failed"}:
        return ProviderCapabilityFit.UNKNOWN
    if not evidence.relevant_skipped_or_missing and evidence.relevant_scenarios:
        if len(evidence.relevant_passed) == len(evidence.relevant_scenarios):
            return ProviderCapabilityFit.SUPPORTED
        if len(evidence.relevant_passed) + len(evidence.relevant_preflight) == len(
            evidence.relevant_scenarios
        ):
            return ProviderCapabilityFit.PARTIAL
    if evidence.relevant_passed or evidence.relevant_preflight:
        return ProviderCapabilityFit.PARTIAL
    return ProviderCapabilityFit.UNKNOWN


def _risk_posture(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
) -> ProviderRiskPosture:
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


def _credential_readiness(
    diagnostics: ProviderDiagnosticsReport,
) -> ProviderCredentialReadiness:
    if diagnostics.runtime_mode == "local":
        return ProviderCredentialReadiness.NOT_REQUIRED
    if diagnostics.state == "ready":
        return ProviderCredentialReadiness.READY
    if diagnostics.state in {"missing_credentials", "local_fallback"}:
        return ProviderCredentialReadiness.MISSING
    if diagnostics.state == "unsupported_model":
        return ProviderCredentialReadiness.UNSUPPORTED
    if diagnostics.state in {"invalid_workspace_profile", "invalid_provider_config"}:
        return ProviderCredentialReadiness.INVALID
    return ProviderCredentialReadiness.UNKNOWN


def _recommendation_unknowns(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
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
    return unknowns
