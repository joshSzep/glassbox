"""Capability-fit and retained canary evidence helpers."""

import json
from pathlib import Path

from glassbox.core.types import AutonomyMode
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.provider_canary import ProviderCanarySummary
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_recommendation_models import ProviderCapabilityFit
from glassbox.runtime.provider_recommendation_models import ProviderFailurePosture
from glassbox.runtime.provider_recommendation_models import (
    ProviderRecommendationEvidence,
)
from glassbox.runtime.provider_recommendation_models import ProviderTaskKind

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


def load_latest_provider_canary_summary(
    evidence: ProviderCanaryEvidenceSummary,
) -> ProviderCanarySummary | None:
    """Load the latest retained canary summary referenced by evidence."""

    if evidence.latest_summary_path is None:
        return None
    path = Path(evidence.latest_summary_path)
    try:
        return ProviderCanarySummary.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except OSError, ValueError, json.JSONDecodeError:
        return None


def provider_recommendation_evidence(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderCanaryEvidenceSummary,
    summary: ProviderCanarySummary | None,
    relevant_scenarios: list[str],
) -> ProviderRecommendationEvidence:
    """Derive relevant retained canary coverage for one workflow."""

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


def required_provider_capabilities(
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
    """Return operator-facing capabilities expected for a workflow."""

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


def provider_workflow_scenarios(
    task_kind: ProviderTaskKind,
    autonomy_mode: AutonomyMode,
) -> list[str]:
    """Return canary scenarios relevant to a task/autonomy workflow."""

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


def provider_capability_fit(
    diagnostics: ProviderDiagnosticsReport,
    evidence: ProviderRecommendationEvidence,
    failure_posture: ProviderFailurePosture,
) -> ProviderCapabilityFit:
    """Score whether retained evidence covers the workflow capabilities."""

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
