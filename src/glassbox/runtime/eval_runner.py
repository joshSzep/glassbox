"""Batch runner for replay-backed eval suites."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from glassbox.runtime.eval_coverage import (
    EvalCoverageAuditResult,
    maybe_audit_eval_coverage,
)
from glassbox.runtime.evals import (
    EvalBaselineRefreshPolicy,
    EvalCase,
    EvalCaseSeverity,
    EvalInvariant,
    EvalProfileDefinition,
    EvalVerificationStage,
    resolve_eval_suite_selection,
)
from glassbox.runtime.replay import (
    ReplayOutcome,
    ReplayResult,
    ReplayRunner,
    build_replay_triage,
)

_REPLAY_EXIT_CODES: dict[ReplayOutcome, int] = {
    "exact_match": 0,
    "behavioral_drift": 10,
    "manifest_drift": 11,
    "unsupported_session": 12,
    "replay_failure": 13,
}


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


class EvalSuiteResult(BaseModel):
    """Summary of one serial eval-suite execution."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    output_dir: Path
    summary_path: Path
    profile_id: str | None = None
    profile_title: str | None = None
    profile_verification_stage: EvalVerificationStage | None = None
    coverage_audit: EvalCoverageAuditResult | None = None
    selected_case_count: int
    passed_case_count: int
    failed_case_count: int
    exit_code: int
    outcome_counts: dict[ReplayOutcome, int]
    cases: list[EvalCaseResult]


