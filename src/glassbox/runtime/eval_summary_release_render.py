"""Markdown rendering for release sign-off reports."""

import json

from glassbox.runtime.eval_summary_models import EvalReleaseSignoffReport


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
