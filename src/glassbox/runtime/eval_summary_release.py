"""Release sign-off aggregation and summary rendering for eval reports."""

import json
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from glassbox.runtime.eval_runner import EvalCaseResult
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.eval_summary_annotations import artifact_display_path
from glassbox.runtime.eval_summary_models import EvalReleaseProfileStatus
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffCaseReport
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffProfileInput
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffProfileReport
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffReport
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffSkippedProfileInput
from glassbox.runtime.eval_summary_models import EvalReleaseSignoffStatus
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalCaseSeverity


def build_eval_release_signoff_report(
    *,
    workspace_root: Path,
    requested_profile_ids: list[str],
    tag_filters: list[str],
    profile_inputs: list[EvalReleaseSignoffProfileInput],
    skipped_profiles: list[EvalReleaseSignoffSkippedProfileInput],
    artifact_root: Path,
    generated_at: datetime | None = None,
) -> EvalReleaseSignoffReport:
    """Aggregate one or more named eval profiles into release sign-off evidence."""

    report_by_profile_id = {
        profile_input.profile.profile_id: build_release_profile_report(
            profile_input,
            artifact_root=artifact_root,
        )
        for profile_input in profile_inputs
    }
    report_by_profile_id.update(
        {
            skipped_profile.profile_id: build_skipped_profile_report(skipped_profile)
            for skipped_profile in skipped_profiles
        }
    )
    profile_reports = [
        report_by_profile_id[profile_id]
        for profile_id in requested_profile_ids
        if profile_id in report_by_profile_id
    ]

    severity_totals = zero_severity_totals()
    failed_severity_totals = zero_severity_totals()
    advisory_drift_case_count = 0
    unsupported_case_count = 0
    capability_map: dict[str, tuple[str, bool, bool]] = {}
    baseline_case_map: dict[str, EvalReleaseSignoffCaseReport] = {}

    for profile_report in profile_reports:
        advisory_drift_case_count += profile_report.advisory_drift_case_count
        unsupported_case_count += profile_report.unsupported_case_count
        merge_severity_totals(severity_totals, profile_report.severity_totals)
        merge_severity_totals(
            failed_severity_totals,
            profile_report.failed_severity_totals,
        )
        for case_report in profile_report.cases:
            baseline_case_map.setdefault(case_report.case_id, case_report)

    for profile_input in profile_inputs:
        coverage_audit = profile_input.suite_result.coverage_audit
        if coverage_audit is None:
            continue
        for capability in coverage_audit.capability_statuses:
            existing = capability_map.get(capability.capability_id)
            is_release_critical = capability.criticality == "release-critical"
            if existing is None:
                capability_map[capability.capability_id] = (
                    capability.title,
                    capability.covered,
                    is_release_critical,
                )
                continue
            capability_map[capability.capability_id] = (
                existing[0],
                existing[1] or capability.covered,
                existing[2] or is_release_critical,
            )

    uncovered_capability_ids = sorted(
        capability_id
        for capability_id, (
            _title,
            covered,
            _release_critical,
        ) in capability_map.items()
        if not covered
    )
    uncovered_release_critical_capability_ids = sorted(
        capability_id
        for capability_id, (_title, covered, release_critical) in capability_map.items()
        if not covered and release_critical
    )

    latest_case = extreme_baseline_case(
        list(baseline_case_map.values()),
        newest=True,
    )
    oldest_case = extreme_baseline_case(
        list(baseline_case_map.values()),
        newest=False,
    )
    cases_without_baseline_history = sorted(
        case.case_id
        for case in baseline_case_map.values()
        if case.baseline_history_count == 0
    )
    advisory_refresh_case_ids = sorted(
        case.case_id
        for case in baseline_case_map.values()
        if case.baseline_refresh_policy == "advisory"
    )

    has_blocking_skip = any(
        profile.status == "skipped" and profile.blocking is True
        for profile in profile_reports
    )
    has_failed_profile = any(profile.status == "failed" for profile in profile_reports)
    has_warning_profile = any(
        profile.status == "warning" for profile in profile_reports
    )
    has_non_blocking_skip = any(
        profile.status == "skipped" and profile.blocking is not True
        for profile in profile_reports
    )

    status: EvalReleaseSignoffStatus = "passed"
    if (
        has_failed_profile
        or has_blocking_skip
        or uncovered_release_critical_capability_ids
    ):
        status = "failed"
    elif has_warning_profile or has_non_blocking_skip:
        status = "warning"

    return EvalReleaseSignoffReport(
        workspace_root=workspace_root,
        generated_at=generated_at or datetime.now(UTC),
        requested_profile_ids=requested_profile_ids,
        tag_filters=tag_filters,
        status=status,
        contract_satisfied=status == "passed",
        exit_code=0 if status != "failed" else 1,
        profile_count=len(profile_reports),
        executed_profile_count=len(profile_inputs),
        skipped_profile_count=sum(
            1 for profile in profile_reports if profile.status == "skipped"
        ),
        advisory_drift_case_count=advisory_drift_case_count,
        unsupported_case_count=unsupported_case_count,
        capability_count=len(capability_map),
        covered_capability_count=sum(
            1
            for _capability_id, (
                _title,
                covered,
                _release_critical,
            ) in capability_map.items()
            if covered
        ),
        uncovered_capability_ids=uncovered_capability_ids,
        uncovered_release_critical_capability_ids=uncovered_release_critical_capability_ids,
        severity_totals=severity_totals,
        failed_severity_totals=failed_severity_totals,
        latest_baseline_recorded_at=(
            latest_case.latest_baseline_recorded_at if latest_case is not None else None
        ),
        latest_baseline_case_id=(
            latest_case.case_id if latest_case is not None else None
        ),
        latest_baseline_operation=(
            latest_case.latest_baseline_operation if latest_case is not None else None
        ),
        oldest_baseline_recorded_at=(
            oldest_case.latest_baseline_recorded_at if oldest_case is not None else None
        ),
        oldest_baseline_case_id=(
            oldest_case.case_id if oldest_case is not None else None
        ),
        oldest_baseline_operation=(
            oldest_case.latest_baseline_operation if oldest_case is not None else None
        ),
        cases_without_baseline_history=cases_without_baseline_history,
        advisory_refresh_case_ids=advisory_refresh_case_ids,
        profiles=profile_reports,
    )


