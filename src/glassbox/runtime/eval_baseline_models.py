"""Shared models for eval baseline promotion and refresh reports."""

from pathlib import Path
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.evals import EvalProfileTrack
from glassbox.runtime.evals import EvalVerificationStage

DEFAULT_EVAL_BASELINE_REPORTS_DIR = Path(".glassbox") / "evals" / "baseline-updates"
type EvalExpectationMode = Literal["exact_match", "selected_invariants"]


class EvalBaselineValueChange(BaseModel):
    """One before/after value change in a baseline update report."""

    model_config = ConfigDict(extra="forbid")

    before: Any = None
    after: Any = None


class EvalBaselineCapabilityImpact(BaseModel):
    """Coverage metadata that helps reviewers understand a baseline change."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    title: str | None = None
    criticality: str | None = None
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    expected_case_ids: list[str] = Field(default_factory=list)
    current_case_expected: bool = False


class EvalBaselineProfileImpact(BaseModel):
    """Profile metadata affected by one baseline promotion or refresh."""

    model_config = ConfigDict(extra="forbid")
    profile_id: str
    title: str
    verification_stage: EvalVerificationStage
    track: EvalProfileTrack
    blocking: bool
    selection_reasons: list[str] = Field(default_factory=list)


class EvalBaselineImpactSummary(BaseModel):
    """Resolved impact context for one baseline promotion or refresh."""

    model_config = ConfigDict(extra="forbid")
    likely_change_owners: list[str] = Field(default_factory=list)
    impacted_verification_stages: list[EvalVerificationStage] = Field(
        default_factory=list
    )
    impacted_capabilities: list[EvalBaselineCapabilityImpact] = Field(
        default_factory=list
    )
    impacted_profiles: list[EvalBaselineProfileImpact] = Field(default_factory=list)

    def blocking_profile_ids(self) -> list[str]:
        return [
            profile.profile_id for profile in self.impacted_profiles if profile.blocking
        ]


class EvalBaselineUpdateReport(BaseModel):
    """Review artifact for one promoted or refreshed eval baseline."""

    model_config = ConfigDict(extra="forbid")
    operation: str
    case_id: str
    title: str
    source_session_id: UUID
    rationale: str
    case_path: Path
    bundle_path: Path
    report_path: Path
    acknowledgement_required: bool = False
    acknowledgement_received: bool = False
    bundle_summary_before: dict[str, Any] | None = None
    bundle_summary_after: dict[str, Any] = Field(default_factory=dict)
    bundle_metric_changes: dict[str, EvalBaselineValueChange] = Field(
        default_factory=dict
    )
    manifest_field_changes: dict[str, EvalBaselineValueChange] = Field(
        default_factory=dict
    )
    expectation_before: dict[str, Any] | None = None
    expectation_after: dict[str, Any] = Field(default_factory=dict)
    release_contract_before: dict[str, Any] | None = None
    release_contract_after: dict[str, Any] = Field(default_factory=dict)
    baseline_history_count_before: int = 0
    baseline_history_count_after: int = 0
    likely_change_owners: list[str] = Field(default_factory=list)
    impacted_verification_stages: list[EvalVerificationStage] = Field(
        default_factory=list
    )
    impacted_capabilities: list[EvalBaselineCapabilityImpact] = Field(
        default_factory=list
    )
    impacted_profiles: list[EvalBaselineProfileImpact] = Field(default_factory=list)
    impacted_blocking_profile_ids: list[str] = Field(default_factory=list)
