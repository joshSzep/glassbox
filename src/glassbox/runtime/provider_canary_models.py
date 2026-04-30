"""Shared provider-canary models and retained evidence constants."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.provider_capability_matrix import ProviderCapabilityMatrix

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

EVIDENCE_STALE_AFTER_SECONDS = 7 * 24 * 60 * 60
FRESHNESS_POLICY_VERSION = "provider-evidence-freshness.v1"
PROVIDER_CANARY_SCHEMA_VERSION = "provider-canary-summary.v1"


class ProviderCanaryScenarioDefinition(BaseModel):
    """Policy-owned advisory canary scenario metadata."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    automation_status: ProviderCanaryAutomationStatus
    timeout_seconds: float
    description: str
    prompt: str | None = None


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

    schema_version: str = PROVIDER_CANARY_SCHEMA_VERSION
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
    freshness_policy_version: str = FRESHNESS_POLICY_VERSION
    stale_after_seconds: int = EVIDENCE_STALE_AFTER_SECONDS
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