def build_eval_release_signoff_summary(report: EvalReleaseSignoffReport) -> str:
    """Render a concise terminal and automation summary for release sign-off."""

    lines = [
        "## Release Sign-Off Report",
        "",
        f"- Status: `{report.status}`",
        f"- Release contract satisfied: `{report.contract_satisfied}`",
        f"- Requested profiles: `{'`, `'.join(report.requested_profile_ids)}`",
        f"- Generated at: `{report.generated_at.isoformat()}`",
        f"- Executed profiles: `{report.executed_profile_count}`",
        f"- Skipped profiles: `{report.skipped_profile_count}`",
        f"- Advisory drift cases: `{report.advisory_drift_case_count}`",
        f"- Unsupported cases: `{report.unsupported_case_count}`",
        (
            "- Covered capabilities: "
            f"`{report.covered_capability_count}` / `{report.capability_count}`"
        ),
    ]
    if report.tag_filters:
        lines.append("- Tag filters: `" + "`, `".join(report.tag_filters) + "`")
    if report.uncovered_release_critical_capability_ids:
        lines.append(
            "- Uncovered release-critical capabilities: `"
            + "`, `".join(report.uncovered_release_critical_capability_ids)
            + "`"
        )
    elif report.uncovered_capability_ids:
        lines.append(
            "- Uncovered capabilities: `"
            + "`, `".join(report.uncovered_capability_ids)
            + "`"
        )

    lines.extend(
        [
            "",
            "### Profiles",
            "",
            (
                "| Profile | Stage | Blocking | Status | Cases | Failures | "
                "Advisory Drift | Summary |"
            ),
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for profile in report.profiles:
        lines.append(
            "| "
            f"`{profile.profile_id}` | `{profile.verification_stage or '-'}` | "
            f"`{profile.blocking if profile.blocking is not None else '-'}` | "
            f"`{profile.status}` | `{profile.selected_case_count}` | "
            f"`{profile.failed_case_count}` | `{profile.advisory_drift_case_count}` | "
            f"`{profile.summary_artifact_path or profile.skip_reason or '-'}` |"
        )

    lines.extend(
        [
            "",
            "### Severity Totals",
            "",
            "| Severity | Cases | Failed |",
            "| --- | ---: | ---: |",
        ]
    )
    for severity in ("critical", "high", "medium", "low"):
        lines.append(
            "| "
            f"`{severity}` | `{report.severity_totals[severity]}` | "
            f"`{report.failed_severity_totals[severity]}` |"
        )

    lines.extend(["", "### Baseline Freshness", ""])
    if report.latest_baseline_recorded_at is not None:
        latest_case_id = report.latest_baseline_case_id or "unknown"
        lines.append(
            "- Latest baseline update: `"
            + latest_case_id
            + "` at `"
            + report.latest_baseline_recorded_at.isoformat()
            + "`"
            + (
                f" via `{report.latest_baseline_operation}`"
                if report.latest_baseline_operation is not None
                else ""
            )
        )
    if report.oldest_baseline_recorded_at is not None:
        oldest_case_id = report.oldest_baseline_case_id or "unknown"
        lines.append(
            "- Oldest retained baseline update: `"
            + oldest_case_id
            + "` at `"
            + report.oldest_baseline_recorded_at.isoformat()
            + "`"
            + (
                f" via `{report.oldest_baseline_operation}`"
                if report.oldest_baseline_operation is not None
                else ""
            )
        )
    if report.cases_without_baseline_history:
        lines.append(
            "- Cases without baseline history: `"
            + "`, `".join(report.cases_without_baseline_history)
            + "`"
        )
    if report.advisory_refresh_case_ids:
        lines.append(
            "- Advisory refresh policies: `"
            + "`, `".join(report.advisory_refresh_case_ids)
            + "`"
        )

    attention_profiles = [
        profile
        for profile in report.profiles
        if profile.status in {"failed", "warning", "skipped"}
    ]
    if attention_profiles:
        lines.extend(["", "### Attention Needed", ""])
        for profile in attention_profiles:
            lines.append(
                f"- `{profile.profile_id}`: `{profile.status}`. "
                f"{profile.decision_summary}"
            )
            if profile.cases and profile.status != "skipped":
                for case in profile.cases:
                    if case.passed and case.replay_outcome == "exact_match":
                        continue
                    lines.append(
                        "  - `"
                        + case.case_id
                        + "`: `"
                        + case.replay_outcome
                        + "` at `"
                        + case.artifact_path
                        + "`"
                        + (
                            f". {case.triage_headline}"
                            if case.triage_headline is not None
                            else ""
                        )
                    )

    lines.extend(
        [
            "",
            "<details>",
            "<summary>Machine-readable summary</summary>",
            "",
            "```json",
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True),
            "```",
            "</details>",
        ]
    )
    return "\n".join(lines) + "\n"


def build_release_profile_report(
    profile_input: EvalReleaseSignoffProfileInput,
    *,
    artifact_root: Path,
) -> EvalReleaseSignoffProfileReport:
    profile = profile_input.profile
    suite_result = profile_input.suite_result
    cases_by_id = {case.case_id: case for case in profile_input.eval_cases}
    case_reports = [
        build_release_case_report(
            case_result=case_result,
            eval_case=cases_by_id.get(case_result.case_id),
            artifact_root=artifact_root,
            output_dir=suite_result.output_dir,
        )
        for case_result in suite_result.cases
    ]
    advisory_drift_case_count = sum(
        1
        for case in suite_result.cases
        if case.passed and case.replay_outcome != "exact_match"
    )
    unsupported_case_count = sum(
        1 for case in suite_result.cases if case.replay_outcome == "unsupported_session"
    )
    budget_status = (
        suite_result.profile_budget.status
        if suite_result.profile_budget is not None
        else None
    )
    coverage_audit = suite_result.coverage_audit
    release_critical_gaps = (
        coverage_audit.uncovered_release_critical_capability_ids
        if coverage_audit is not None
        else []
    )
    uncovered_capability_ids = (
        [
            capability.capability_id
            for capability in coverage_audit.capability_statuses
            if not capability.covered
        ]
        if coverage_audit is not None
        else []
    )

    status: EvalReleaseProfileStatus = "passed"
    if suite_result.exit_code != 0 and profile.blocking:
        status = "failed"
    elif release_critical_gaps:
        status = "failed"
    elif (
        advisory_drift_case_count
        or suite_result.exit_code != 0
        or budget_status == "warning"
    ):
        status = "warning"
    elif coverage_audit is not None and coverage_audit.uncovered_capability_count:
        status = "warning"

    return EvalReleaseSignoffProfileReport(
        profile_id=profile.profile_id,
        profile_title=profile.title,
        verification_stage=profile.verification_stage,
        blocking=profile.blocking,
        status=status,
        decision_summary=profile_decision_summary(
            status=status,
            suite_result=suite_result,
            advisory_drift_case_count=advisory_drift_case_count,
            unsupported_case_count=unsupported_case_count,
            uncovered_capability_ids=uncovered_capability_ids,
            uncovered_release_critical_capability_ids=release_critical_gaps,
        ),
        selected_case_count=suite_result.selected_case_count,
        passed_case_count=suite_result.passed_case_count,
        failed_case_count=suite_result.failed_case_count,
        advisory_drift_case_count=advisory_drift_case_count,
        unsupported_case_count=unsupported_case_count,
        budget_status=budget_status,
        budget_enforcement=(
            suite_result.profile_budget.enforcement
            if suite_result.profile_budget is not None
            else None
        ),
        suite_exit_code=suite_result.exit_code,
        severity_totals=severity_totals_for_case_reports(case_reports),
        failed_severity_totals=failed_severity_totals_for_case_reports(case_reports),
        capability_count=(
            coverage_audit.capability_count if coverage_audit is not None else None
        ),
        covered_capability_count=(
            coverage_audit.covered_capability_count
            if coverage_audit is not None
            else None
        ),
        uncovered_capability_ids=uncovered_capability_ids,
        uncovered_release_critical_capability_ids=list(release_critical_gaps),
        output_dir=display_path(
            artifact_root=artifact_root,
            path=suite_result.output_dir,
        ),
        summary_artifact_path=display_path(
            artifact_root=artifact_root,
            path=suite_result.summary_path,
        ),
        cases=case_reports,
    )


def build_release_case_report(
    *,
    case_result: EvalCaseResult,
    eval_case: EvalCase | None,
    artifact_root: Path,
    output_dir: Path,
) -> EvalReleaseSignoffCaseReport:
    latest_history_entry = None
    baseline_history_count = 0
    if eval_case is not None:
        baseline_history_count = len(eval_case.baseline_history)
        if eval_case.baseline_history:
            latest_history_entry = max(
                eval_case.baseline_history,
                key=lambda entry: entry.recorded_at,
            )

    return EvalReleaseSignoffCaseReport(
        case_id=case_result.case_id,
        title=case_result.title,
        owner=case_result.owner,
        capabilities=list(case_result.capabilities),
        severity=case_result.severity,
        verification_stages=list(case_result.verification_stages),
        baseline_refresh_policy=case_result.baseline_refresh_policy,
        passed=case_result.passed,
        replay_outcome=case_result.replay_outcome,
        artifact_path=artifact_display_path(
            artifact_root=display_path(artifact_root=artifact_root, path=output_dir),
            output_dir=output_dir,
            artifact_path=case_result.artifact_path,
        ),
        triage_headline=case_result.triage_headline,
        triage_classification=case_result.triage_classification,
        message=case_result.message,
        baseline_history_count=baseline_history_count,
        latest_baseline_recorded_at=(
            latest_history_entry.recorded_at
            if latest_history_entry is not None
            else None
        ),
        latest_baseline_operation=(
            latest_history_entry.operation if latest_history_entry is not None else None
        ),
        latest_baseline_rationale=(
            latest_history_entry.rationale if latest_history_entry is not None else None
        ),
    )


def build_skipped_profile_report(
    skipped_profile: EvalReleaseSignoffSkippedProfileInput,
) -> EvalReleaseSignoffProfileReport:
    profile = skipped_profile.profile
    return EvalReleaseSignoffProfileReport(
        profile_id=skipped_profile.profile_id,
        profile_title=profile.title if profile is not None else None,
        verification_stage=(
            profile.verification_stage if profile is not None else None
        ),
        blocking=profile.blocking if profile is not None else None,
        status="skipped",
        decision_summary=skipped_profile.reason,
        skip_reason=skipped_profile.reason,
    )


def profile_decision_summary(
    *,
    status: EvalReleaseProfileStatus,
    suite_result: EvalSuiteResult,
    advisory_drift_case_count: int,
    unsupported_case_count: int,
    uncovered_capability_ids: list[str],
    uncovered_release_critical_capability_ids: list[str],
) -> str:
    details: list[str] = []
    if suite_result.failed_case_count:
        details.append(f"{suite_result.failed_case_count} failing case(s)")
    if advisory_drift_case_count:
        details.append(f"{advisory_drift_case_count} advisory drift case(s)")
    if unsupported_case_count:
        details.append(f"{unsupported_case_count} unsupported case(s)")
    if uncovered_release_critical_capability_ids:
        details.append(
            "uncovered release-critical capabilities: "
            + ", ".join(uncovered_release_critical_capability_ids)
        )
    elif uncovered_capability_ids:
        details.append("uncovered capabilities: " + ", ".join(uncovered_capability_ids))
    if (
        suite_result.profile_budget is not None
        and suite_result.profile_budget.violations
    ):
        details.append(f"budget status {suite_result.profile_budget.status}")

    if not details:
        if status == "passed":
            return "profile satisfied the curated replay and eval contract"
        return "profile completed without additional release-signoff notes"
    return "; ".join(details)


def severity_totals_for_case_reports(
    case_reports: list[EvalReleaseSignoffCaseReport],
) -> dict[EvalCaseSeverity, int]:
    totals = zero_severity_totals()
    for case_report in case_reports:
        totals[case_report.severity] += 1
    return totals


def failed_severity_totals_for_case_reports(
    case_reports: list[EvalReleaseSignoffCaseReport],
) -> dict[EvalCaseSeverity, int]:
    totals = zero_severity_totals()
    for case_report in case_reports:
        if not case_report.passed:
            totals[case_report.severity] += 1
    return totals


def zero_severity_totals() -> dict[EvalCaseSeverity, int]:
    return {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }


def merge_severity_totals(
    destination: dict[EvalCaseSeverity, int],
    source: dict[EvalCaseSeverity, int],
) -> None:
    for severity, count in source.items():
        destination[severity] += count


def extreme_baseline_case(
    case_reports: Sequence[EvalReleaseSignoffCaseReport],
    *,
    newest: bool,
) -> EvalReleaseSignoffCaseReport | None:
    candidates = [
        case_report
        for case_report in case_reports
        if case_report.latest_baseline_recorded_at is not None
    ]
    if not candidates:
        return None
    return (max if newest else min)(
        candidates,
        key=lambda case_report: cast(datetime, case_report.latest_baseline_recorded_at),
    )


def display_path(*, artifact_root: Path, path: Path) -> str:
    try:
        return path.relative_to(artifact_root).as_posix()
    except ValueError:
        return str(path)
