"""Replay and eval report formatting helpers for the CLI."""

from __future__ import annotations

from pathlib import Path

from glassbox.runtime.eval_baselines import format_eval_baseline_update_report
from glassbox.runtime.eval_coverage import build_eval_coverage_summary_lines
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.replay import ReplayResult

_REPLAY_EXIT_CODES = {
    "exact_match": 0,
    "behavioral_drift": 10,
    "manifest_drift": 11,
    "unsupported_session": 12,
    "replay_failure": 13,
}


def _print_replay_report(result: ReplayResult) -> None:
    session_id = result.source_session_id
    if session_id is not None:
        print(f"Replay session {session_id}")
    print(f"Outcome: {_format_replay_outcome(result.outcome)}")

    if result.message:
        print(f"Summary: {result.message}")

    if result.triage is not None:
        if result.triage.classification != result.outcome:
            print(
                "Classification: "
                + _format_replay_outcome(result.triage.classification)
            )
        if result.triage.headline not in {"", result.message, None}:
            print(f"Triage: {result.triage.headline}")
        if result.triage.first_relevant_change not in {None, result.triage.headline}:
            print(f"First change: {result.triage.first_relevant_change}")
        if result.triage.drift_sources:
            print("Drift sources: " + ", ".join(result.triage.drift_sources))
        if result.triage.recommended_inspection_path:
            print(f"Next inspect: {result.triage.recommended_inspection_path}")

    if result.outcome == "exact_match":
        print(
            "Matched: transcript, tool calls, approval flow, question flow, "
            "event families, and final state"
        )
        return

    if result.mismatches:
        print("Mismatches:")
        for mismatch in result.mismatches:
            print(f"  - {mismatch}")

    for detail_line in _replay_detail_lines(result):
        print(detail_line)


def _print_eval_suite_report(result: EvalSuiteResult) -> None:
    print(f"Eval workspace {result.workspace_root}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.profile_verification_stage})")
    if result.profile_budget is not None:
        print(
            f"Budget: {result.profile_budget.status} "
            f"({result.profile_budget.enforcement})"
        )
    print(f"Selected cases: {result.selected_case_count}")
    print(f"Passed: {result.passed_case_count}")
    print(f"Failed: {result.failed_case_count}")
    print("Outcomes:")
    for outcome, count in result.outcome_counts.items():
        print(f"  - {_format_replay_outcome(outcome)}: {count}")
    print(f"Artifacts: {result.output_dir}")
    if result.coverage_audit is not None:
        for line in build_eval_coverage_summary_lines(result.coverage_audit):
            print(line)
    if result.profile_budget is not None:
        profile_budget = result.profile_budget
        print("Profile budget:")
        print(
            "  Selected cases: "
            f"{profile_budget.selected_case_count}"
            + _format_budget_limit(profile_budget.max_selected_case_count)
        )
        print(
            "  Selected-invariant cases: "
            f"{profile_budget.selected_invariant_case_count}"
            + _format_budget_limit(profile_budget.max_selected_invariant_case_count)
        )
        print(
            "  Recorded model calls: "
            f"{profile_budget.recorded_model_call_count}"
            + _format_budget_limit(profile_budget.max_recorded_model_call_count)
        )
        print(
            "  Case artifact bytes: "
            f"{profile_budget.case_artifact_bytes}"
            + _format_budget_limit(profile_budget.max_case_artifact_bytes)
        )
        print(
            "  Unsupported cases: "
            f"{profile_budget.unsupported_case_count}"
            + (" (allowed)" if profile_budget.allow_unsupported_cases else "")
        )
        print(
            "  Advisory cases: "
            f"{profile_budget.advisory_case_count}"
            + (" (allowed)" if profile_budget.allow_advisory_cases else "")
        )
        if profile_budget.promotion_policy:
            print("  Promotion policy: " + profile_budget.promotion_policy)
        if profile_budget.demotion_policy:
            print("  Demotion policy: " + profile_budget.demotion_policy)
        if profile_budget.violations:
            print("  Budget violations:")
            for violation in profile_budget.violations:
                print("    - " + violation.message)
    print("Cases:")
    for case_result in result.cases:
        status = "passed" if case_result.passed else "failed"
        print(
            f"  - {case_result.case_id}: "
            f"{_format_replay_outcome(case_result.replay_outcome)} ({status})"
        )
        if (
            case_result.triage_classification is not None
            and case_result.triage_classification != case_result.replay_outcome
        ):
            print(
                "    Classification: "
                + _format_replay_outcome(case_result.triage_classification)
            )
        if case_result.triage_headline:
            print(f"    Triage: {case_result.triage_headline}")
        if case_result.message:
            print(f"    Summary: {case_result.message}")
        if case_result.first_relevant_mismatch:
            print("    First relevant mismatch: " + case_result.first_relevant_mismatch)
        elif case_result.triage_first_relevant_change:
            print(
                "    First reported change: " + case_result.triage_first_relevant_change
            )
        if case_result.relevant_mismatches:
            print(
                "    Relevant mismatches: " + ", ".join(case_result.relevant_mismatches)
            )
        if case_result.ignored_mismatches:
            print(
                "    Ignored mismatches: " + ", ".join(case_result.ignored_mismatches)
            )
        if case_result.selected_invariant_interpretation:
            print(
                "    Selected invariants: "
                + case_result.selected_invariant_interpretation
            )
        if case_result.triage_drift_sources:
            print("    Drift sources: " + ", ".join(case_result.triage_drift_sources))
        if case_result.triage_recommended_inspection_path:
            print("    Next inspect: " + case_result.triage_recommended_inspection_path)
        print(f"    Artifact: {case_result.artifact_path}")


