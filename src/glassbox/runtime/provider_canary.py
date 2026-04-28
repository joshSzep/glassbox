"""Advisory live-provider canary execution and summary artifacts."""

import asyncio
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import SessionConfig
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityMatrix
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report

type ProviderCanaryOutcome = Literal["passed", "failed", "skipped", "warning"]

_DEFAULT_SCENARIOS = ("streaming-text",)


class ProviderCanaryScenarioResult(BaseModel):
    """Outcome for one advisory canary scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    outcome: ProviderCanaryOutcome
    detail: str
    event_family_counts: dict[str, int] = Field(default_factory=dict)
    session_id: str | None = None
    final_status: str | None = None


class ProviderCanarySummary(BaseModel):
    """Structured retained advisory provider-canary evidence."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    advisory: bool
    provider: str
    model_name: str
    diagnostics_state: str
    output_path: str
    scenarios: list[ProviderCanaryScenarioResult]
    capability_matrix: ProviderCapabilityMatrix
    skipped_reason: str | None = None
    next_actions: list[str]


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
    selected_scenarios = scenarios or list(_DEFAULT_SCENARIOS)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "provider-canary-summary.json"

    if diagnostics.state != "ready" or diagnostics.runtime_mode == "local":
        summary = _skipped_summary(
            diagnostics,
            output_path=output_path,
            scenarios=selected_scenarios,
            reason=_skip_reason(diagnostics),
        )
        _write_summary(output_path, summary)
        return summary

    results: list[ProviderCanaryScenarioResult] = []
    for scenario_id in selected_scenarios:
        if scenario_id != "streaming-text":
            results.append(
                ProviderCanaryScenarioResult(
                    scenario_id=scenario_id,
                    outcome="skipped",
                    detail="scenario is policy-defined but not automated yet",
                )
            )
            continue
        results.append(await _run_streaming_text_canary(workspace_root, model_name))

    next_actions = [
        action
        for result in results
        if result.outcome in {"failed", "warning"}
        for action in [f"inspect provider canary scenario {result.scenario_id}"]
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
        scenarios=results,
        capability_matrix=capability_matrix,
        skipped_reason=None,
        next_actions=next_actions,
    )
    _write_summary(output_path, summary)
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
                "Reply with a short provider canary acknowledgement.",
            )
            events = repository.read_session_events(state.session_id)
            final_state = repository.get_session_state(state.session_id)
    except Exception as exc:
        return ProviderCanaryScenarioResult(
            scenario_id="streaming-text",
            outcome="failed",
            detail=f"live provider canary failed: {exc}",
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
        event_family_counts=counts,
        session_id=str(state.session_id),
        final_status=final_state.status if final_state is not None else None,
    )


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


def _skipped_summary(
    diagnostics: ProviderDiagnosticsReport,
    *,
    output_path: Path,
    scenarios: list[str],
    reason: str,
) -> ProviderCanarySummary:
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
        scenarios=[
            ProviderCanaryScenarioResult(
                scenario_id=scenario_id,
                outcome="skipped",
                detail=reason,
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


def _skip_reason(diagnostics: ProviderDiagnosticsReport) -> str:
    if diagnostics.runtime_mode == "local":
        return "selected model uses the deterministic local runtime"
    if diagnostics.state == "local_fallback":
        return "provider credentials are unavailable; local fallback would run"
    if diagnostics.problems:
        return "; ".join(diagnostics.problems)
    return f"provider diagnostics state is {diagnostics.state}"


def _write_summary(output_path: Path, summary: ProviderCanarySummary) -> None:
    output_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
