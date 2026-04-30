"""Advisory live-provider canary execution and summary artifacts."""

import asyncio
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
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
type ProviderCanaryAutomationStatus = Literal["automated", "preflight_only"]
type ProviderCanaryEvidenceStatus = Literal[
    "missing",
    "passed",
    "failed",
    "warning",
    "skipped",
]
type ProviderCanaryFreshnessStatus = Literal[
    "fresh",
    "stale",
    "incompatible",
    "missing",
    "credentialless",
    "warning",
    "failed",
]

_DEFAULT_SCENARIOS = (
    "streaming-text",
    "tool-call",
    "approval",
    "ask-user",
    "cancellation",
    "dashboard",
    "daemon-attach",
    "malformed-tool-call",
    "long-context-continuity",
    "retry-behavior",
    "rate-limit-handling",
    "tool-call-streaming",
    "cancellation-during-retry",
    "multi-step-plan-following",
    "verification-loop-interaction",
)
_EVIDENCE_STALE_AFTER_SECONDS = 7 * 24 * 60 * 60
_FRESHNESS_POLICY_VERSION = "provider-evidence-freshness.v1"
_PROVIDER_CANARY_SCHEMA_VERSION = "provider-canary-summary.v1"


class ProviderCanaryScenarioDefinition(BaseModel):
    """Policy-owned advisory canary scenario metadata."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    automation_status: ProviderCanaryAutomationStatus
    timeout_seconds: float
    description: str
    prompt: str | None = None


_SCENARIO_DEFINITIONS = {
    "streaming-text": ProviderCanaryScenarioDefinition(
        scenario_id="streaming-text",
        automation_status="automated",
        timeout_seconds=60.0,
        description=(
            "Run a short provider-backed text turn and verify model and "
            "assistant event evidence."
        ),
        prompt="Reply with a short provider canary acknowledgement.",
    ),
    "tool-call": ProviderCanaryScenarioDefinition(
        scenario_id="tool-call",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider/tool-call readiness before workflow-specific "
            "live automation is available."
        ),
    ),
    "approval": ProviderCanaryScenarioDefinition(
        scenario_id="approval",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider behavior for approval-gated tool workflows.",
    ),
    "ask-user": ProviderCanaryScenarioDefinition(
        scenario_id="ask-user",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider behavior for ask-user suspension and resume workflows."
        ),
    ),
    "cancellation": ProviderCanaryScenarioDefinition(
        scenario_id="cancellation",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight provider behavior for cancellation-sensitive workflow runs."
        ),
    ),
    "dashboard": ProviderCanaryScenarioDefinition(
        scenario_id="dashboard",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description="Preflight dashboard compatibility for retained provider evidence.",
    ),
    "daemon-attach": ProviderCanaryScenarioDefinition(
        scenario_id="daemon-attach",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight daemon attach compatibility for provider-backed sessions."
        ),
    ),
    "malformed-tool-call": ProviderCanaryScenarioDefinition(
        scenario_id="malformed-tool-call",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight provider/tool adapter behavior for malformed or "
            "schema-invalid tool calls."
        ),
    ),
    "long-context-continuity": ProviderCanaryScenarioDefinition(
        scenario_id="long-context-continuity",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider suitability for long-context continuity across "
            "multi-step local work."
        ),
    ),
    "retry-behavior": ProviderCanaryScenarioDefinition(
        scenario_id="retry-behavior",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider retry posture for transient failures.",
    ),
    "rate-limit-handling": ProviderCanaryScenarioDefinition(
        scenario_id="rate-limit-handling",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider behavior expectations around rate limits.",
    ),
    "tool-call-streaming": ProviderCanaryScenarioDefinition(
        scenario_id="tool-call-streaming",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight streaming behavior while tool calls are emitted.",
    ),
    "cancellation-during-retry": ProviderCanaryScenarioDefinition(
        scenario_id="cancellation-during-retry",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight cancellation behavior while retry handling is active.",
    ),
    "multi-step-plan-following": ProviderCanaryScenarioDefinition(
        scenario_id="multi-step-plan-following",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider suitability for following bounded task plans.",
    ),
    "verification-loop-interaction": ProviderCanaryScenarioDefinition(
        scenario_id="verification-loop-interaction",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider suitability for verify-repair loop interaction."
        ),
    ),
}


class ProviderCanaryScenarioResult(BaseModel):
    """Outcome for one advisory canary scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    outcome: ProviderCanaryOutcome
    detail: str
    automation_status: ProviderCanaryAutomationStatus = "automated"
    timeout_seconds: float | None = None
    event_family_counts: dict[str, int] = Field(default_factory=dict)
    session_id: str | None = None
    final_status: str | None = None


