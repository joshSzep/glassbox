"""Provider-aware model recommendation helpers."""

import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models import ProviderRecoveryRecord
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


class ProviderRecommendedAction(StrEnum):
    """Concrete advisory action for continuing after provider posture changes."""

    CONTINUE = "continue"
    RETRY = "retry"
    PAUSE = "pause"
    SWITCH_PROVIDER = "switch_provider"
    LOCAL_FALLBACK = "local_fallback"
    FIX_CREDENTIALS = "fix_credentials"
    REFRESH_EVIDENCE = "refresh_evidence"


class ProviderFailurePosture(BaseModel):
    """Latest provider recovery evidence folded into recommendations."""

    model_config = ConfigDict(extra="forbid")

    state: str
    provider: str | None = None
    model_name: str | None = None
    failure_kind: str | None = None
    recovery_action: str | None = None
    retryable: bool = False
    safe_to_continue: bool | None = None
    degraded: bool = False
    repeated_failure_count: int = 0
    latest_reason: str | None = None
    operator_next_action: str | None = None


class ProviderBudgetImpact(BaseModel):
    """Budget-relevant retry and pause impact for advisory recommendations."""

    model_config = ConfigDict(extra="forbid")

    retry_delay_seconds: int | None = None
    retry_attempt: int | None = None
    max_attempts: int | None = None
    next_retry_at: str | None = None
    budget_warning: str | None = None


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
    recommended_action: ProviderRecommendedAction
    failure_posture: ProviderFailurePosture
    budget_impact: ProviderBudgetImpact
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
    provider_recovery_history: Sequence[ProviderRecoveryRecord] | None = None,
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
    recovery_history = list(provider_recovery_history or [])
    failure_posture = _failure_posture(recovery_history)
    budget_impact = _budget_impact(recovery_history)
    required_capabilities = _required_capabilities(task_kind, autonomy_mode)
    reasons, warnings = _recommendation_reasons(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    posture, confidence = _posture_and_confidence(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    capability_fit = _capability_fit(
        diagnostics,
        recommendation_evidence,
        failure_posture,
    )
    risk_posture = _risk_posture(diagnostics, recommendation_evidence, failure_posture)
    credential_readiness = _credential_readiness(diagnostics)
    unknowns = _recommendation_unknowns(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    recommended_action = _recommended_action(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        credential_readiness,
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
        recommended_action=recommended_action,
        failure_posture=failure_posture,
        budget_impact=budget_impact,
        required_capabilities=required_capabilities,
        reasons=reasons,
        warnings=warnings,
        unknowns=unknowns,
        evidence=recommendation_evidence,
        next_actions=[
            *_action_next_steps(recommended_action, failure_posture),
            *diagnostics.next_actions,
            *evidence.next_actions,
        ],
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
    failure_posture: ProviderFailurePosture,
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
    if failure_posture.state != "none":
        warnings.append(f"current provider failure posture is {failure_posture.state}")
    return reasons, warnings


def _posture_and_confidence(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    *,
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> tuple[ProviderRecommendationPosture, ProviderRecommendationConfidence]:
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


def _capability_fit(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
) -> ProviderCapabilityFit:
    if failure_posture.state in {"degraded", "repeated_failure"}:
        return ProviderCapabilityFit.INSUFFICIENT
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
    failure_posture: ProviderFailurePosture,
) -> ProviderRiskPosture:
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
    failure_posture: ProviderFailurePosture,
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
    if failure_posture.state == "repeated_failure":
        unknowns.append("repeated provider failures may indicate provider degradation")
    if failure_posture.state == "blocked":
        unknowns.append("latest provider recovery evidence says continuation is unsafe")
    return unknowns


def _failure_posture(
    recovery_history: Sequence[ProviderRecoveryRecord],
) -> ProviderFailurePosture:
    if not recovery_history:
        return ProviderFailurePosture(state="none")
    latest = recovery_history[0]
    repeated_count = sum(
        1 for record in recovery_history if record.provider == latest.provider
    )
    if repeated_count >= 2:
        state = "repeated_failure"
    elif latest.degraded:
        state = "degraded"
    elif latest.retryable and latest.safe_to_continue:
        state = "retryable"
    elif latest.safe_to_continue is False:
        state = "blocked"
    else:
        state = "unknown"
    return ProviderFailurePosture(
        state=state,
        provider=latest.provider,
        model_name=latest.model_name,
        failure_kind=latest.failure_kind.value,
        recovery_action=latest.action.value,
        retryable=latest.retryable,
        safe_to_continue=latest.safe_to_continue,
        degraded=latest.degraded,
        repeated_failure_count=repeated_count,
        latest_reason=latest.reason,
        operator_next_action=latest.operator_next_action,
    )


def _budget_impact(
    recovery_history: Sequence[ProviderRecoveryRecord],
) -> ProviderBudgetImpact:
    if not recovery_history:
        return ProviderBudgetImpact()
    latest = recovery_history[0]
    warning = None
    if latest.backoff_seconds is not None:
        warning = "retry delay consumes provider retry budget and wall-clock budget"
    if latest.max_attempts is not None and latest.attempt >= latest.max_attempts:
        warning = "provider retry attempts are exhausted; pause before retrying"
    return ProviderBudgetImpact(
        retry_delay_seconds=latest.backoff_seconds,
        retry_attempt=latest.attempt,
        max_attempts=latest.max_attempts,
        next_retry_at=latest.next_retry_at.isoformat()
        if latest.next_retry_at
        else None,
        budget_warning=warning,
    )


def _recommended_action(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
    credential_readiness: ProviderCredentialReadiness,
) -> ProviderRecommendedAction:
    if credential_readiness == ProviderCredentialReadiness.MISSING:
        return ProviderRecommendedAction.FIX_CREDENTIALS
    if diagnostics.state == "unsupported_model":
        return ProviderRecommendedAction.LOCAL_FALLBACK
    if diagnostics.runtime_mode == "local":
        return ProviderRecommendedAction.LOCAL_FALLBACK
    if failure_posture.state == "retryable":
        return ProviderRecommendedAction.RETRY
    if failure_posture.state in {"degraded", "repeated_failure"}:
        return ProviderRecommendedAction.SWITCH_PROVIDER
    if failure_posture.state == "blocked":
        return ProviderRecommendedAction.PAUSE
    if evidence.freshness_status in {"missing", "stale", "incompatible", "failed"}:
        return ProviderRecommendedAction.REFRESH_EVIDENCE
    return ProviderRecommendedAction.CONTINUE


def _action_next_steps(
    action: ProviderRecommendedAction,
    failure_posture: ProviderFailurePosture,
) -> list[str]:
    if action == ProviderRecommendedAction.RETRY:
        return [
            "retry the provider call only within the configured autonomy "
            "and retry budget"
        ]
    if action == ProviderRecommendedAction.PAUSE:
        return [
            "pause long-running work and inspect the latest checkpoint before retrying"
        ]
    if action == ProviderRecommendedAction.SWITCH_PROVIDER:
        return [
            "pause work, run provider diagnostics, then choose an operator-approved "
            "provider switch or model switch"
        ]
    if action == ProviderRecommendedAction.LOCAL_FALLBACK:
        return [
            "use an unprefixed local model only for deterministic local work "
            "that does not require live-provider capabilities"
        ]
    if action == ProviderRecommendedAction.FIX_CREDENTIALS:
        return ["fix provider credentials, then rerun provider diagnostics"]
    if action == ProviderRecommendedAction.REFRESH_EVIDENCE:
        return ["refresh provider canary evidence before relying on provider advice"]
    if failure_posture.operator_next_action is not None:
        return [failure_posture.operator_next_action]
    return ["continue with the selected provider; advice remains advisory"]