class EvalRunner:
    """Run repository-local eval cases serially using portable replay bundles."""

    def __init__(self, replay_runner: ReplayRunner | None = None) -> None:
        self._replay_runner = replay_runner or ReplayRunner()

    async def run_suite(
        self,
        workspace_root: Path,
        *,
        profile_id: str | None = None,
        case_ids: list[str] | None = None,
        tags: list[str] | None = None,
        output_dir: Path | None = None,
        refresh_output_dir: bool = False,
    ) -> EvalSuiteResult:
        resolved_workspace_root = workspace_root.resolve()
        selection = resolve_eval_suite_selection(
            resolved_workspace_root,
            profile_id=profile_id,
            case_ids=case_ids,
            tags=tags,
        )
        eval_cases = selection.cases
        if not eval_cases:
            raise ValueError("no eval cases selected")
        coverage_audit = maybe_audit_eval_coverage(
            resolved_workspace_root,
            profile_id=profile_id,
            case_ids=case_ids,
            tags=tags,
        )

        resolved_output_dir = _resolve_output_dir(
            resolved_workspace_root,
            output_dir=output_dir,
        )
        if refresh_output_dir:
            _refresh_output_dir(
                resolved_workspace_root,
                output_dir=resolved_output_dir,
            )
        resolved_output_dir.mkdir(parents=True, exist_ok=True)

        case_results = [
            await self._run_case(
                eval_case,
                workspace_root=resolved_workspace_root,
                output_dir=resolved_output_dir,
            )
            for eval_case in eval_cases
        ]
        outcome_counts = _outcome_counts(case_results)
        exit_code = _suite_exit_code(case_results)
        summary_path = resolved_output_dir / "summary.json"
        suite_result = EvalSuiteResult(
            workspace_root=resolved_workspace_root,
            output_dir=resolved_output_dir,
            summary_path=summary_path,
            profile_id=_profile_id(selection.profile),
            profile_title=_profile_title(selection.profile),
            profile_verification_stage=_profile_stage(selection.profile),
            coverage_audit=coverage_audit,
            selected_case_count=len(case_results),
            passed_case_count=sum(1 for case in case_results if case.passed),
            failed_case_count=sum(1 for case in case_results if not case.passed),
            exit_code=exit_code,
            outcome_counts=outcome_counts,
            cases=case_results,
        )
        summary_path.write_text(
            json.dumps(suite_result.model_dump(mode="json"), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return suite_result

    async def _run_case(
        self,
        eval_case: EvalCase,
        *,
        workspace_root: Path,
        output_dir: Path,
    ) -> EvalCaseResult:
        replay_result = await self._replay_runner.replay_bundle_file(
            eval_case.bundle_path,
            workspace_root=workspace_root,
        )
        relevant_mismatches, ignored_mismatches = _partition_mismatches(
            replay_result.mismatches,
            selected_invariants=set(eval_case.expectation.selected_invariants()),
        )
        replay_triage = replay_result.triage or build_replay_triage(replay_result)
        selected_invariant_interpretation = _selected_invariant_interpretation(
            replay_result,
            selected_invariants=list(eval_case.expectation.selected_invariants()),
            relevant_mismatches=relevant_mismatches,
            ignored_mismatches=ignored_mismatches,
        )
        case_result = EvalCaseResult(
            case_id=eval_case.case_id,
            title=eval_case.title,
            tags=list(eval_case.tags),
            owner=eval_case.release_contract.owner,
            capabilities=list(eval_case.release_contract.capabilities),
            severity=eval_case.release_contract.severity,
            verification_stages=list(eval_case.release_contract.verification_stages),
            baseline_refresh_policy=(
                eval_case.release_contract.baseline_refresh_policy
            ),
            selected_invariants=list(eval_case.expectation.selected_invariants()),
            replay_outcome=replay_result.outcome,
            replay_exit_code=_REPLAY_EXIT_CODES[replay_result.outcome],
            passed=_case_passed(replay_result, relevant_mismatches),
            message=_case_message(
                replay_result,
                triage_headline=replay_triage.headline,
                relevant_mismatches=relevant_mismatches,
                ignored_mismatches=ignored_mismatches,
                selected_invariant_interpretation=selected_invariant_interpretation,
            ),
            mismatches=list(replay_result.mismatches),
            relevant_mismatches=relevant_mismatches,
            ignored_mismatches=ignored_mismatches,
            first_relevant_mismatch=(
                relevant_mismatches[0] if relevant_mismatches else None
            ),
            triage_classification=replay_triage.classification,
            triage_headline=replay_triage.headline,
            triage_first_relevant_change=replay_triage.first_relevant_change,
            triage_drift_sources=list(replay_triage.drift_sources),
            triage_recommended_inspection_path=(
                replay_triage.recommended_inspection_path
            ),
            selected_invariant_interpretation=selected_invariant_interpretation,
            artifact_path=output_dir / f"{eval_case.case_id}.json",
        )
        case_result.artifact_path.write_text(
            json.dumps(
                {
                    **case_result.model_dump(mode="json"),
                    "replay_result": replay_result.model_dump(mode="json"),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return case_result


def _resolve_output_dir(workspace_root: Path, *, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir.resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (workspace_root / ".glassbox" / "evals" / timestamp).resolve()


def _refresh_output_dir(workspace_root: Path, *, output_dir: Path) -> None:
    managed_root = (workspace_root / ".glassbox" / "evals").resolve()
    if not output_dir.is_relative_to(managed_root):
        raise ValueError(
            "--refresh-output-dir requires an output directory under .glassbox/evals"
        )
    if not output_dir.exists():
        return
    for child in output_dir.iterdir():
        if child.is_file() and child.suffix == ".json":
            child.unlink()


def _partition_mismatches(
    mismatches: list[str],
    *,
    selected_invariants: set[EvalInvariant],
) -> tuple[list[str], list[str]]:
    relevant_mismatches: list[str] = []
    ignored_mismatches: list[str] = []
    for mismatch in mismatches:
        invariant = _mismatch_invariant(mismatch)
        if invariant is None or invariant in selected_invariants:
            relevant_mismatches.append(mismatch)
        else:
            ignored_mismatches.append(mismatch)
    return relevant_mismatches, ignored_mismatches


def _mismatch_invariant(mismatch: str) -> EvalInvariant | None:
    invariant, separator, suffix = mismatch.partition(" drift")
    if separator and invariant in {
        "transcript",
        "tool_calls",
        "approvals",
        "questions",
        "event_families",
        "final_state",
    }:
        return cast(EvalInvariant, invariant)
    return None


def _case_passed(
    replay_result: ReplayResult,
    relevant_mismatches: list[str],
) -> bool:
    if replay_result.outcome == "exact_match":
        return True
    if replay_result.outcome == "behavioral_drift":
        return not relevant_mismatches
    return False


def _case_message(
    replay_result: ReplayResult,
    *,
    triage_headline: str,
    relevant_mismatches: list[str],
    ignored_mismatches: list[str],
    selected_invariant_interpretation: str | None,
) -> str | None:
    if replay_result.outcome != "behavioral_drift":
        return replay_result.message
    if not relevant_mismatches and selected_invariant_interpretation is not None:
        return selected_invariant_interpretation
    if relevant_mismatches and triage_headline.strip() != "":
        return triage_headline
    if not relevant_mismatches and ignored_mismatches:
        return selected_invariant_interpretation
    return replay_result.message


def _selected_invariant_interpretation(
    replay_result: ReplayResult,
    *,
    selected_invariants: list[EvalInvariant],
    relevant_mismatches: list[str],
    ignored_mismatches: list[str],
) -> str | None:
    if not selected_invariants:
        return None
    if replay_result.outcome == "exact_match":
        return "selected invariants matched with no observed drift"
    if replay_result.outcome != "behavioral_drift":
        return None
    if not relevant_mismatches and ignored_mismatches:
        return "selected invariants matched; ignored drift was limited to " + ", ".join(
            ignored_mismatches
        )
    if relevant_mismatches:
        return "selected invariants failed on " + ", ".join(relevant_mismatches)
    return "selected invariants matched"


def _outcome_counts(
    case_results: list[EvalCaseResult],
) -> dict[ReplayOutcome, int]:
    outcome_counts: dict[ReplayOutcome, int] = {
        "exact_match": 0,
        "behavioral_drift": 0,
        "manifest_drift": 0,
        "unsupported_session": 0,
        "replay_failure": 0,
    }
    for case_result in case_results:
        outcome_counts[case_result.replay_outcome] += 1
    return outcome_counts


def _suite_exit_code(case_results: list[EvalCaseResult]) -> int:
    failing_results = [
        case_result for case_result in case_results if not case_result.passed
    ]
    if not failing_results:
        return 0

    failing_outcomes = {case_result.replay_outcome for case_result in failing_results}
    for outcome in (
        "replay_failure",
        "unsupported_session",
        "manifest_drift",
        "behavioral_drift",
    ):
        if outcome in failing_outcomes:
            return _REPLAY_EXIT_CODES[outcome]
    return 1


def _profile_id(profile: EvalProfileDefinition | None) -> str | None:
    if profile is None:
        return None
    return profile.profile_id


def _profile_title(profile: EvalProfileDefinition | None) -> str | None:
    if profile is None:
        return None
    return profile.title


def _profile_stage(
    profile: EvalProfileDefinition | None,
) -> EvalVerificationStage | None:
    if profile is None:
        return None
    return profile.verification_stage
