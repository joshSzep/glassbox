"""Unit tests for automation-facing eval summary formatting."""

import json
from pathlib import Path

from glassbox.runtime.eval_coverage import EvalCoverageAuditResult
from glassbox.runtime.eval_inputs import load_eval_suite_result
from glassbox.runtime.eval_runner import EvalCaseResult
from glassbox.runtime.eval_runner import EvalProfileBudgetHealth
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.eval_summary import build_eval_suite_annotations
from glassbox.runtime.eval_summary import build_eval_suite_job_summary
from glassbox.runtime.eval_summary import build_eval_suite_summary_payload
from glassbox.runtime.eval_summary import format_github_actions_annotation
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.replay import ReplayOutcome


def test_build_eval_suite_job_summary_surfaces_counts_cases_and_artifacts() -> None:
    result = _suite_result(
        [
            _case_result(
                case_id="smoke.hello",
                replay_outcome="exact_match",
                passed=True,
            ),
            _case_result(
                case_id="manifest.case",
                replay_outcome="manifest_drift",
                passed=False,
                message="prepared turn no longer matches recorded manifest",
                triage_classification="manifest_drift",
                triage_headline="prepared turn drifted before model execution",
                triage_first_relevant_change=(
                    "prepared turn no longer matches recorded manifest"
                ),
                triage_recommended_inspection_path=(
                    "Inspect the recorded prepared turn manifest and the current "
                    "prompt and turn-context inputs."
                ),
            ),
        ]
    )

    summary = build_eval_suite_job_summary(
        result,
        artifact_name="push-smoke-evals-deadbeef",
        artifact_root=".glassbox/evals/push-smoke",
    )

    assert "- Selected cases: `2`" in summary
    assert "- Passed: `1`" in summary
    assert "- Failed: `1`" in summary
    assert "- Budget status: `violated`" in summary
    assert "### Profile Budget" in summary
    assert "- Covered capabilities: `1` / `2`" in summary
    assert "- Uncovered release-critical capabilities: `approval_flow`" in summary
    assert "| `manifest_drift` | `1` |" in summary
    assert (
        "| `manifest.case` | `runtime.replay` | `failed` | `manifest_drift` | `high` | "
        "`.glassbox/evals/push-smoke/manifest.case.json` |"
    ) in summary
    assert "prepared turn drifted before model execution" in summary
    assert (
        "First change: `prepared turn no longer matches recorded manifest`" in summary
    )
    assert "Next inspect: Inspect the recorded prepared turn manifest" in summary
    assert "push-smoke-evals-deadbeef" in summary
    assert (
        '"summary_artifact_path": ".glassbox/evals/push-smoke/summary.json"' in summary
    )


def test_build_eval_suite_annotations_marks_failed_cases_by_severity() -> None:
    result = _suite_result(
        [
            _case_result(
                case_id="behavior.case",
                replay_outcome="behavioral_drift",
                passed=False,
                message="transcript drift",
                severity="medium",
                triage_headline="behavioral drift detected in transcript",
                first_relevant_mismatch="transcript drift",
                triage_recommended_inspection_path=(
                    "Inspect transcript messages and the last recorded model "
                    "response in the retained replay artifact."
                ),
            ),
            _case_result(
                case_id="broken.case",
                replay_outcome="replay_failure",
                passed=False,
                message="missing replay bundle file",
                severity="high",
                triage_headline="missing replay bundle file",
                triage_recommended_inspection_path=(
                    "Inspect the replay bundle, retained replay artifacts, and "
                    "runtime error surface for missing or invalid inputs."
                ),
            ),
        ]
    )

    annotations = build_eval_suite_annotations(
        result,
        artifact_root=".glassbox/evals/push-smoke",
    )

    assert [annotation.level for annotation in annotations] == ["warning", "error"]
    assert annotations[0].title == "behavior.case: behavioral_drift"
    assert (
        annotations[0].message
        == "behavioral drift detected in transcript First change: transcript "
        "drift. Next inspect: Inspect transcript messages and the last recorded "
        "model response in the retained replay artifact.. Artifact: "
        ".glassbox/evals/push-smoke/behavior.case.json"
    )
    assert annotations[1].message == (
        "missing replay bundle file Next inspect: Inspect the replay bundle, "
        "retained replay artifacts, and runtime error surface for missing or "
        "invalid inputs.. Artifact: "
        ".glassbox/evals/push-smoke/broken.case.json"
    )


def test_build_eval_suite_summary_payload_includes_triage_fields() -> None:
    payload = build_eval_suite_summary_payload(
        _suite_result(
            [
                _case_result(
                    case_id="context.case",
                    replay_outcome="manifest_drift",
                    passed=False,
                    triage_classification="context_source_drift",
                    triage_headline=(
                        "recorded enriched context drifted for runtime_notes"
                    ),
                    triage_first_relevant_change=(
                        "recorded enriched context source drifted: runtime_notes"
                    ),
                    triage_drift_sources=["runtime_notes"],
                    triage_recommended_inspection_path=(
                        "Inspect runtime note inputs and replay enriched-context "
                        "capture for runtime_notes."
                    ),
                    first_relevant_mismatch=None,
                    selected_invariant_interpretation=None,
                )
            ]
        ),
        artifact_name="push-smoke-evals-deadbeef",
        artifact_root=".glassbox/evals/push-smoke",
    )

    case_payload = payload["cases"][0]

    assert case_payload["triage_classification"] == "context_source_drift"
    assert case_payload["triage_headline"] == (
        "recorded enriched context drifted for runtime_notes"
    )
    assert case_payload["triage_drift_sources"] == ["runtime_notes"]
    assert case_payload["recommended_inspection_path"] == (
        "Inspect runtime note inputs and replay enriched-context capture for "
        "runtime_notes."
    )
    assert payload["profile_budget"]["status"] == "violated"
    assert payload["budget_status"] == "violated"


