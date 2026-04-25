"""Guided promotion and refresh workflows for replay-backed eval baselines."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Literal
from typing import cast
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest
from glassbox.runtime.evals import DEFAULT_EVAL_BUNDLES_DIR
from glassbox.runtime.evals import DEFAULT_EVAL_CASES_DIR
from glassbox.runtime.evals import EvalBaselineHistoryEntry
from glassbox.runtime.evals import EvalBaselineRefreshPolicy
from glassbox.runtime.evals import EvalCaseExpectation
from glassbox.runtime.evals import EvalCaseManifest
from glassbox.runtime.evals import EvalCaseReleaseContract
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.evals import EvalInvariant
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalProfileTrack
from glassbox.runtime.evals import EvalVerificationStage
from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier
from glassbox.runtime.evals import load_eval_profiles
from glassbox.runtime.replay import ReplayRunner

DEFAULT_EVAL_BASELINE_REPORTS_DIR = Path(".glassbox") / "evals" / "baseline-updates"
type EvalExpectationMode = Literal["exact_match", "selected_invariants"]


class EvalBaselineValueChange(BaseModel):
    """One before/after value change in a baseline update report."""

    model_config = ConfigDict(extra="forbid")

    before: Any = None
    after: Any = None


class EvalBaselineCapabilityImpact(BaseModel):
    """Coverage metadata that helps reviewers understand a baseline change."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    title: str | None = None
    criticality: str | None = None
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    expected_case_ids: list[str] = Field(default_factory=list)
    current_case_expected: bool = False


