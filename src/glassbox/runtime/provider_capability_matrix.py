"""Advisory provider capability matrix models and builders."""

from collections.abc import Mapping
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from typing import Literal
from typing import TypedDict

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport

type ProviderCapabilitySupport = Literal[
    "supported",
    "unsupported",
    "assumed",
    "not_applicable",
    "unknown",
]
type ProviderCapabilityResult = Literal[
    "passed",
    "failed",
    "skipped",
    "warning",
    "not_run",
]
type ProviderCredentialState = Literal[
    "configured",
    "missing",
    "partial",
    "not_required",
    "unsupported",
]
type ProviderRedactionStatus = Literal["redacted", "not_applicable"]
type ProviderScenarioConfidence = Literal[
    "observed",
    "preflight",
    "skipped",
    "unknown",
]
type ProviderRetryPosture = Literal[
    "not_applicable",
    "not_evaluated",
    "retry_ready",
    "rate_limit_unknown",
    "unknown",
]
type ProviderToolCallReliability = Literal[
    "observed",
    "assumed",
    "not_applicable",
    "unknown",
]


class _ScenarioCapabilities(TypedDict):
    streaming_support: ProviderCapabilitySupport
    tool_call_support: ProviderCapabilitySupport
    approval_behavior: ProviderCapabilitySupport
    ask_user_behavior: ProviderCapabilitySupport
    cancellation_behavior: ProviderCapabilitySupport
    dashboard_compatibility: ProviderCapabilitySupport
    daemon_attach_compatibility: ProviderCapabilitySupport
    observed_limits: list[str]
    retry_posture: ProviderRetryPosture
    tool_call_reliability: ProviderToolCallReliability


class ProviderCapabilityMatrixEntry(BaseModel):
    """One provider/model/scenario row in retained advisory evidence."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model_name: str
    scenario_id: str
    credential_state: ProviderCredentialState
    streaming_support: ProviderCapabilitySupport
    tool_call_support: ProviderCapabilitySupport
    approval_behavior: ProviderCapabilitySupport
    ask_user_behavior: ProviderCapabilitySupport
    cancellation_behavior: ProviderCapabilitySupport
    dashboard_compatibility: ProviderCapabilitySupport
    daemon_attach_compatibility: ProviderCapabilitySupport
    scenario_confidence: ProviderScenarioConfidence
    observed_limits: list[str] = Field(default_factory=list)
    retry_posture: ProviderRetryPosture
    tool_call_reliability: ProviderToolCallReliability
    result: ProviderCapabilityResult
    skipped_reason: str | None = None
    redaction_status: ProviderRedactionStatus = "redacted"
    evidence_summary: str


class ProviderCapabilityMatrix(BaseModel):
    """Reviewable advisory provider capability evidence matrix."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    advisory: bool = True
    deterministic_release_blocking: bool = False
    provider: str
    model_name: str
    diagnostics_state: str
    entries: list[ProviderCapabilityMatrixEntry] = Field(default_factory=list)
    interpretation: str


def build_provider_capability_matrix(
    diagnostics: ProviderDiagnosticsReport,
    *,
    scenario_ids: Sequence[str],
    results: Mapping[str, ProviderCapabilityResult] | None = None,
    details: Mapping[str, str] | None = None,
    skipped_reason: str | None = None,
) -> ProviderCapabilityMatrix:
    """Build redacted advisory capability evidence rows for selected scenarios."""

    result_map = dict(results or {})
    detail_map = dict(details or {})
    entries: list[ProviderCapabilityMatrixEntry] = []
    for scenario_id in scenario_ids:
        capabilities = _scenario_capabilities(scenario_id)
        result = result_map.get(scenario_id, "not_run")
        entries.append(
            ProviderCapabilityMatrixEntry(
                provider=diagnostics.selected_provider,
                model_name=diagnostics.selected_model_name,
                scenario_id=scenario_id,
                credential_state=_credential_state(diagnostics),
                streaming_support=capabilities["streaming_support"],
                tool_call_support=capabilities["tool_call_support"],
                approval_behavior=capabilities["approval_behavior"],
                ask_user_behavior=capabilities["ask_user_behavior"],
                cancellation_behavior=capabilities["cancellation_behavior"],
                dashboard_compatibility=capabilities["dashboard_compatibility"],
                daemon_attach_compatibility=capabilities["daemon_attach_compatibility"],
                scenario_confidence=_scenario_confidence(
                    scenario_id,
                    result,
                    skipped_reason=skipped_reason,
                    result_map_present=bool(result_map),
                ),
                observed_limits=capabilities["observed_limits"],
                retry_posture=capabilities["retry_posture"],
                tool_call_reliability=capabilities["tool_call_reliability"],
                result=result,
                skipped_reason=(
                    skipped_reason if result == "skipped" or not result_map else None
                ),
                evidence_summary=detail_map.get(
                    scenario_id,
                    _default_evidence_summary(diagnostics, scenario_id),
                ),
            )
        )
    return ProviderCapabilityMatrix(
        generated_at=datetime.now(UTC).isoformat(),
        provider=diagnostics.selected_provider,
        model_name=diagnostics.selected_model_name,
        diagnostics_state=diagnostics.state,
        entries=entries,
        interpretation=(
            "Provider capability evidence is advisory and separate from "
            "deterministic replay/eval release signoff."
        ),
    )


