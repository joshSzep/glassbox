"""Unit tests for automation-facing eval summary formatting."""

from __future__ import annotations

from pathlib import Path

from glassbox.runtime.eval_runner import EvalCaseResult, EvalSuiteResult
from glassbox.runtime.eval_summary import (
    build_eval_suite_annotations,
    build_eval_suite_job_summary,
    build_eval_suite_summary_payload,
    format_github_actions_annotation,
)
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
    assert "| `manifest_drift` | `1` |" in summary
    assert (
        "| `manifest.case` | `runtime.replay` | `failed` | `manifest_drift` | `high` | "
        "`.glassbox/evals/push-smoke/manifest.case.json` |"
    ) in summary
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
            ),
            _case_result(
                case_id="broken.case",
                replay_outcome="replay_failure",
                passed=False,
                message="missing replay bundle file",
                severity="high",
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
        == "transcript drift Artifact: .glassbox/evals/push-smoke/behavior.case.json"
    )
    assert annotations[1].message == (
        "missing replay bundle file Artifact: "
        ".glassbox/evals/push-smoke/broken.case.json"
    )


def test_format_github_actions_annotation_escapes_control_characters() -> None:
    payload = build_eval_suite_summary_payload(
        _suite_result([_case_result(case_id="smoke.hello")]),
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


def _suite_result(cases: list[EvalCaseResult]) -> EvalSuiteResult:
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
    return EvalSuiteResult(
        workspace_root=Path("/workspace/glassbox"),
        output_dir=output_dir,
        summary_path=output_dir / "summary.json",
        selected_case_count=len(cases),
        passed_case_count=sum(1 for case in cases if case.passed),
        failed_case_count=sum(1 for case in cases if not case.passed),
        exit_code=11 if any(not case.passed for case in cases) else 0,
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
        artifact_path=Path("/tmp/push-smoke") / f"{case_id}.json",
    )