class EvalBaselineProfileImpact(BaseModel):
    """Profile metadata affected by one baseline promotion or refresh."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    title: str
    verification_stage: EvalVerificationStage
    track: EvalProfileTrack
    blocking: bool
    selection_reasons: list[str] = Field(default_factory=list)


class EvalBaselineUpdateReport(BaseModel):
    """Review artifact for one promoted or refreshed eval baseline."""

    model_config = ConfigDict(extra="forbid")

    operation: str
    case_id: str
    title: str
    source_session_id: UUID
    rationale: str
    case_path: Path
    bundle_path: Path
    report_path: Path
    acknowledgement_required: bool = False
    acknowledgement_received: bool = False
    bundle_summary_before: dict[str, Any] | None = None
    bundle_summary_after: dict[str, Any] = Field(default_factory=dict)
    bundle_metric_changes: dict[str, EvalBaselineValueChange] = Field(
        default_factory=dict
    )
    manifest_field_changes: dict[str, EvalBaselineValueChange] = Field(
        default_factory=dict
    )
    expectation_before: dict[str, Any] | None = None
    expectation_after: dict[str, Any] = Field(default_factory=dict)
    release_contract_before: dict[str, Any] | None = None
    release_contract_after: dict[str, Any] = Field(default_factory=dict)
    baseline_history_count_before: int = 0
    baseline_history_count_after: int = 0
    likely_change_owners: list[str] = Field(default_factory=list)
    impacted_verification_stages: list[EvalVerificationStage] = Field(
        default_factory=list
    )
    impacted_capabilities: list[EvalBaselineCapabilityImpact] = Field(
        default_factory=list
    )
    impacted_profiles: list[EvalBaselineProfileImpact] = Field(default_factory=list)
    impacted_blocking_profile_ids: list[str] = Field(default_factory=list)


def promote_eval_case(
    workspace_root: Path,
    *,
    replay_runner: ReplayRunner,
    session_id: UUID,
    case_id: str,
    title: str,
    tags: list[str] | None = None,
    notes: str | None = None,
    expectation_mode: str | None = None,
    invariants: list[str] | None = None,
    owner: str | None = None,
    capabilities: list[str] | None = None,
    severity: str | None = None,
    verification_stages: list[str] | None = None,
    baseline_refresh_policy: str | None = None,
    rationale: str | None = None,
    report_path: Path | None = None,
) -> EvalBaselineUpdateReport:
    """Promote one recorded session into a new repository-local eval case."""

    resolved_workspace_root = workspace_root.resolve()
    normalized_case_id = _normalize_identifier(case_id, kind="case_id")
    case_path = _default_case_path(resolved_workspace_root, normalized_case_id)
    if case_path.exists():
        raise ValueError(f"eval case already exists: {normalized_case_id}")

    bundle_path = _default_bundle_path(resolved_workspace_root, normalized_case_id)
    exported_bundle_path = replay_runner.export_session_bundle(session_id, bundle_path)

    expectation = _build_expectation(
        expectation_mode=expectation_mode,
        invariants=invariants,
    )
    release_contract = _build_release_contract(
        owner=owner,
        capabilities=capabilities,
        severity=severity,
        verification_stages=verification_stages,
        baseline_refresh_policy=baseline_refresh_policy,
    )
    _validate_curated_release_contract(normalized_case_id, release_contract)

    manifest = EvalCaseManifest(
        case_id=normalized_case_id,
        title=title,
        bundle_path=_bundle_path_relative_to_case(case_path, exported_bundle_path),
        tags=list(tags or []),
        notes=notes,
        expectation=expectation,
        release_contract=release_contract,
        baseline_history=[
            EvalBaselineHistoryEntry(
                operation="promote",
                recorded_at=datetime.now(UTC),
                source_session_id=session_id,
                rationale=rationale or f"Initial promotion from session {session_id}",
            )
        ],
    )
    _write_manifest(case_path, manifest)

    report = _build_update_report(
        workspace_root=resolved_workspace_root,
        operation="promote",
        session_id=session_id,
        rationale=manifest.baseline_history[-1].rationale,
        case_path=case_path,
        bundle_path=exported_bundle_path,
        report_path=_resolve_report_path(
            resolved_workspace_root,
            normalized_case_id,
            report_path=report_path,
        ),
        manifest_before=None,
        manifest_after=manifest,
        bundle_payload_before=None,
        bundle_payload_after=_load_json_file(exported_bundle_path),
        acknowledgement_required=False,
        acknowledgement_received=False,
    )
    _write_report(report)
    return report


def refresh_eval_case(
    workspace_root: Path,
    *,
    replay_runner: ReplayRunner,
    session_id: UUID,
    case_id: str,
    rationale: str,
    acknowledge_policy: bool = False,
    title: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
    expectation_mode: str | None = None,
    invariants: list[str] | None = None,
    owner: str | None = None,
    capabilities: list[str] | None = None,
    severity: str | None = None,
    verification_stages: list[str] | None = None,
    baseline_refresh_policy: str | None = None,
    report_path: Path | None = None,
) -> EvalBaselineUpdateReport:
    """Refresh one existing eval baseline from a new recorded source session."""

    resolved_workspace_root = workspace_root.resolve()
    normalized_case_id = _normalize_identifier(case_id, kind="case_id")
    case_path = _default_case_path(resolved_workspace_root, normalized_case_id)
    if not case_path.is_file():
        raise ValueError(f"unknown eval case id: {normalized_case_id}")

    manifest_before = _load_manifest(case_path)
    bundle_path = (case_path.parent / manifest_before.bundle_path).resolve()
    _ensure_path_within_root(
        bundle_path,
        resolved_workspace_root,
        kind="eval bundle path",
    )
    bundle_payload_before = (
        _load_json_file(bundle_path) if bundle_path.exists() else None
    )

    expectation_after = _merge_expectation(
        manifest_before.expectation,
        expectation_mode=expectation_mode,
        invariants=invariants,
    )
    release_contract_after = _merge_release_contract(
        manifest_before.release_contract,
        owner=owner,
        capabilities=capabilities,
        severity=severity,
        verification_stages=verification_stages,
        baseline_refresh_policy=baseline_refresh_policy,
    )
    requires_acknowledgement = _refresh_requires_acknowledgement(
        release_contract_after,
    )
    _validate_curated_release_contract(normalized_case_id, release_contract_after)
    if requires_acknowledgement and not acknowledge_policy:
        impacted_profiles = _resolve_impacted_profiles(
            resolved_workspace_root,
            case_id=normalized_case_id,
            tags=list(tags) if tags is not None else list(manifest_before.tags),
            release_contract=release_contract_after,
        )
        blocking_profile_ids = [
            profile.profile_id for profile in impacted_profiles if profile.blocking
        ]
        scope_suffix = ""
        if blocking_profile_ids:
            scope_suffix = (
                " (affected blocking profiles: " + ", ".join(blocking_profile_ids) + ")"
            )
        raise ValueError(
            "refreshing blocking or release-candidate eval case requires "
            f"--acknowledge-policy: {normalized_case_id}{scope_suffix}"
        )

    refreshed_bundle_path = replay_runner.export_session_bundle(session_id, bundle_path)
    manifest_after = EvalCaseManifest(
        manifest_version=manifest_before.manifest_version,
        case_id=manifest_before.case_id,
        title=title or manifest_before.title,
        bundle_path=manifest_before.bundle_path,
        tags=list(tags) if tags is not None else list(manifest_before.tags),
        notes=notes if notes is not None else manifest_before.notes,
        expectation=expectation_after,
        release_contract=release_contract_after,
        baseline_history=list(manifest_before.baseline_history)
        + [
            EvalBaselineHistoryEntry(
                operation="refresh",
                recorded_at=datetime.now(UTC),
                source_session_id=session_id,
                rationale=rationale,
            )
        ],
    )
    _write_manifest(case_path, manifest_after)

    report = _build_update_report(
        workspace_root=resolved_workspace_root,
        operation="refresh",
        session_id=session_id,
        rationale=rationale,
        case_path=case_path,
        bundle_path=refreshed_bundle_path,
        report_path=_resolve_report_path(
            resolved_workspace_root,
            normalized_case_id,
            report_path=report_path,
        ),
        manifest_before=manifest_before,
        manifest_after=manifest_after,
        bundle_payload_before=bundle_payload_before,
        bundle_payload_after=_load_json_file(refreshed_bundle_path),
        acknowledgement_required=requires_acknowledgement,
        acknowledgement_received=acknowledge_policy,
    )
    _write_report(report)
    return report


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


def _build_expectation(
    *,
    expectation_mode: str | None,
    invariants: list[str] | None,
) -> EvalCaseExpectation:
    if expectation_mode is None and invariants:
        expectation_mode = "selected_invariants"
    return EvalCaseExpectation(
        mode=cast(EvalExpectationMode, expectation_mode or "exact_match"),
        invariants=[cast(EvalInvariant, invariant) for invariant in invariants or []],
    )


def _merge_expectation(
    existing: EvalCaseExpectation,
    *,
    expectation_mode: str | None,
    invariants: list[str] | None,
) -> EvalCaseExpectation:
    payload = existing.model_dump(mode="json")
    if expectation_mode is not None:
        payload["mode"] = expectation_mode
    if invariants is not None:
        payload["invariants"] = list(invariants)
        if expectation_mode is None:
            payload["mode"] = "selected_invariants"
    return EvalCaseExpectation.model_validate(payload)


def _build_release_contract(
    *,
    owner: str | None,
    capabilities: list[str] | None,
    severity: str | None,
    verification_stages: list[str] | None,
    baseline_refresh_policy: str | None,
) -> EvalCaseReleaseContract:
    return EvalCaseReleaseContract(
        owner=owner,
        capabilities=list(capabilities or []),
        severity=cast(EvalCaseSeverity, severity or "medium"),
        verification_stages=[
            cast(EvalVerificationStage, stage)
            for stage in verification_stages or ["advisory"]
        ],
        baseline_refresh_policy=cast(
            EvalBaselineRefreshPolicy,
            baseline_refresh_policy or "review_required",
        ),
    )


def _merge_release_contract(
    existing: EvalCaseReleaseContract,
    *,
    owner: str | None,
    capabilities: list[str] | None,
    severity: str | None,
    verification_stages: list[str] | None,
    baseline_refresh_policy: str | None,
) -> EvalCaseReleaseContract:
    payload = existing.model_dump(mode="json")
    if owner is not None:
        payload["owner"] = owner
    if capabilities is not None:
        payload["capabilities"] = list(capabilities)
    if severity is not None:
        payload["severity"] = severity
    if verification_stages is not None:
        payload["verification_stages"] = list(verification_stages)
    if baseline_refresh_policy is not None:
        payload["baseline_refresh_policy"] = baseline_refresh_policy
    return EvalCaseReleaseContract.model_validate(payload)


def _validate_curated_release_contract(
    case_id: str,
    release_contract: EvalCaseReleaseContract,
) -> None:
    if not _refresh_requires_acknowledgement(release_contract):
        return
    if release_contract.owner is None or not release_contract.capabilities:
        raise ValueError(
            "blocking or release-candidate eval case requires owner and "
            f"capabilities metadata before baseline updates: {case_id}"
        )


def _refresh_requires_acknowledgement(
    release_contract: EvalCaseReleaseContract,
) -> bool:
    return bool(
        set(release_contract.verification_stages)
        & {"commit-time", "push-time", "release-candidate"}
    )


def _default_case_path(workspace_root: Path, case_id: str) -> Path:
    return (workspace_root / DEFAULT_EVAL_CASES_DIR / f"{case_id}.json").resolve()


def _default_bundle_path(workspace_root: Path, case_id: str) -> Path:
    return (workspace_root / DEFAULT_EVAL_BUNDLES_DIR / f"{case_id}.json").resolve()


def _bundle_path_relative_to_case(case_path: Path, bundle_path: Path) -> Path:
    return Path("..") / bundle_path.relative_to(case_path.parent.parent)


def _resolve_report_path(
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


def _load_manifest(case_path: Path) -> EvalCaseManifest:
    try:
        raw_manifest = case_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing eval case file: {case_path}") from exc
    try:
        return EvalCaseManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(f"invalid eval case file {case_path}: {exc}") from exc


def _write_manifest(case_path: Path, manifest: EvalCaseManifest) -> None:
    case_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_manifest = json.dumps(
        manifest.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )
    case_path.write_text(f"{serialized_manifest}\n", encoding="utf-8")


def _load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_update_report(
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
    impact_summary = _build_baseline_impact_summary(
        workspace_root,
        manifest_before=manifest_before,
        manifest_after=manifest_after,
    )
    bundle_summary_before = (
        _summarize_bundle_payload(bundle_payload_before)
        if bundle_payload_before is not None
        else None
    )
    bundle_summary_after = _summarize_bundle_payload(bundle_payload_after)
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
        bundle_metric_changes=_diff_mapping(
            bundle_summary_before,
            bundle_summary_after,
        ),
        manifest_field_changes=_diff_mapping(
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
        likely_change_owners=impact_summary["likely_change_owners"],
        impacted_verification_stages=impact_summary["impacted_verification_stages"],
        impacted_capabilities=impact_summary["impacted_capabilities"],
        impacted_profiles=impact_summary["impacted_profiles"],
        impacted_blocking_profile_ids=impact_summary["impacted_blocking_profile_ids"],
    )


def _write_report(report: EvalBaselineUpdateReport) -> None:
    report.report_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(
        report.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    report.report_path.write_text(f"{serialized_report}\n", encoding="utf-8")


def _summarize_bundle_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
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


def _diff_mapping(
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


def _build_baseline_impact_summary(
    workspace_root: Path,
    *,
    manifest_before: EvalCaseManifest | None,
    manifest_after: EvalCaseManifest,
) -> dict[str, Any]:
    likely_change_owners = _collect_likely_change_owners(
        before_owner=(
            None if manifest_before is None else manifest_before.release_contract.owner
        ),
        after_owner=manifest_after.release_contract.owner,
    )
    impacted_capabilities = _resolve_impacted_capabilities(
        workspace_root,
        case_id=manifest_after.case_id,
        release_contract=manifest_after.release_contract,
    )
    impacted_profiles = _resolve_impacted_profiles(
        workspace_root,
        case_id=manifest_after.case_id,
        tags=list(manifest_after.tags),
        release_contract=manifest_after.release_contract,
    )
    return {
        "likely_change_owners": likely_change_owners,
        "impacted_verification_stages": list(
            manifest_after.release_contract.verification_stages
        ),
        "impacted_capabilities": impacted_capabilities,
        "impacted_profiles": impacted_profiles,
        "impacted_blocking_profile_ids": [
            profile.profile_id for profile in impacted_profiles if profile.blocking
        ],
    }


def _collect_likely_change_owners(
    *,
    before_owner: str | None,
    after_owner: str | None,
) -> list[str]:
    owners: list[str] = []
    for owner in [before_owner, after_owner]:
        if owner is None or owner in owners:
            continue
        owners.append(owner)
    return owners


def _resolve_impacted_capabilities(
    workspace_root: Path,
    *,
    case_id: str,
    release_contract: EvalCaseReleaseContract,
) -> list[EvalBaselineCapabilityImpact]:
    definitions_by_id = _load_capability_definitions_by_id(workspace_root)
    impacts: list[EvalBaselineCapabilityImpact] = []
    for capability_id in release_contract.capabilities:
        definition = definitions_by_id.get(capability_id)
        impacts.append(
            EvalBaselineCapabilityImpact(
                capability_id=capability_id,
                title=None if definition is None else definition.title,
                criticality=None if definition is None else definition.criticality,
                verification_stages=(
                    list(release_contract.verification_stages)
                    if definition is None
                    else list(definition.verification_stages)
                ),
                expected_case_ids=(
                    [] if definition is None else list(definition.expected_case_ids)
                ),
                current_case_expected=(
                    False
                    if definition is None
                    else case_id in definition.expected_case_ids
                ),
            )
        )
    return impacts


def _resolve_impacted_profiles(
    workspace_root: Path,
    *,
    case_id: str,
    tags: list[str],
    release_contract: EvalCaseReleaseContract,
) -> list[EvalBaselineProfileImpact]:
    impacts: list[EvalBaselineProfileImpact] = []
    for profile in _load_profiles_for_baseline_report(workspace_root):
        selection_reasons = _build_profile_selection_reasons(
            profile,
            case_id=case_id,
            tags=tags,
            release_contract=release_contract,
        )
        if not selection_reasons:
            continue
        impacts.append(
            EvalBaselineProfileImpact(
                profile_id=profile.profile_id,
                title=profile.title,
                verification_stage=profile.verification_stage,
                track=profile.track,
                blocking=profile.blocking,
                selection_reasons=selection_reasons,
            )
        )
    impacts.sort(
        key=lambda impact: (
            not impact.blocking,
            impact.verification_stage,
            impact.profile_id,
        )
    )
    return impacts


def _load_capability_definitions_by_id(
    workspace_root: Path,
) -> dict[str, EvalCapabilityDefinition]:
    try:
        manifest = load_eval_coverage_manifest(workspace_root)
    except ValueError:
        return {}
    return {
        capability.capability_id: capability for capability in manifest.capabilities
    }


def _load_profiles_for_baseline_report(
    workspace_root: Path,
) -> list[EvalProfileDefinition]:
    try:
        return load_eval_profiles(workspace_root)
    except ValueError:
        return []


def _build_profile_selection_reasons(
    profile: EvalProfileDefinition,
    *,
    case_id: str,
    tags: list[str],
    release_contract: EvalCaseReleaseContract,
) -> list[str]:
    reasons: list[str] = []
    if profile.case_ids:
        if case_id not in profile.case_ids:
            return []
        reasons.append("explicit case id")
    if profile.tags:
        if not set(profile.tags).issubset(set(tags)):
            return []
        reasons.append("tag match")
    if profile.verification_stage not in release_contract.verification_stages:
        return []
    reasons.append(f"stage {profile.verification_stage}")
    return reasons