class ProviderCanarySummary(BaseModel):
    """Structured retained advisory provider-canary evidence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = _PROVIDER_CANARY_SCHEMA_VERSION
    generated_at: str
    advisory: bool
    provider: str
    model_name: str
    diagnostics_state: str
    output_path: str
    scenario_definitions: list[ProviderCanaryScenarioDefinition]
    scenarios: list[ProviderCanaryScenarioResult]
    capability_matrix: ProviderCapabilityMatrix
    skipped_reason: str | None = None
    next_actions: list[str]


class ProviderCanaryEvidenceSummary(BaseModel):
    """Compact index for retained provider-canary evidence."""

    model_config = ConfigDict(extra="forbid")

    summary_count: int
    latest_summary_path: str | None = None
    latest_generated_at: str | None = None
    latest_status: ProviderCanaryEvidenceStatus
    freshness_status: ProviderCanaryFreshnessStatus
    freshness_policy_version: str = _FRESHNESS_POLICY_VERSION
    stale_after_seconds: int = _EVIDENCE_STALE_AFTER_SECONDS
    schema_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    configured_model_name: str | None = None
    identity_matches_current_config: bool | None = None
    diagnostics_state: str | None = None
    scenario_count: int = 0
    matrix_entry_count: int = 0
    missing_scenarios: list[str] = Field(default_factory=list)
    passed_count: int = 0
    skipped_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    stale: bool = False
    next_actions: list[str] = Field(default_factory=list)


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
    selected_scenarios = _selected_scenarios(scenarios)
    scenario_definitions = [
        _definition_for_scenario(scenario_id) for scenario_id in selected_scenarios
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "provider-canary-summary.json"

    if diagnostics.state != "ready" or diagnostics.runtime_mode == "local":
        summary = _skipped_summary(
            diagnostics,
            output_path=output_path,
            scenarios=selected_scenarios,
            scenario_definitions=scenario_definitions,
            reason=_skip_reason(diagnostics),
        )
        _write_summary(output_path, summary)
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
        scenario_definitions=scenario_definitions,
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


def load_provider_canary_evidence(
    workspace_root: Path,
    *,
    summary_path: Path | None = None,
    expected_model_name: str | None = None,
) -> ProviderCanaryEvidenceSummary:
    """Load a compact advisory summary for retained provider-canary evidence."""

    summaries = _provider_canary_summary_paths(workspace_root, summary_path)
    if not summaries:
        return ProviderCanaryEvidenceSummary(
            summary_count=0,
            latest_status="missing",
            freshness_status="missing",
            configured_model_name=_configured_model_name(
                workspace_root,
                expected_model_name=expected_model_name,
            ),
            next_actions=[
                f"glassbox provider canary run --cwd {workspace_root}",
            ],
        )

    latest_path = summaries[0]
    payload = _load_summary_payload(latest_path)
    try:
        summary = ProviderCanarySummary.model_validate(payload)
    except ValueError as exc:
        return _legacy_or_invalid_provider_canary_evidence(
            latest_path,
            payload,
            summary_count=len(summaries),
            workspace_root=workspace_root,
            error=exc,
            expected_model_name=expected_model_name,
        )
    outcome_counts = _outcome_counts(summary.scenarios)
    latest_status = _evidence_status(outcome_counts)
    stale = _is_stale(latest_path)
    configured_model_name = _configured_model_name(
        workspace_root,
        expected_model_name=expected_model_name,
    )
    identity_matches_current_config = _identity_matches_current_config(
        retained_model_name=summary.model_name,
        configured_model_name=configured_model_name,
    )
    missing_scenarios = _missing_scenarios(summary)
    freshness_status = _freshness_status(
        latest_status=latest_status,
        stale=stale,
        diagnostics_state=summary.diagnostics_state,
        provider=summary.provider,
    )
    next_actions = [f"inspect provider canary evidence {latest_path}"]
    if stale:
        next_actions.append(f"glassbox provider canary run --cwd {workspace_root}")
    if identity_matches_current_config is False:
        next_actions.append(
            "rerun provider canary evidence for the currently configured model"
        )
    if missing_scenarios:
        next_actions.append(
            "rerun provider canary evidence to cover missing scenarios: "
            + ", ".join(missing_scenarios)
        )
    if latest_status in {"failed", "warning", "skipped"}:
        next_actions.extend(summary.next_actions)

    return ProviderCanaryEvidenceSummary(
        summary_count=len(summaries),
        latest_summary_path=str(latest_path),
        latest_generated_at=summary.generated_at,
        latest_status=latest_status,
        freshness_status=freshness_status,
        schema_version=summary.schema_version,
        provider=summary.provider,
        model_name=summary.model_name,
        configured_model_name=configured_model_name,
        identity_matches_current_config=identity_matches_current_config,
        diagnostics_state=summary.diagnostics_state,
        scenario_count=len(summary.scenarios),
        matrix_entry_count=len(summary.capability_matrix.entries),
        missing_scenarios=missing_scenarios,
        passed_count=outcome_counts["passed"],
        skipped_count=outcome_counts["skipped"],
        warning_count=outcome_counts["warning"],
        failed_count=outcome_counts["failed"],
        stale=stale,
        next_actions=next_actions,
    )


def _legacy_or_invalid_provider_canary_evidence(
    latest_path: Path,
    payload: dict[str, Any],
    *,
    summary_count: int,
    workspace_root: Path,
    error: ValueError,
    expected_model_name: str | None,
) -> ProviderCanaryEvidenceSummary:
    scenarios = payload.get("scenarios")
    scenario_count = len(scenarios) if isinstance(scenarios, list) else 0
    matrix_payload = payload.get("capability_matrix")
    matrix_entries = (
        matrix_payload.get("entries") if isinstance(matrix_payload, dict) else None
    )
    matrix_entry_count = len(matrix_entries) if isinstance(matrix_entries, list) else 0
    return ProviderCanaryEvidenceSummary(
        summary_count=summary_count,
        latest_summary_path=str(latest_path),
        latest_generated_at=_payload_str(payload.get("generated_at")),
        latest_status="warning",
        freshness_status="incompatible",
        schema_version=_payload_str(payload.get("schema_version")),
        provider=_payload_str(payload.get("provider")),
        model_name=_payload_str(payload.get("model_name")),
        configured_model_name=_configured_model_name(
            workspace_root,
            expected_model_name=expected_model_name,
        ),
        diagnostics_state=_payload_str(payload.get("diagnostics_state")),
        scenario_count=scenario_count,
        matrix_entry_count=matrix_entry_count,
        missing_scenarios=list(_DEFAULT_SCENARIOS),
        warning_count=1,
        stale=True,
        next_actions=[
            f"inspect provider canary evidence {latest_path}",
            f"glassbox provider canary run --cwd {workspace_root}",
            "retained provider canary evidence is stale or incompatible: "
            f"{type(error).__name__}",
        ],
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
    scenario_definitions: list[ProviderCanaryScenarioDefinition],
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
        scenario_definitions=scenario_definitions,
        scenarios=[
            ProviderCanaryScenarioResult(
                scenario_id=scenario_id,
                outcome="skipped",
                detail=reason,
                automation_status=_definition_for_scenario(
                    scenario_id
                ).automation_status,
                timeout_seconds=_definition_for_scenario(scenario_id).timeout_seconds,
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


def _selected_scenarios(scenarios: list[str] | None) -> list[str]:
    return scenarios or list(_DEFAULT_SCENARIOS)


def _definition_for_scenario(scenario_id: str) -> ProviderCanaryScenarioDefinition:
    return _SCENARIO_DEFINITIONS.get(
        scenario_id,
        ProviderCanaryScenarioDefinition(
            scenario_id=scenario_id,
            automation_status="preflight_only",
            timeout_seconds=30.0,
            description=(
                "Unknown scenario retained as a skipped advisory preflight row."
            ),
        ),
    )


def _write_summary(output_path: Path, summary: ProviderCanarySummary) -> None:
    output_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _provider_canary_summary_paths(
    workspace_root: Path,
    summary_path: Path | None,
) -> list[Path]:
    if summary_path is not None:
        resolved = (
            summary_path
            if summary_path.is_absolute()
            else workspace_root / summary_path
        )
        return [resolved] if resolved.exists() else []
    evidence_root = workspace_root / ".glassbox"
    if not evidence_root.exists():
        return []
    return sorted(
        evidence_root.glob("**/provider-canary-summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _load_summary_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _outcome_counts(
    scenarios: list[ProviderCanaryScenarioResult],
) -> dict[ProviderCanaryOutcome, int]:
    counts: dict[ProviderCanaryOutcome, int] = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "warning": 0,
    }
    for scenario in scenarios:
        counts[scenario.outcome] += 1
    return counts


def _evidence_status(
    outcome_counts: dict[ProviderCanaryOutcome, int],
) -> ProviderCanaryEvidenceStatus:
    if outcome_counts["failed"] > 0:
        return "failed"
    if outcome_counts["warning"] > 0:
        return "warning"
    if outcome_counts["skipped"] > 0:
        return "skipped" if outcome_counts["passed"] == 0 else "warning"
    return "passed"


def _freshness_status(
    *,
    latest_status: ProviderCanaryEvidenceStatus,
    stale: bool,
    diagnostics_state: str,
    provider: str,
) -> ProviderCanaryFreshnessStatus:
    if stale:
        return "stale"
    if latest_status == "failed":
        return "failed"
    if latest_status == "warning":
        return "warning"
    if latest_status == "skipped" and (
        diagnostics_state in {"missing_credentials", "local_fallback"}
        or provider == "local"
    ):
        return "credentialless"
    if latest_status == "skipped":
        return "warning"
    return "fresh"


def _is_stale(path: Path) -> bool:
    age_seconds = datetime.now(UTC).timestamp() - path.stat().st_mtime
    return age_seconds > _EVIDENCE_STALE_AFTER_SECONDS


def _configured_model_name(
    workspace_root: Path,
    *,
    expected_model_name: str | None,
) -> str | None:
    if expected_model_name is not None:
        return expected_model_name
    if not (workspace_root / "glassbox.profile.json").exists():
        return None
    try:
        return build_provider_diagnostics_report(workspace_root).selected_model_name
    except ValueError:
        return None


def _identity_matches_current_config(
    *,
    retained_model_name: str,
    configured_model_name: str | None,
) -> bool | None:
    if configured_model_name is None:
        return None
    return retained_model_name == configured_model_name


def _missing_scenarios(summary: ProviderCanarySummary) -> list[str]:
    observed = {entry.scenario_id for entry in summary.capability_matrix.entries}
    return [
        scenario_id for scenario_id in _DEFAULT_SCENARIOS if scenario_id not in observed
    ]


def _payload_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
