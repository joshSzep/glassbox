"""Replay and eval report formatting helpers for the CLI."""

from collections.abc import Sequence
from pathlib import Path

from glassbox.runtime.eval_baselines import format_eval_baseline_update_report
from glassbox.runtime.eval_coverage import build_eval_coverage_summary_lines
from glassbox.runtime.eval_recommendations import EvalLongRunSurfaceRecommendation
from glassbox.runtime.eval_recommendations import EvalRecommendationReport
from glassbox.runtime.eval_recommendations import EvalReleaseSurfaceRecommendation
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
        _print_optional_value("Owner", case_result.owner, indent="    ")
        _print_optional_joined_line(
            "Capabilities",
            case_result.capabilities,
            indent="    ",
        )
        _print_optional_joined_line(
            "Release stages",
            case_result.verification_stages,
            indent="    ",
        )
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


def _print_eval_profile(*, workspace_root: Path, profile) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    print(f"Profile: {profile.profile_id}")
    print(f"Title: {profile.title}")
    print(f"Track: {profile.track}")
    print(f"Verification stage: {profile.verification_stage}")
    print(f"Blocking: {'yes' if profile.blocking else 'no'}")
    if profile.description:
        print("Description: " + profile.description)
    if profile.tags:
        print("Tags: " + ", ".join(profile.tags))
    if profile.case_ids:
        print("Case IDs: " + ", ".join(profile.case_ids))
    if profile.budget is None:
        return

    budget = profile.budget
    print("Budget:")
    _print_optional_budget_value("  Max selected cases", budget.max_selected_case_count)
    _print_optional_budget_value(
        "  Max selected-invariant cases", budget.max_selected_invariant_case_count
    )
    _print_optional_budget_value(
        "  Max recorded model calls", budget.max_recorded_model_call_count
    )
    _print_optional_budget_value(
        "  Max case artifact bytes", budget.max_case_artifact_bytes
    )
    if budget.allow_unsupported_cases is not None:
        print(
            "  Allow unsupported cases: "
            + ("yes" if budget.allow_unsupported_cases else "no")
        )
    if budget.allow_advisory_cases is not None:
        print(
            "  Allow advisory cases: "
            + ("yes" if budget.allow_advisory_cases else "no")
        )
    if budget.promotion_policy:
        print("  Promotion policy: " + budget.promotion_policy)
    if budget.demotion_policy:
        print("  Demotion policy: " + budget.demotion_policy)


def _print_optional_budget_value(label: str, value: int | None) -> None:
    if value is not None:
        print(f"{label}: {value}")