def _credential_state(
    diagnostics: ProviderDiagnosticsReport,
) -> ProviderCredentialState:
    if diagnostics.runtime_mode == "local":
        return "not_required"
    if diagnostics.state == "unsupported_model":
        return "unsupported"
    if diagnostics.state in {"missing_credentials", "invalid_provider_config"}:
        return "partial"
    if diagnostics.state == "local_fallback":
        return "missing"
    return "configured"


def _scenario_capabilities(scenario_id: str) -> _ScenarioCapabilities:
    values: _ScenarioCapabilities = {
        "streaming_support": "unknown",
        "tool_call_support": "unknown",
        "approval_behavior": "not_applicable",
        "ask_user_behavior": "not_applicable",
        "cancellation_behavior": "not_applicable",
        "dashboard_compatibility": "not_applicable",
        "daemon_attach_compatibility": "not_applicable",
        "observed_limits": [],
        "retry_posture": "not_applicable",
        "tool_call_reliability": "not_applicable",
    }
    if scenario_id == "streaming-text":
        values["streaming_support"] = "supported"
        values["observed_limits"] = ["text streaming only"]
    elif scenario_id == "tool-call":
        values["tool_call_support"] = "supported"
        values["tool_call_reliability"] = "assumed"
    elif scenario_id == "approval":
        values["tool_call_support"] = "supported"
        values["approval_behavior"] = "supported"
        values["tool_call_reliability"] = "assumed"
    elif scenario_id == "ask-user":
        values["tool_call_support"] = "supported"
        values["ask_user_behavior"] = "supported"
        values["tool_call_reliability"] = "assumed"
    elif scenario_id == "cancellation":
        values["cancellation_behavior"] = "assumed"
    elif scenario_id == "dashboard":
        values["dashboard_compatibility"] = "assumed"
    elif scenario_id == "daemon-attach":
        values["daemon_attach_compatibility"] = "assumed"
    elif scenario_id == "malformed-tool-call":
        values["tool_call_support"] = "supported"
        values["tool_call_reliability"] = "unknown"
        values["observed_limits"] = ["schema-invalid tool-call recovery not automated"]
    elif scenario_id == "long-context-continuity":
        values["streaming_support"] = "assumed"
        values["observed_limits"] = [
            "context window and continuity limits not measured"
        ]
    elif scenario_id == "retry-behavior":
        values["retry_posture"] = "not_evaluated"
        values["observed_limits"] = ["transient provider retry path not automated"]
    elif scenario_id == "rate-limit-handling":
        values["retry_posture"] = "rate_limit_unknown"
        values["observed_limits"] = ["rate-limit headers and backoff not observed"]
    elif scenario_id == "tool-call-streaming":
        values["streaming_support"] = "supported"
        values["tool_call_support"] = "supported"
        values["tool_call_reliability"] = "assumed"
        values["observed_limits"] = ["streaming tool-call delta handling not automated"]
    elif scenario_id == "cancellation-during-retry":
        values["cancellation_behavior"] = "assumed"
        values["retry_posture"] = "not_evaluated"
        values["observed_limits"] = ["retry cancellation timing not automated"]
    elif scenario_id == "multi-step-plan-following":
        values["tool_call_support"] = "supported"
        values["tool_call_reliability"] = "assumed"
        values["observed_limits"] = ["multi-step plan adherence not automated"]
    elif scenario_id == "verification-loop-interaction":
        values["tool_call_support"] = "supported"
        values["tool_call_reliability"] = "assumed"
        values["observed_limits"] = ["verify-repair interaction not automated"]
    return values


def _scenario_confidence(
    scenario_id: str,
    result: ProviderCapabilityResult,
    *,
    skipped_reason: str | None,
    result_map_present: bool,
) -> ProviderScenarioConfidence:
    if result == "passed":
        return "observed"
    if result == "skipped" and skipped_reason is not None:
        return "skipped"
    if result == "skipped" and result_map_present:
        return "preflight"
    if scenario_id == "streaming-text" and result == "not_run":
        return "unknown"
    if result in {"failed", "warning"}:
        return "observed"
    return "preflight"


def _default_evidence_summary(
    diagnostics: ProviderDiagnosticsReport,
    scenario_id: str,
) -> str:
    if diagnostics.state != "ready":
        return (
            f"{scenario_id} did not run because diagnostics state is "
            f"{diagnostics.state}"
        )
    return f"{scenario_id} has no retained canary result yet"
