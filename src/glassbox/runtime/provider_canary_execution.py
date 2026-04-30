"""Live provider-canary execution orchestration."""

import asyncio
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import SessionConfig
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.provider_canary_models import ProviderCanaryOutcome
from glassbox.runtime.provider_canary_models import ProviderCanaryScenarioDefinition
from glassbox.runtime.provider_canary_models import ProviderCanaryScenarioResult
from glassbox.runtime.provider_canary_models import ProviderCanarySummary
from glassbox.runtime.provider_canary_reporting import skipped_provider_canary_summary
from glassbox.runtime.provider_canary_reporting import write_provider_canary_summary
from glassbox.runtime.provider_canary_scenarios import provider_canary_definition_for
from glassbox.runtime.provider_canary_scenarios import (
    selected_provider_canary_scenarios,
)
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report


async def run_provider_canary(
    workspace_root: Path,
    *,
    model_name: str,
    output_dir: Path,
    scenarios: list[str] | None = None,
) -> ProviderCanarySummary:
    """Run or skip advisory provider canaries and retain a summary artifact."""

    diagnostics = build_provider_diagnostics_report(
        workspace_root,
        explicit_model_name=model_name,
    )
    selected_scenarios = selected_provider_canary_scenarios(scenarios)
    scenario_definitions = [
        provider_canary_definition_for(scenario_id)
        for scenario_id in selected_scenarios
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "provider-canary-summary.json"

    if diagnostics.state != "ready" or diagnostics.runtime_mode == "local":
        summary = skipped_provider_canary_summary(
            diagnostics,
            output_path=output_path,
            scenarios=selected_scenarios,
            scenario_definitions=scenario_definitions,
            reason=_provider_canary_skip_reason(diagnostics),
        )
        write_provider_canary_summary(output_path, summary)
        return summary

    results: list[ProviderCanaryScenarioResult] = []
    for definition in scenario_definitions:
        if definition.automation_status != "automated":
            results.append(
                ProviderCanaryScenarioResult(
                    scenario_id=definition.scenario_id,
                    outcome="skipped",
                    detail=(
                        "scenario is retained for preflight but not live-automated yet"
                    ),
                    automation_status=definition.automation_status,
                    timeout_seconds=definition.timeout_seconds,
                )
            )
            continue
        try:
            results.append(
                await asyncio.wait_for(
                    _run_streaming_text_canary(workspace_root, model_name, definition),
                    timeout=definition.timeout_seconds,
                )
            )
        except TimeoutError:
            results.append(
                ProviderCanaryScenarioResult(
                    scenario_id=definition.scenario_id,
                    outcome="failed",
                    detail=f"scenario timed out after {definition.timeout_seconds:g}s",
                    automation_status=definition.automation_status,
                    timeout_seconds=definition.timeout_seconds,
                )
            )

    next_actions = [
        f"inspect provider canary scenario {result.scenario_id}"
        for result in results
        if result.outcome in {"failed", "warning"}
    ]
    capability_results: dict[str, ProviderCapabilityResult] = {
        result.scenario_id: result.outcome for result in results
    }
    capability_matrix = build_provider_capability_matrix(
        diagnostics,
        scenario_ids=selected_scenarios,
        results=capability_results,
        details={result.scenario_id: result.detail for result in results},
    )
    summary = ProviderCanarySummary(
        generated_at=datetime.now(UTC).isoformat(),
        advisory=True,
        provider=diagnostics.selected_provider,
        model_name=diagnostics.selected_model_name,
        diagnostics_state=diagnostics.state,
        output_path=str(output_path),
        scenario_definitions=scenario_definitions,
        scenarios=results,
        capability_matrix=capability_matrix,
        skipped_reason=None,
        next_actions=next_actions,
    )
    write_provider_canary_summary(output_path, summary)
    return summary


def run_provider_canary_sync(
    workspace_root: Path,
    *,
    model_name: str,
    output_dir: Path,
    scenarios: list[str] | None = None,
) -> ProviderCanarySummary:
    """Synchronous wrapper for CLI entrypoints."""

    return asyncio.run(
        run_provider_canary(
            workspace_root,
            model_name=model_name,
            output_dir=output_dir,
            scenarios=scenarios,
        )
    )


async def _run_streaming_text_canary(
    workspace_root: Path,
    model_name: str,
    definition: ProviderCanaryScenarioDefinition,
) -> ProviderCanaryScenarioResult:
    try:
        with open_runtime_context(workspace_root) as runtime_context:
            service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await service.start_session(
                SessionConfig(
                    model_name=model_name,
                    cwd=workspace_root,
                    approval_mode="never",
                )
            )
            await service.submit_user_message(
                state.session_id,
                definition.prompt
                or "Reply with a short provider canary acknowledgement.",
            )
            events = repository.read_session_events(state.session_id)
            final_state = repository.get_session_state(state.session_id)
    except Exception as exc:
        return ProviderCanaryScenarioResult(
            scenario_id="streaming-text",
            outcome="failed",
            detail=f"live provider canary failed: {exc}",
            automation_status=definition.automation_status,
            timeout_seconds=definition.timeout_seconds,
        )

    counts = _event_family_counts(events)
    has_model_start = counts.get("ModelCallStarted", 0) > 0
    has_completed = counts.get("AssistantMessageCompleted", 0) > 0
    outcome: ProviderCanaryOutcome = (
        "passed" if has_model_start and has_completed else "warning"
    )
    detail = (
        "provider text turn completed with model and assistant evidence"
        if outcome == "passed"
        else "provider turn completed without the expected event-family evidence"
    )
    return ProviderCanaryScenarioResult(
        scenario_id="streaming-text",
        outcome=outcome,
        detail=detail,
        automation_status=definition.automation_status,
        timeout_seconds=definition.timeout_seconds,
        event_family_counts=counts,
        session_id=str(state.session_id),
        final_status=_final_streaming_text_status(
            events,
            fallback=final_state.status if final_state is not None else None,
        ),
    )


def _provider_canary_skip_reason(diagnostics: ProviderDiagnosticsReport) -> str:
    if diagnostics.runtime_mode == "local":
        return "selected model uses the deterministic local runtime"
    if diagnostics.state == "local_fallback":
        return "provider credentials are unavailable; local fallback would run"
    if diagnostics.problems:
        return "; ".join(diagnostics.problems)
    return f"provider diagnostics state is {diagnostics.state}"


def _final_streaming_text_status(events, *, fallback: str | None) -> str | None:
    for event in reversed(events):
        if isinstance(event.payload, TurnCompleted):
            return event.payload.outcome
        if isinstance(event.payload, TurnFailed):
            return "failed"
    return fallback


def _event_family_counts(events) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = event.event_type
        if isinstance(event.payload, ModelCallStarted):
            event_type = "ModelCallStarted"
        elif isinstance(event.payload, AssistantMessageCompleted):
            event_type = "AssistantMessageCompleted"
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts
