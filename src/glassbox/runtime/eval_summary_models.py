"""Shared models for eval suite summaries and release sign-off reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.evals import EvalBaselineOperation
from glassbox.runtime.evals import EvalBaselineRefreshPolicy
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalVerificationStage
from glassbox.runtime.replay import ReplayOutcome

type AnnotationLevel = Literal["notice", "warning", "error"]
type EvalReleaseSignoffStatus = Literal["passed", "warning", "failed"]
type EvalReleaseProfileStatus = Literal["passed", "warning", "failed", "skipped"]


@dataclass(frozen=True)
class EvalAutomationAnnotation:
    """One GitHub Actions-friendly annotation for a replay/eval case."""

    level: AnnotationLevel
    title: str
    message: str


@dataclass(frozen=True)
class EvalReleaseSignoffProfileInput:
    """Executed profile evidence used to build a release sign-off report."""

    profile: EvalProfileDefinition
    eval_cases: list[EvalCase]
    suite_result: EvalSuiteResult


@dataclass(frozen=True)
class EvalReleaseSignoffSkippedProfileInput:
    """One requested profile omitted from release evidence generation."""

    profile_id: str
    reason: str
    profile: EvalProfileDefinition | None = None


class EvalReleaseSignoffCaseReport(BaseModel):
    """Release-oriented summary for one retained eval case artifact."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    severity: EvalCaseSeverity = "medium"
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    baseline_refresh_policy: EvalBaselineRefreshPolicy = "review_required"
    passed: bool
    replay_outcome: ReplayOutcome
    artifact_path: str
    triage_headline: str | None = None
    triage_classification: str | None = None
    message: str | None = None
    baseline_history_count: int = 0
    latest_baseline_recorded_at: datetime | None = None
    latest_baseline_operation: EvalBaselineOperation | None = None
    latest_baseline_rationale: str | None = None


class EvalReleaseSignoffProfileReport(BaseModel):
    """Release-oriented summary for one named eval profile."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    profile_title: str | None = None
    verification_stage: EvalVerificationStage | None = None
    blocking: bool | None = None
    status: EvalReleaseProfileStatus
    decision_summary: str
    skip_reason: str | None = None
    selected_case_count: int = 0
    passed_case_count: int = 0
    failed_case_count: int = 0
    advisory_drift_case_count: int = 0
    unsupported_case_count: int = 0
    budget_status: str | None = None
    budget_enforcement: str | None = None
    suite_exit_code: int | None = None
    severity_totals: dict[EvalCaseSeverity, int] = Field(default_factory=dict)
    failed_severity_totals: dict[EvalCaseSeverity, int] = Field(default_factory=dict)
    capability_count: int | None = None
    covered_capability_count: int | None = None
    uncovered_capability_ids: list[str] = Field(default_factory=list)
    uncovered_release_critical_capability_ids: list[str] = Field(default_factory=list)
    output_dir: str | None = None
    summary_artifact_path: str | None = None
    cases: list[EvalReleaseSignoffCaseReport] = Field(default_factory=list)


class EvalReleaseSignoffReport(BaseModel):
    """Machine-readable release sign-off summary across named eval profiles."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    generated_at: datetime
    requested_profile_ids: list[str] = Field(default_factory=list)
    tag_filters: list[str] = Field(default_factory=list)
    status: EvalReleaseSignoffStatus
    contract_satisfied: bool
    exit_code: int
    profile_count: int
    executed_profile_count: int
    skipped_profile_count: int
    advisory_drift_case_count: int
    unsupported_case_count: int
    capability_count: int
    covered_capability_count: int
    uncovered_capability_ids: list[str] = Field(default_factory=list)
    uncovered_release_critical_capability_ids: list[str] = Field(default_factory=list)
    severity_totals: dict[EvalCaseSeverity, int] = Field(default_factory=dict)
    failed_severity_totals: dict[EvalCaseSeverity, int] = Field(default_factory=dict)
    latest_baseline_recorded_at: datetime | None = None
    latest_baseline_case_id: str | None = None
    latest_baseline_operation: EvalBaselineOperation | None = None
    oldest_baseline_recorded_at: datetime | None = None
    oldest_baseline_case_id: str | None = None
    oldest_baseline_operation: EvalBaselineOperation | None = None
    cases_without_baseline_history: list[str] = Field(default_factory=list)
    advisory_refresh_case_ids: list[str] = Field(default_factory=list)
    profiles: list[EvalReleaseSignoffProfileReport] = Field(default_factory=list)
