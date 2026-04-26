"""Report building, persistence, and rendering for eval baseline updates."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from glassbox.runtime.eval_baseline_impact import build_baseline_impact_summary
from glassbox.runtime.eval_baseline_models import DEFAULT_EVAL_BASELINE_REPORTS_DIR
from glassbox.runtime.eval_baseline_models import EvalBaselineUpdateReport
from glassbox.runtime.eval_baseline_models import EvalBaselineValueChange
from glassbox.runtime.evals import EvalCaseManifest
from glassbox.runtime.evals import _ensure_path_within_root


def format_eval_baseline_update_report(report: EvalBaselineUpdateReport) -> list[str]:
    """Render a compact operator-facing summary for one baseline update."""

    lines = [
        f"Case: {report.case_id}",
        f"Operation: {report.operation}",
        f"Source session: {report.source_session_id}",
        f"Rationale: {report.rationale}",
        f"Case manifest: {report.case_path}",
        f"Replay bundle: {report.bundle_path}",
        f"Review artifact: {report.report_path}",
    ]
    if report.acknowledgement_required:
        lines.append(
            "Policy acknowledgement: "
            + ("confirmed" if report.acknowledgement_received else "required")
        )
    if report.likely_change_owners:
        lines.append("Likely owners: " + ", ".join(report.likely_change_owners))
    if report.impacted_verification_stages:
        lines.append(
            "Release surfaces: " + ", ".join(report.impacted_verification_stages)
        )
    if report.impacted_blocking_profile_ids:
        lines.append(
            "Blocking profiles: " + ", ".join(report.impacted_blocking_profile_ids)
        )
    if report.impacted_capabilities:
        lines.append("Impacted capabilities:")
        for capability in report.impacted_capabilities:
            detail = capability.capability_id
            fragments: list[str] = []
            if capability.title is not None:
                fragments.append(capability.title)
            if capability.criticality is not None:
                fragments.append(capability.criticality)
            if capability.verification_stages:
                fragments.append("stages=" + ", ".join(capability.verification_stages))
            if capability.current_case_expected:
                fragments.append("expected case")
            if fragments:
                detail += ": " + "; ".join(fragments)
            lines.append("  - " + detail)
    if report.impacted_profiles:
        lines.append("Impacted profiles:")
        for profile in report.impacted_profiles:
            detail = (
                f"{profile.profile_id}: {profile.verification_stage}, "
                f"{profile.track}, "
                f"{'blocking' if profile.blocking else 'non-blocking'}"
            )
            if profile.selection_reasons:
                detail += " [" + ", ".join(profile.selection_reasons) + "]"
            lines.append("  - " + detail)
    if report.manifest_field_changes:
        lines.append(
            "Manifest fields changed: "
            + ", ".join(sorted(report.manifest_field_changes))
        )
    if report.bundle_metric_changes:
        lines.append(
            "Bundle metrics changed: " + ", ".join(sorted(report.bundle_metric_changes))
        )
    return lines


def resolve_report_path(
    workspace_root: Path,
    case_id: str,
    *,
    report_path: Path | None,
) -> Path:
    if report_path is not None:
        resolved_report_path = report_path.resolve()
        _ensure_path_within_root(
            resolved_report_path,
            workspace_root,
            kind="eval baseline report path",
        )
        return resolved_report_path
    return (
        workspace_root / DEFAULT_EVAL_BASELINE_REPORTS_DIR / f"{case_id}.json"
    ).resolve()


def build_update_report(
    *,
    workspace_root: Path,
    operation: str,
    session_id: UUID,
    rationale: str,
    case_path: Path,
    bundle_path: Path,
    report_path: Path,
    manifest_before: EvalCaseManifest | None,
    manifest_after: EvalCaseManifest,
    bundle_payload_before: dict[str, Any] | None,
    bundle_payload_after: dict[str, Any],
    acknowledgement_required: bool,
    acknowledgement_received: bool,
) -> EvalBaselineUpdateReport:
    impact_summary = build_baseline_impact_summary(
        workspace_root,
        manifest_before=manifest_before,
        manifest_after=manifest_after,
    )
    bundle_summary_before = (
        summarize_bundle_payload(bundle_payload_before)
        if bundle_payload_before is not None
        else None
    )
    bundle_summary_after = summarize_bundle_payload(bundle_payload_after)
    return EvalBaselineUpdateReport(
        operation=operation,
        case_id=manifest_after.case_id,
        title=manifest_after.title,
        source_session_id=session_id,
        rationale=rationale,
        case_path=case_path,
        bundle_path=bundle_path,
        report_path=report_path,
        acknowledgement_required=acknowledgement_required,
        acknowledgement_received=acknowledgement_received,
        bundle_summary_before=bundle_summary_before,
        bundle_summary_after=bundle_summary_after,
        bundle_metric_changes=diff_mapping(
            bundle_summary_before,
            bundle_summary_after,
        ),
        manifest_field_changes=diff_mapping(
            manifest_before.model_dump(mode="json", exclude_none=True)
            if manifest_before is not None
            else None,
            manifest_after.model_dump(mode="json", exclude_none=True),
        ),
        expectation_before=(
            manifest_before.expectation.model_dump(mode="json")
            if manifest_before is not None
            else None
        ),
        expectation_after=manifest_after.expectation.model_dump(mode="json"),
        release_contract_before=(
            manifest_before.release_contract.model_dump(mode="json")
            if manifest_before is not None
            else None
        ),
        release_contract_after=manifest_after.release_contract.model_dump(mode="json"),
        baseline_history_count_before=(
            len(manifest_before.baseline_history) if manifest_before is not None else 0
        ),
        baseline_history_count_after=len(manifest_after.baseline_history),
        likely_change_owners=impact_summary.likely_change_owners,
        impacted_verification_stages=impact_summary.impacted_verification_stages,
        impacted_capabilities=impact_summary.impacted_capabilities,
        impacted_profiles=impact_summary.impacted_profiles,
        impacted_blocking_profile_ids=impact_summary.blocking_profile_ids(),
    )


def write_report(report: EvalBaselineUpdateReport) -> None:
    report.report_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(
        report.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    report.report_path.write_text(f"{serialized_report}\n", encoding="utf-8")


def summarize_bundle_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {}
    baseline_payload = payload.get("baseline") or {}
    final_state = baseline_payload.get("final_state")
    final_state_status = None
    if isinstance(final_state, dict):
        final_state_status = final_state.get("status")
    return {
        "model_call_count": len(payload.get("model_calls", [])),
        "tool_request_count": len(payload.get("tool_requests", [])),
        "tool_result_count": len(payload.get("tool_results", [])),
        "turn_output_count": len(payload.get("turn_outputs", [])),
        "inherited_message_count": len(payload.get("inherited_messages", [])),
        "inherited_runtime_note_count": len(payload.get("inherited_runtime_notes", [])),
        "baseline_transcript_message_count": len(
            baseline_payload.get("transcript", [])
        ),
        "baseline_tool_call_count": len(baseline_payload.get("tool_calls", [])),
        "baseline_approval_count": len(baseline_payload.get("approvals", [])),
        "baseline_question_count": len(baseline_payload.get("questions", [])),
        "baseline_final_state_status": final_state_status,
    }


def diff_mapping(
    before: dict[str, Any] | None,
    after: dict[str, Any],
) -> dict[str, EvalBaselineValueChange]:
    before_payload = before or {}
    changed_keys = sorted(set(before_payload) | set(after))
    return {
        key: EvalBaselineValueChange(
            before=before_payload.get(key),
            after=after.get(key),
        )
        for key in changed_keys
        if before_payload.get(key) != after.get(key)
    }
