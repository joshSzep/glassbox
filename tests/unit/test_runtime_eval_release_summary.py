"""Focused tests for eval release-signoff aggregation and summaries."""

from __future__ import annotations

from pathlib import Path

from glassbox.runtime.eval_coverage import EvalCoverageAuditResult
from glassbox.runtime.eval_runner import EvalCaseResult
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.eval_summary import EvalReleaseSignoffProfileInput
from glassbox.runtime.eval_summary import build_eval_release_signoff_report
from glassbox.runtime.eval_summary import build_eval_release_signoff_summary
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalVerificationStage
from glassbox.runtime.replay import ReplayOutcome


def test_build_eval_release_signoff_report_aggregates_profiles() -> None:
    artifact_root = Path("/tmp/signoff")
    output_dir = artifact_root / "profiles" / "release-candidate"
    summary_path = output_dir / "summary.json"
    suite_result = _suite_result(
        cases=[
            _case_result(
                case_id="release.flow",
                replay_outcome="exact_match",
                passed=True,
                owner="runtime.release",
                capabilities=["approval_flow"],
                severity="high",
                artifact_path=output_dir / "release.flow.json",
            )
        ],
        profile_id="release-candidate",
        profile_title="Release candidate",
        verification_stage="release-candidate",
        output_dir=output_dir,
        summary_path=summary_path,
        covered_capability_ids=["approval_flow", "replay_portability"],
        uncovered_release_critical_capability_ids=[],
    )

    report = build_eval_release_signoff_report(
        workspace_root=Path("/workspace/glassbox"),
        requested_profile_ids=["release-candidate"],
        tag_filters=["release"],
        profile_inputs=[
            EvalReleaseSignoffProfileInput(
                profile=_profile_definition(
                    profile_id="release-candidate",
                    title="Release candidate",
                    verification_stage="release-candidate",
                    blocking=True,
                    tags=["release"],
                ),
                eval_cases=[
                    _eval_case(
                        case_id="release.flow",
                        severity="high",
                        capabilities=["approval_flow"],
                        baseline_history=[
                            {
                                "operation": "refresh",
                                "recorded_at": "2026-02-10T00:00:00Z",
                                "source_session_id": (
                                    "00000000-0000-0000-0000-000000000002"
                                ),
                                "rationale": "Refresh after contract review",
                            }
                        ],
                    )
                ],
                suite_result=suite_result,
            )
        ],
        skipped_profiles=[],
        artifact_root=artifact_root,
    )

    assert report.status == "passed"
    assert report.contract_satisfied is True
    assert report.covered_capability_count == 2
    assert report.uncovered_release_critical_capability_ids == []
    assert report.latest_baseline_case_id == "release.flow"
    assert report.profiles[0].summary_artifact_path == (
        "profiles/release-candidate/summary.json"
    )
    assert report.profiles[0].cases[0].artifact_path == (
        "profiles/release-candidate/release.flow.json"
    )


def test_build_eval_release_signoff_summary_surfaces_attention_needed() -> None:
    artifact_root = Path("/tmp/signoff")
    output_dir = artifact_root / "profiles" / "release-candidate"
    summary_path = output_dir / "summary.json"
    suite_result = _suite_result(
        cases=[
            _case_result(
                case_id="release.blocking",
                replay_outcome="manifest_drift",
                passed=False,
                owner="runtime.release",
                capabilities=["approval_flow"],
                severity="critical",
                triage_headline="prepared turn drifted before model execution",
                artifact_path=output_dir / "release.blocking.json",
            )
        ],
        profile_id="release-candidate",
        profile_title="Release candidate",
        verification_stage="release-candidate",
        output_dir=output_dir,
        summary_path=summary_path,
        covered_capability_ids=[],
        uncovered_release_critical_capability_ids=["approval_flow"],
    )

    report = build_eval_release_signoff_report(
        workspace_root=Path("/workspace/glassbox"),
        requested_profile_ids=["release-candidate"],
        tag_filters=["release"],
        profile_inputs=[
            EvalReleaseSignoffProfileInput(
                profile=_profile_definition(
                    profile_id="release-candidate",
                    title="Release candidate",
                    verification_stage="release-candidate",
                    blocking=True,
                    tags=["release"],
                ),
                eval_cases=[
                    _eval_case(case_id="release.blocking", severity="critical")
                ],
                suite_result=suite_result,
            )
        ],
        skipped_profiles=[],
        artifact_root=artifact_root,
    )

    summary = build_eval_release_signoff_summary(report)

    assert "- Status: `failed`" in summary
    assert "### Attention Needed" in summary
    assert "`release-candidate`: `failed`." in summary
    assert "`release.blocking`: `manifest_drift`" in summary


