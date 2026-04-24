"""Formatting helpers for eval-suite summaries in automation contexts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from glassbox.runtime.eval_runner import EvalCaseResult, EvalSuiteResult
from glassbox.runtime.replay import ReplayOutcome

type AnnotationLevel = Literal["notice", "warning", "error"]


@dataclass(frozen=True)
class EvalAutomationAnnotation:
    """One GitHub Actions-friendly annotation for a replay/eval case."""

    level: AnnotationLevel
    title: str
    message: str


def load_eval_suite_result(summary_path: Path) -> EvalSuiteResult:
    """Load one structured eval suite summary from disk."""

    return EvalSuiteResult.model_validate_json(summary_path.read_text(encoding="utf-8"))


def build_eval_suite_summary_payload(
    result: EvalSuiteResult,
    *,
    artifact_name: str,
    artifact_root: str,
) -> dict[str, Any]:
    """Build a compact automation payload from one eval suite result."""

    normalized_root = _normalized_artifact_root(artifact_root)
    return {
        "suite_status": "failed" if result.failed_case_count else "passed",
        "selected_case_count": result.selected_case_count,
        "passed_case_count": result.passed_case_count,
        "failed_case_count": result.failed_case_count,
        "exit_code": result.exit_code,
        "outcome_counts": dict(result.outcome_counts),
        "artifact_name": artifact_name,
        "summary_artifact_path": f"{normalized_root}/summary.json",
        "cases": [
            {
                "case_id": case.case_id,
                "passed": case.passed,
                "replay_outcome": case.replay_outcome,
                "severity": _severity_for_case(case),
                "artifact_path": _artifact_display_path(
                    artifact_root=normalized_root,
                    output_dir=result.output_dir,
                    artifact_path=case.artifact_path,
                ),
                "message": case.message,
            }
            for case in result.cases
        ],
    }


def build_eval_suite_job_summary(
    result: EvalSuiteResult,
    *,
    artifact_name: str,
    artifact_root: str,
) -> str:
    """Render a GitHub Actions job summary for one eval suite result."""

    payload = build_eval_suite_summary_payload(
        result,
        artifact_name=artifact_name,
        artifact_root=artifact_root,
    )

    lines = [
        "## Push Smoke Eval Summary",
        "",
        f"- Suite status: `{payload['suite_status']}`",
        f"- Selected cases: `{payload['selected_case_count']}`",
        f"- Passed: `{payload['passed_case_count']}`",
        f"- Failed: `{payload['failed_case_count']}`",
        f"- Exit code: `{payload['exit_code']}`",
        f"- Uploaded artifact: `{payload['artifact_name']}`",
        f"- Summary JSON: `{payload['summary_artifact_path']}`",
        "",
        "### Outcome Totals",
        "",
        "| Outcome | Count |",
        "| --- | ---: |",
    ]
    for outcome, count in payload["outcome_counts"].items():
        lines.append(f"| `{outcome}` | `{count}` |")

    lines.extend(
        [
            "",
            "### Cases",
            "",
            "| Case | Status | Outcome | Severity | Artifact |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for case in payload["cases"]:
        case_status = "passed" if case["passed"] else "failed"
        lines.append(
            "| "
            f"`{case['case_id']}` | `{case_status}` | `{case['replay_outcome']}` | "
            f"`{case['severity']}` | `{case['artifact_path']}` |"
        )

    failed_cases = [case for case in payload["cases"] if not case["passed"]]
    if failed_cases:
        lines.extend(["", "### Failed Cases", ""])
        for case in failed_cases:
            detail = case["message"] or "See retained case artifact for details."
            lines.append(
                f"- `{case['case_id']}`: `{case['replay_outcome']}` "
                f"(`{case['severity']}`) at `{case['artifact_path']}`. {detail}"
            )

    lines.extend(
        [
            "",
            "<details>",
            "<summary>Machine-readable summary</summary>",
            "",
            "```json",
            json.dumps(payload, indent=2, sort_keys=True),
            "```",
            "</details>",
        ]
    )
    return "\n".join(lines) + "\n"


def build_eval_suite_annotations(
    result: EvalSuiteResult,
    *,
    artifact_root: str,
) -> list[EvalAutomationAnnotation]:
    """Build per-case annotations for quick automation triage."""

    normalized_root = _normalized_artifact_root(artifact_root)
    annotations: list[EvalAutomationAnnotation] = []
    for case in result.cases:
        if case.passed:
            continue
        artifact_path = _artifact_display_path(
            artifact_root=normalized_root,
            output_dir=result.output_dir,
            artifact_path=case.artifact_path,
        )
        detail = case.message or "See retained case artifact for details."
        annotations.append(
            EvalAutomationAnnotation(
                level=_severity_for_case(case),
                title=f"{case.case_id}: {case.replay_outcome}",
                message=f"{detail} Artifact: {artifact_path}",
            )
        )
    return annotations


def format_github_actions_annotation(annotation: EvalAutomationAnnotation) -> str:
    """Render one GitHub Actions workflow command for an annotation."""

    title = _escape_github_actions_value(annotation.title)
    message = _escape_github_actions_value(annotation.message)
    return f"::{annotation.level} title={title}::{message}"


def _normalized_artifact_root(artifact_root: str) -> str:
    return artifact_root.rstrip("/")


def _artifact_display_path(
    *,
    artifact_root: str,
    output_dir: Path,
    artifact_path: Path,
) -> str:
    try:
        relative_path = artifact_path.relative_to(output_dir)
    except ValueError:
        return str(artifact_path)
    return f"{artifact_root}/{relative_path.as_posix()}"


def _severity_for_case(case: EvalCaseResult) -> AnnotationLevel:
    severity_by_outcome: dict[ReplayOutcome, AnnotationLevel] = {
        "exact_match": "notice",
        "behavioral_drift": "warning",
        "manifest_drift": "error",
        "unsupported_session": "error",
        "replay_failure": "error",
    }
    return severity_by_outcome[case.replay_outcome]


def _escape_github_actions_value(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