def test_format_github_actions_annotation_escapes_control_characters() -> None:
    payload = build_eval_suite_summary_payload(
        _suite_result(
            [_case_result(case_id="smoke.hello")],
            include_profile_budget=False,
        ),
        artifact_name="push-smoke-evals-deadbeef",
        artifact_root=".glassbox/evals/push-smoke",
    )
    assert payload["suite_status"] == "passed"

    command = format_github_actions_annotation(
        build_eval_suite_annotations(
            _suite_result(
                [
                    _case_result(
                        case_id="manifest.case",
                        replay_outcome="manifest_drift",
                        passed=False,
                        message="line one\nline two",
                    )
                ]
            ),
            artifact_root=".glassbox/evals/push-smoke",
        )[0]
    )

    assert command.startswith("::error title=manifest.case: manifest_drift::")
    assert "%0A" in command


def test_load_eval_suite_result_round_trips_summary_json(tmp_path: Path) -> None:
    result = _suite_result([_case_result(case_id="smoke.hello")])
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    loaded = load_eval_suite_result(summary_path, EvalSuiteResult)

    assert loaded == result


def _suite_result(
    cases: list[EvalCaseResult],
    *,
    include_profile_budget: bool = True,
) -> EvalSuiteResult:
    output_dir = Path("/tmp/push-smoke")
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
    profile_budget = None
    if include_profile_budget:
        profile_budget = EvalProfileBudgetHealth.model_validate(
            {
                "status": "violated",
                "enforcement": "enforced",
                "max_selected_case_count": 1,
                "selected_case_count": len(cases),
                "max_selected_invariant_case_count": 0,
                "selected_invariant_case_count": 0,
                "max_recorded_model_call_count": 1,
                "recorded_model_call_count": 2,
                "max_case_artifact_bytes": 1024,
                "case_artifact_bytes": 2048,
                "allow_unsupported_cases": False,
                "unsupported_case_count": 0,
                "allow_advisory_cases": False,
                "advisory_case_count": 0,
                "promotion_policy": "Promote only deterministic low-cost smoke cases.",
                "demotion_policy": (
                    "Demote cases that bloat output or require relaxed invariants."
                ),
                "violations": [
                    {
                        "code": "selected_case_count",
                        "message": "selected case count 2 exceeds profile budget 1",
                        "actual": len(cases),
                        "limit": 1,
                        "case_ids": [case.case_id for case in cases],
                    }
                ],
            }
        )

    exit_code = 11 if any(not case.passed for case in cases) else 0
    if include_profile_budget and profile_budget is not None:
        exit_code = 14 if exit_code == 0 else exit_code

    return EvalSuiteResult(
        workspace_root=Path("/workspace/glassbox"),
        output_dir=output_dir,
        summary_path=output_dir / "summary.json",
        profile_id="push-confirmation",
        profile_title="Push confirmation",
        profile_verification_stage="push-time",
        profile_budget=profile_budget,
        coverage_audit=EvalCoverageAuditResult.model_validate(
            {
                "profile_id": "push-confirmation",
                "profile_title": "Push confirmation",
                "verification_stage": "push-time",
                "audited_case_ids": [case.case_id for case in cases],
                "capability_count": 2,
                "covered_capability_count": 1,
                "uncovered_capability_count": 1,
                "uncovered_release_critical_capability_ids": ["approval_flow"],
                "unmapped_case_ids": [],
                "redundant_case_ids": [],
                "capability_statuses": [
                    {
                        "capability_id": "replay_portability",
                        "title": "Replay portability",
                        "criticality": "release-critical",
                        "verification_stages": ["push-time"],
                        "coverage_mode": "single_case",
                        "expected_case_ids": [cases[0].case_id],
                        "selected_case_ids": [cases[0].case_id],
                        "covered": True,
                    },
                    {
                        "capability_id": "approval_flow",
                        "title": "Approval flow",
                        "criticality": "release-critical",
                        "verification_stages": ["push-time"],
                        "coverage_mode": "single_case",
                        "expected_case_ids": [],
                        "selected_case_ids": [],
                        "covered": False,
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
    replay_outcome: ReplayOutcome = "exact_match",
    passed: bool = True,
    message: str | None = None,
    severity: EvalCaseSeverity | None = None,
    first_relevant_mismatch: str | None = None,
    triage_classification: str | None = None,
    triage_headline: str | None = None,
    triage_first_relevant_change: str | None = None,
    triage_drift_sources: list[str] | None = None,
    triage_recommended_inspection_path: str | None = None,
    selected_invariant_interpretation: str | None = None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case_id,
        title=case_id,
        tags=["smoke"],
        owner="runtime.replay",
        capabilities=["replay_contract"],
        severity=severity or ("high" if not passed else "medium"),
        verification_stages=["push-time"],
        baseline_refresh_policy="review_required",
        selected_invariants=[],
        replay_outcome=replay_outcome,
        replay_exit_code=0 if replay_outcome == "exact_match" else 11,
        passed=passed,
        message=message,
        mismatches=[],
        relevant_mismatches=[],
        ignored_mismatches=[],
        first_relevant_mismatch=first_relevant_mismatch,
        triage_classification=triage_classification,
        triage_headline=triage_headline,
        triage_first_relevant_change=triage_first_relevant_change,
        triage_drift_sources=list(triage_drift_sources or []),
        triage_recommended_inspection_path=triage_recommended_inspection_path,
        selected_invariant_interpretation=selected_invariant_interpretation,
        artifact_path=Path("/tmp/push-smoke") / f"{case_id}.json",
    )