def _suite_result(
    *,
    cases: list[EvalCaseResult],
    profile_id: str,
    profile_title: str,
    verification_stage: EvalVerificationStage,
    output_dir: Path,
    summary_path: Path,
    covered_capability_ids: list[str],
    uncovered_release_critical_capability_ids: list[str],
) -> EvalSuiteResult:
    outcome_counts: dict[ReplayOutcome, int] = {
        "exact_match": sum(1 for case in cases if case.replay_outcome == "exact_match"),
        "behavioral_drift": sum(
            1 for case in cases if case.replay_outcome == "behavioral_drift"
        ),
        "manifest_drift": sum(
            1 for case in cases if case.replay_outcome == "manifest_drift"
        ),
        "unsupported_session": sum(
            1 for case in cases if case.replay_outcome == "unsupported_session"
        ),
        "replay_failure": sum(
            1 for case in cases if case.replay_outcome == "replay_failure"
        ),
    }
    exit_code = 11 if any(not case.passed for case in cases) else 0

    return EvalSuiteResult(
        workspace_root=Path("/workspace/glassbox"),
        output_dir=output_dir,
        summary_path=summary_path,
        profile_id=profile_id,
        profile_title=profile_title,
        profile_verification_stage=verification_stage,
        profile_budget=None,
        coverage_audit=EvalCoverageAuditResult.model_validate(
            {
                "profile_id": profile_id,
                "profile_title": profile_title,
                "verification_stage": verification_stage,
                "audited_case_ids": [case.case_id for case in cases],
                "capability_count": 2,
                "covered_capability_count": len(covered_capability_ids),
                "uncovered_capability_count": 2 - len(covered_capability_ids),
                "uncovered_release_critical_capability_ids": (
                    uncovered_release_critical_capability_ids
                ),
                "unmapped_case_ids": [],
                "redundant_case_ids": [],
                "capability_statuses": [
                    {
                        "capability_id": "replay_portability",
                        "title": "Replay portability",
                        "criticality": "release-critical",
                        "verification_stages": [verification_stage],
                        "coverage_mode": "single_case",
                        "expected_case_ids": [],
                        "selected_case_ids": [],
                        "covered": "replay_portability" in covered_capability_ids,
                    },
                    {
                        "capability_id": "approval_flow",
                        "title": "Approval flow",
                        "criticality": "release-critical",
                        "verification_stages": [verification_stage],
                        "coverage_mode": "single_case",
                        "expected_case_ids": [],
                        "selected_case_ids": [],
                        "covered": "approval_flow" in covered_capability_ids,
                    },
                ],
            }
        ),
        selected_case_count=len(cases),
        passed_case_count=sum(1 for case in cases if case.passed),
        failed_case_count=sum(1 for case in cases if not case.passed),
        exit_code=exit_code,
        outcome_counts=outcome_counts,
        cases=cases,
    )


def _case_result(
    *,
    case_id: str,
    replay_outcome: ReplayOutcome,
    passed: bool,
    owner: str,
    capabilities: list[str],
    severity: EvalCaseSeverity,
    artifact_path: Path,
    triage_headline: str | None = None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case_id,
        title=case_id,
        tags=["release"],
        owner=owner,
        capabilities=capabilities,
        severity=severity,
        verification_stages=["release-candidate"],
        baseline_refresh_policy="review_required",
        selected_invariants=[],
        replay_outcome=replay_outcome,
        replay_exit_code=0 if replay_outcome == "exact_match" else 11,
        passed=passed,
        message=None,
        mismatches=[],
        relevant_mismatches=[],
        ignored_mismatches=[],
        first_relevant_mismatch=None,
        triage_classification=None,
        triage_headline=triage_headline,
        triage_first_relevant_change=None,
        triage_drift_sources=[],
        triage_recommended_inspection_path=None,
        selected_invariant_interpretation=None,
        artifact_path=artifact_path,
    )


def _profile_definition(
    *,
    profile_id: str,
    title: str,
    verification_stage: EvalVerificationStage,
    blocking: bool,
    tags: list[str],
) -> EvalProfileDefinition:
    return EvalProfileDefinition.model_validate(
        {
            "profile_id": profile_id,
            "title": title,
            "track": "deterministic",
            "verification_stage": verification_stage,
            "blocking": blocking,
            "tags": tags,
        }
    )


def _eval_case(
    *,
    case_id: str,
    severity: EvalCaseSeverity,
    capabilities: list[str] | None = None,
    baseline_history: list[dict[str, object]] | None = None,
) -> EvalCase:
    return EvalCase.model_validate(
        {
            "manifest_version": 1,
            "case_id": case_id,
            "title": case_id,
            "case_path": Path("/workspace/glassbox/evals/cases") / f"{case_id}.json",
            "bundle_path": Path("evals/bundles") / f"{case_id}.json",
            "tags": ["release"],
            "notes": None,
            "expectation": {"mode": "exact_match", "invariants": []},
            "release_contract": {
                "owner": "runtime.release",
                "capabilities": capabilities or [],
                "severity": severity,
                "verification_stages": ["release-candidate"],
                "baseline_refresh_policy": "review_required",
            },
            "baseline_history": baseline_history or [],
        }
    )
