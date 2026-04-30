"""Provider-aware model recommendation facade and orchestration."""

from collections.abc import Sequence
from pathlib import Path

from glassbox.core.models import ProviderRecoveryRecord
from glassbox.core.types import AutonomyMode
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.provider_recommendation_actions import provider_action_next_steps
from glassbox.runtime.provider_recommendation_actions import provider_recommended_action
from glassbox.runtime.provider_recommendation_capability import (
    load_latest_provider_canary_summary,
)
from glassbox.runtime.provider_recommendation_capability import provider_capability_fit
from glassbox.runtime.provider_recommendation_capability import (
    provider_recommendation_evidence,
)
from glassbox.runtime.provider_recommendation_capability import (
    provider_workflow_scenarios,
)
from glassbox.runtime.provider_recommendation_capability import (
    required_provider_capabilities,
)
from glassbox.runtime.provider_recommendation_credentials import (
    provider_credential_readiness,
)
from glassbox.runtime.provider_recommendation_failures import provider_budget_impact
from glassbox.runtime.provider_recommendation_failures import provider_failure_posture
from glassbox.runtime.provider_recommendation_models import ProviderBudgetImpact
from glassbox.runtime.provider_recommendation_models import ProviderCapabilityFit
from glassbox.runtime.provider_recommendation_models import ProviderCredentialReadiness
from glassbox.runtime.provider_recommendation_models import ProviderFailurePosture
from glassbox.runtime.provider_recommendation_models import ProviderRecommendation
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationConfidence,
)
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationEvidence,
)
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationPosture,
)
from glassbox.runtime.provider_recommendation_models import ProviderRecommendedAction
from glassbox.runtime.provider_recommendation_models import ProviderRiskPosture
from glassbox.runtime.provider_recommendation_models import ProviderTaskKind
from glassbox.runtime.provider_recommendation_risk import (
    provider_posture_and_confidence,
)
from glassbox.runtime.provider_recommendation_risk import (
    provider_recommendation_reasons,
)
from glassbox.runtime.provider_recommendation_risk import (
    provider_recommendation_unknowns,
)
from glassbox.runtime.provider_recommendation_risk import provider_risk_posture
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME

__all__ = [
    "ProviderBudgetImpact",
    "ProviderCapabilityFit",
    "ProviderCredentialReadiness",
    "ProviderFailurePosture",
    "ProviderRecommendation",
    "ProviderRecommendationConfidence",
    "ProviderRecommendationEvidence",
    "ProviderRecommendationPosture",
    "ProviderRecommendedAction",
    "ProviderRiskPosture",
    "ProviderTaskKind",
    "recommend_provider",
]


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
    summary = load_latest_provider_canary_summary(evidence)
    relevant_scenarios = provider_workflow_scenarios(task_kind, autonomy_mode)
    recommendation_evidence = provider_recommendation_evidence(
        diagnostics,
        evidence,
        summary,
        relevant_scenarios,
    )
    recovery_history = list(provider_recovery_history or [])
    failure_posture = provider_failure_posture(recovery_history)
    budget_impact = provider_budget_impact(recovery_history)
    required_capabilities = required_provider_capabilities(task_kind, autonomy_mode)
    reasons, warnings = provider_recommendation_reasons(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    posture, confidence = provider_posture_and_confidence(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    capability_fit = provider_capability_fit(
        diagnostics,
        recommendation_evidence,
        failure_posture,
    )
    risk_posture = provider_risk_posture(
        diagnostics,
        recommendation_evidence,
        failure_posture,
    )
    credential_readiness = provider_credential_readiness(diagnostics)
    unknowns = provider_recommendation_unknowns(
        diagnostics,
        recommendation_evidence,
        failure_posture,
        task_kind=task_kind,
        autonomy_mode=autonomy_mode,
    )
    recommended_action = provider_recommended_action(
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
            *provider_action_next_steps(recommended_action, failure_posture),
            *diagnostics.next_actions,
            *evidence.next_actions,
        ],
    )
