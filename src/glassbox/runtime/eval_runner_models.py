"""Data models for replay-backed eval suite execution."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.eval_coverage import EvalCoverageAuditResult
from glassbox.runtime.evals import EvalBaselineRefreshPolicy
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.evals import EvalInvariant
from glassbox.runtime.evals import EvalVerificationStage
from glassbox.runtime.replay import ReplayOutcome

type EvalProfileBudgetStatus = Literal["ok", "warning", "violated"]
type EvalProfileBudgetEnforcement = Literal["enforced", "warning"]
type EvalProfileBudgetViolationCode = Literal[
    "selected_case_count",
    "selected_invariant_case_count",
    "recorded_model_call_count",
    "case_artifact_bytes",
    "unsupported_cases",
    "advisory_cases",
]


class EvalCaseResult(BaseModel):
    """One executed eval case with expectation-aware pass/fail state."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    severity: EvalCaseSeverity = "medium"
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    baseline_refresh_policy: EvalBaselineRefreshPolicy = "review_required"
    selected_invariants: list[EvalInvariant] = Field(default_factory=list)
    replay_outcome: ReplayOutcome
    replay_exit_code: int
    passed: bool
    message: str | None = None
    mismatches: list[str] = Field(default_factory=list)
    relevant_mismatches: list[str] = Field(default_factory=list)
    ignored_mismatches: list[str] = Field(default_factory=list)
    first_relevant_mismatch: str | None = None
    triage_classification: str | None = None
    triage_headline: str | None = None
    triage_first_relevant_change: str | None = None
    triage_drift_sources: list[str] = Field(default_factory=list)
    triage_recommended_inspection_path: str | None = None
    selected_invariant_interpretation: str | None = None
    artifact_path: Path


class EvalProfileBudgetViolation(BaseModel):
    """One profile-budget violation surfaced during eval execution."""

    model_config = ConfigDict(extra="forbid")

    code: EvalProfileBudgetViolationCode
    message: str
    actual: int
    limit: int | None = None
    case_ids: list[str] = Field(default_factory=list)


class EvalProfileBudgetHealth(BaseModel):
    """Measured health for one profile budget during suite execution."""

    model_config = ConfigDict(extra="forbid")

    status: EvalProfileBudgetStatus
    enforcement: EvalProfileBudgetEnforcement
    max_selected_case_count: int | None = None
    selected_case_count: int
    max_selected_invariant_case_count: int | None = None
    selected_invariant_case_count: int
    max_recorded_model_call_count: int | None = None
    recorded_model_call_count: int
    max_case_artifact_bytes: int | None = None
    case_artifact_bytes: int
    allow_unsupported_cases: bool
    unsupported_case_count: int
    allow_advisory_cases: bool
    advisory_case_count: int
    promotion_policy: str | None = None
    demotion_policy: str | None = None
    violations: list[EvalProfileBudgetViolation] = Field(default_factory=list)


class EvalSuiteResult(BaseModel):
    """Summary of one serial eval-suite execution."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    output_dir: Path
    summary_path: Path
    profile_id: str | None = None
    profile_title: str | None = None
    profile_verification_stage: EvalVerificationStage | None = None
    profile_budget: EvalProfileBudgetHealth | None = None
    coverage_audit: EvalCoverageAuditResult | None = None
    selected_case_count: int
    passed_case_count: int
    failed_case_count: int
    exit_code: int
    outcome_counts: dict[ReplayOutcome, int]
    cases: list[EvalCaseResult]