def _print_eval_coverage_audit(*, workspace_root: Path, result) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.verification_stage})")
    for line in build_eval_coverage_summary_lines(result):
        print(line)
    if result.uncovered_release_critical_capability_ids:
        print("Uncovered release-critical capability details:")
        for capability_id in result.uncovered_release_critical_capability_ids:
            print(f"  - {capability_id}")
    if result.unmapped_case_ids:
        print("Unmapped case details:")
        for case_id in result.unmapped_case_ids:
            print(f"  - {case_id}")


def _print_eval_baseline_update(report) -> None:
    for line in format_eval_baseline_update_report(report):
        print(line)


def _print_eval_profiles(*, workspace_root: Path, profiles) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    if not profiles:
        print("No eval profiles matched the requested filter")
        return
    print("Profiles:")
    for profile in profiles:
        print(
            f"  - {profile.profile_id}: {profile.track}, "
            f"{profile.verification_stage}, "
            f"{'blocking' if profile.blocking else 'non-blocking'}"
        )
        if profile.tags:
            print("    Tags: " + ", ".join(profile.tags))
        if profile.case_ids:
            print("    Case IDs: " + ", ".join(profile.case_ids))
        if profile.description:
            print("    Description: " + profile.description)


def _format_budget_limit(limit: int | None) -> str:
    if limit is None:
        return " (no configured limit)"
    return f" / {limit}"


def _replay_detail_lines(result: ReplayResult) -> list[str]:
    if result.baseline is None or result.replay is None:
        return []

    detail_lines: list[str] = []
    mismatch_set = set(result.mismatches)
    if "transcript drift" in mismatch_set:
        detail_lines.append(
            "Transcript: baseline "
            f"{len(result.baseline.transcript)} message(s), replay "
            f"{len(result.replay.transcript)} message(s)"
        )
    if "tool_calls drift" in mismatch_set:
        detail_lines.append(
            "Tool calls: baseline "
            f"{len(result.baseline.tool_calls)} call(s), replay "
            f"{len(result.replay.tool_calls)} call(s)"
        )
    if "approvals drift" in mismatch_set:
        detail_lines.append(
            "Approvals: baseline "
            f"{len(result.baseline.approvals)} item(s), replay "
            f"{len(result.replay.approvals)} item(s)"
        )
    if "questions drift" in mismatch_set:
        detail_lines.append(
            "Questions: baseline "
            f"{len(result.baseline.questions)} item(s), replay "
            f"{len(result.replay.questions)} item(s)"
        )
    if "event_families drift" in mismatch_set:
        detail_lines.append(
            "Event families: baseline "
            f"{len(result.baseline.event_families)} event(s), replay "
            f"{len(result.replay.event_families)} event(s)"
        )
    if "final_state drift" in mismatch_set:
        detail_lines.append(
            "Final state: baseline "
            f"{result.baseline.final_state.status}, replay "
            f"{result.replay.final_state.status}"
        )
    return detail_lines


def _replay_result_payload(result: ReplayResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["exit_code"] = _replay_exit_code(result)
    return payload


def _replay_exit_code(result: ReplayResult) -> int:
    return _REPLAY_EXIT_CODES[result.outcome]


def _format_replay_outcome(outcome: str) -> str:
    return outcome.replace("_", " ")
