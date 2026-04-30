"""Provider-canary summary persistence and outcome aggregation."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.runtime.provider_canary_models import ProviderCanaryOutcome
from glassbox.runtime.provider_canary_models import ProviderCanaryScenarioDefinition
from glassbox.runtime.provider_canary_models import ProviderCanaryScenarioResult
from glassbox.runtime.provider_canary_models import ProviderCanarySummary
from glassbox.runtime.provider_canary_scenarios import provider_canary_definition_for
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport


def write_provider_canary_summary(
    output_path: Path,
    summary: ProviderCanarySummary,
) -> None:
    """Persist retained advisory provider-canary evidence."""

    output_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def skipped_provider_canary_summary(
    diagnostics: ProviderDiagnosticsReport,
    *,
    output_path: Path,
    scenarios: list[str],
    scenario_definitions: list[ProviderCanaryScenarioDefinition],
    reason: str,
) -> ProviderCanarySummary:
    """Build the retained summary for a skipped advisory provider-canary run."""

    capability_results: dict[str, ProviderCapabilityResult] = {
        scenario_id: "skipped" for scenario_id in scenarios
    }
    return ProviderCanarySummary(
        generated_at=datetime.now(UTC).isoformat(),
        advisory=True,
        provider=diagnostics.selected_provider,
        model_name=diagnostics.selected_model_name,
        diagnostics_state=diagnostics.state,
        output_path=str(output_path),
        scenario_definitions=scenario_definitions,
        scenarios=[
            ProviderCanaryScenarioResult(
                scenario_id=scenario_id,
                outcome="skipped",
                detail=reason,
                automation_status=provider_canary_definition_for(
                    scenario_id
                ).automation_status,
                timeout_seconds=provider_canary_definition_for(
                    scenario_id
                ).timeout_seconds,
            )
            for scenario_id in scenarios
        ],
        capability_matrix=build_provider_capability_matrix(
            diagnostics,
            scenario_ids=scenarios,
            results=capability_results,
            skipped_reason=reason,
        ),
        skipped_reason=reason,
        next_actions=diagnostics.next_actions,
    )


def count_provider_canary_outcomes(
    scenarios: list[ProviderCanaryScenarioResult],
) -> dict[ProviderCanaryOutcome, int]:
    """Count retained scenario outcomes for evidence summaries."""

    counts: dict[ProviderCanaryOutcome, int] = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "warning": 0,
    }
    for scenario in scenarios:
        counts[scenario.outcome] += 1
    return counts
