"""Eval suite payload construction and job-summary rendering."""

import json
from pathlib import Path
from typing import Any

from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.eval_summary_annotations import annotation_level_for_case
from glassbox.runtime.eval_summary_annotations import artifact_display_path
from glassbox.runtime.eval_summary_annotations import normalized_artifact_root


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

    normalized_root = normalized_artifact_root(artifact_root)
    return {
        "profile_id": result.profile_id,
        "profile_title": result.profile_title,
        "profile_verification_stage": result.profile_verification_stage,
        "profile_budget": (
            result.profile_budget.model_dump(mode="json")
            if result.profile_budget is not None
            else None
        ),
        "coverage_audit": (
            result.coverage_audit.model_dump(mode="json")
            if result.coverage_audit is not None
            else None
        ),
        "suite_status": "failed" if result.exit_code else "passed",
        "budget_status": (
            result.profile_budget.status if result.profile_budget is not None else None
        ),
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
                "owner": case.owner,
                "capabilities": list(case.capabilities),
                "passed": case.passed,
                "replay_outcome": case.replay_outcome,
                "severity": case.severity,
                "verification_stages": list(case.verification_stages),
                "baseline_refresh_policy": case.baseline_refresh_policy,
                "annotation_level": annotation_level_for_case(case),
                "artifact_path": artifact_display_path(
                    artifact_root=normalized_root,
                    output_dir=result.output_dir,
                    artifact_path=case.artifact_path,
                ),
                "triage_classification": case.triage_classification,
                "triage_headline": case.triage_headline,
                "triage_first_relevant_change": case.triage_first_relevant_change,
                "triage_drift_sources": list(case.triage_drift_sources),
                "recommended_inspection_path": case.triage_recommended_inspection_path,
                "first_relevant_mismatch": case.first_relevant_mismatch,
                "selected_invariant_interpretation": (
                    case.selected_invariant_interpretation
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
    ]
    if payload["profile_id"] is not None:
        lines.extend(
            [
                f"- Profile: `{payload['profile_id']}`",
                f"- Profile title: `{payload['profile_title']}`",
                f"- Verification stage: `{payload['profile_verification_stage']}`",
            ]
        )

    profile_budget = payload["profile_budget"]
    unsupported_limit = None
    advisory_limit = None
    if profile_budget is not None:
        unsupported_limit = (
            "allowed" if profile_budget["allow_unsupported_cases"] else "0"
        )
        advisory_limit = "allowed" if profile_budget["allow_advisory_cases"] else "0"
        lines.extend(
            [
                f"- Budget status: `{payload['budget_status']}`",
                f"- Budget enforcement: `{profile_budget['enforcement']}`",
            ]
        )

    lines.extend(
        [
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
    )
    for outcome, count in payload["outcome_counts"].items():
        lines.append(f"| `{outcome}` | `{count}` |")

    if profile_budget is not None:
        lines.extend(
            [
                "",
                "### Profile Budget",
                "",
                "| Measure | Actual | Limit |",
                "| --- | ---: | ---: |",
                "| `selected_case_count` | "
                f"`{profile_budget['selected_case_count']}` | "
                f"`{profile_budget['max_selected_case_count']}` |",
                "| `selected_invariant_case_count` | "
                f"`{profile_budget['selected_invariant_case_count']}` | "
                f"`{profile_budget['max_selected_invariant_case_count']}` |",
                "| `recorded_model_call_count` | "
                f"`{profile_budget['recorded_model_call_count']}` | "
                f"`{profile_budget['max_recorded_model_call_count']}` |",
                "| `case_artifact_bytes` | "
                f"`{profile_budget['case_artifact_bytes']}` | "
                f"`{profile_budget['max_case_artifact_bytes']}` |",
                "| `unsupported_case_count` | "
                f"`{profile_budget['unsupported_case_count']}` | "
                f"`{unsupported_limit}` |",
                "| `advisory_case_count` | "
                f"`{profile_budget['advisory_case_count']}` | "
                f"`{advisory_limit}` |",
            ]
        )
        if profile_budget["promotion_policy"] is not None:
            lines.append("- Promotion policy: " + profile_budget["promotion_policy"])
        if profile_budget["demotion_policy"] is not None:
            lines.append("- Demotion policy: " + profile_budget["demotion_policy"])
        if profile_budget["violations"]:
            lines.append("- Budget violations:")
            for violation in profile_budget["violations"]:
                lines.append(f"  - {violation['message']}")

    coverage_audit = payload["coverage_audit"]
    if coverage_audit is not None:
        lines.extend(
            [
                "",
                "### Capability Coverage",
                "",
                "- Covered capabilities: "
                f"`{coverage_audit['covered_capability_count']}` / "
                f"`{coverage_audit['capability_count']}`",
                "- Uncovered capabilities: "
                f"`{coverage_audit['uncovered_capability_count']}`",
            ]
        )
        if coverage_audit["uncovered_release_critical_capability_ids"]:
            lines.append(
                "- Uncovered release-critical capabilities: `"
                + "`, `".join(
                    coverage_audit["uncovered_release_critical_capability_ids"]
                )
                + "`"
            )
        if coverage_audit["unmapped_case_ids"]:
            lines.append(
                "- Unmapped cases: `"
                + "`, `".join(coverage_audit["unmapped_case_ids"])
                + "`"
            )
        if coverage_audit["redundant_case_ids"]:
            lines.append(
                "- Redundant cases: `"
                + "`, `".join(coverage_audit["redundant_case_ids"])
                + "`"
            )

    lines.extend(
        [
            "",
            "### Cases",
            "",
            "| Case | Owner | Status | Outcome | Severity | Artifact |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in payload["cases"]:
        case_status = "passed" if case["passed"] else "failed"
        owner = case["owner"] or "-"
        lines.append(
            "| "
            f"`{case['case_id']}` | `{owner}` | `{case_status}` | "
            f"`{case['replay_outcome']}` | "
            f"`{case['severity']}` | `{case['artifact_path']}` |"
        )

    failed_cases = [case for case in payload["cases"] if not case["passed"]]
    if failed_cases:
        lines.extend(["", "### Failed Cases", ""])
        for case in failed_cases:
            detail = (
                case["triage_headline"]
                or case["message"]
                or "See retained case artifact for details."
            )
            owner_suffix = f" owner `{case['owner']}`" if case["owner"] else ""
            first_change = (
                case["first_relevant_mismatch"] or case["triage_first_relevant_change"]
            )
            next_inspect = case["recommended_inspection_path"]
            classification_suffix = ""
            if case["triage_classification"] not in {None, case["replay_outcome"]}:
                classification_suffix = (
                    f" classified as `{case['triage_classification']}`"
                )
            lines.append(
                f"- `{case['case_id']}`: `{case['replay_outcome']}` "
                f"(`{case['severity']}`{owner_suffix}){classification_suffix} at "
                f"`{case['artifact_path']}`. {detail}"
            )
            if first_change is not None:
                lines[-1] += f" First change: `{first_change}`."
            if next_inspect is not None:
                lines[-1] += f" Next inspect: {next_inspect}"

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