def _print_eval_recommendations(result: EvalRecommendationReport) -> None:
    print(f"Eval workspace {result.workspace_root}")
    print("Touched paths:")
    for touched_path in result.touched_paths:
        print(f"  - {touched_path}")
    if result.matched_rule_ids:
        print("Matched impact rules: " + ", ".join(result.matched_rule_ids))
    if result.unmatched_paths:
        print("Unmatched paths:")
        for path in result.unmatched_paths:
            print(f"  - {path}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    if result.cheapest_next_command:
        print("Cheapest next command:")
        print(f"  - {result.cheapest_next_command}")
    if result.reason_groups:
        print("Reason groups:")
        for group in result.reason_groups:
            print(f"  - {group.title}")
            _print_optional_joined_line(
                "Cases", group.recommended_case_ids, indent="    "
            )
            _print_optional_joined_line(
                "Profiles", group.recommended_profile_ids, indent="    "
            )
            _print_optional_joined_line("Rules", group.rule_ids, indent="    ")
            _print_optional_joined_line("Paths", group.matched_paths, indent="    ")
            if group.summaries:
                print("    Reasons:")
                for summary in group.summaries:
                    print("      - " + summary)
            if group.release_gate_commands:
                print("    Full gates:")
                for command in group.release_gate_commands:
                    print("      - " + command)
    _print_release_surface_recommendations(result.release_surfaces)
    _print_long_run_surface_recommendations(result.long_run_surfaces)
    if result.cases:
        print("Recommended cases:")
        for case in result.cases:
            print(f"  - {case.case_id}: {case.title} ({case.confidence})")
            for reason in case.reasons:
                print(f"    Reason: {reason.summary}")
    else:
        print("Recommended cases: none")
    if result.profiles:
        print("Recommended profiles:")
        for profile in result.profiles:
            print(
                f"  - {profile.profile_id}: {profile.title} "
                f"({profile.confidence}, {profile.verification_stage}, "
                f"{profile.track})"
            )
            for reason in profile.reasons:
                print(f"    Reason: {reason.summary}")
    else:
        print("Recommended profiles: none")
    if result.recipes:
        print("Verification recipes:")
        for recipe in result.recipes:
            print(
                f"  - {recipe.recipe_id}: {recipe.title} "
                f"({recipe.confidence}, {recipe.source})"
            )
            _print_optional_joined_line("Paths", recipe.matched_paths, indent="    ")
            _print_optional_joined_line(
                "Components", recipe.component_ids, indent="    "
            )
            _print_optional_joined_line("Profiles", recipe.profile_ids, indent="    ")
            _print_optional_joined_line("Cases", recipe.case_ids, indent="    ")
            if recipe.notes:
                print(f"    Notes: {recipe.notes}")
            if recipe.limitations:
                print("    Limitations:")
                for limitation in recipe.limitations:
                    print("      - " + limitation)
            if recipe.commands:
                print("    Commands:")
                for command in recipe.commands:
                    print("      - " + command)
    else:
        print("Verification recipes: none")
    if result.test_targets:
        print("Likely test targets:")
        for target in result.test_targets:
            print(
                f"  - {target.target_id}: {target.title} "
                f"({target.confidence}, {target.source}, {target.freshness})"
            )
            _print_optional_joined_line("Paths", target.matched_paths, indent="    ")
            _print_optional_joined_line("Targets", target.target_paths, indent="    ")
            _print_optional_joined_line(
                "Components", target.component_ids, indent="    "
            )
            _print_optional_joined_line("Packages", target.package_ids, indent="    ")
            if target.reasons:
                print("    Reasons:")
                for reason in target.reasons:
                    print("      - " + reason)
            if target.limitations:
                print("    Limitations:")
                for limitation in target.limitations:
                    print("      - " + limitation)
            if target.command:
                print("    Command:")
                print("      - " + target.command)
    else:
        print("Likely test targets: none")
    if result.suggested_commands:
        print("Suggested commands:")
        for command in result.suggested_commands:
            print(f"  - {command}")
    if result.fallback_policy_commands:
        print("Fallback policy commands:")
        for command in result.fallback_policy_commands:
            print(f"  - {command}")


def _format_budget_limit(limit: int | None) -> str:
    if limit is None:
        return " (no configured limit)"
    return f" / {limit}"


def _print_release_surface_recommendations(
    surfaces: list[EvalReleaseSurfaceRecommendation],
) -> None:
    if not surfaces:
        return
    print("Release surfaces:")
    for surface in surfaces:
        status = "impacted" if surface.impacted else "not impacted"
        print(f"  - {surface.verification_stage}: {status}")
        _print_optional_joined_line(
            "Profiles", surface.recommended_profile_ids, indent="    "
        )
        _print_optional_joined_line(
            "Blocking", surface.blocking_profile_ids, indent="    "
        )
        _print_optional_joined_line(
            "Cases", surface.recommended_case_ids, indent="    "
        )
        _print_optional_joined_line(
            "Capabilities", surface.impacted_capability_ids, indent="    "
        )
        _print_optional_joined_line("Owners", surface.owner_ids, indent="    ")
        if surface.profile_budget_notes:
            print("    Budget notes:")
            for note in surface.profile_budget_notes:
                print("      - " + note)
        if surface.release_gate_commands:
            print("    Full gates:")
            for command in surface.release_gate_commands:
                print("      - " + command)
        if surface.release_gate_notes:
            print("    Gate notes:")
            for note in surface.release_gate_notes:
                print("      - " + note)


def _print_long_run_surface_recommendations(
    surfaces: list[EvalLongRunSurfaceRecommendation],
) -> None:
    if not surfaces:
        return
    print("Long-run surfaces:")
    for surface in surfaces:
        status = "impacted" if surface.impacted else "not impacted"
        print(f"  - {surface.surface}: {status}")
        _print_optional_joined_line(
            "Profiles", surface.recommended_profile_ids, indent="    "
        )
        _print_optional_joined_line(
            "Cases", surface.recommended_case_ids, indent="    "
        )
        if surface.suggested_commands:
            print("    Commands:")
            for command in surface.suggested_commands:
                print("      - " + command)
        if surface.reasons:
            print("    Reasons:")
            for reason in surface.reasons:
                print("      - " + reason)


def _print_optional_value(label: str, value: str | None, *, indent: str) -> None:
    if value:
        print(f"{indent}{label}: {value}")


def _print_optional_joined_line(
    label: str,
    values: Sequence[str],
    *,
    indent: str,
) -> None:
    if values:
        print(f"{indent}{label}: " + ", ".join(values))


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
