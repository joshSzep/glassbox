"""Guided promotion and refresh workflows for replay-backed eval baselines."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from glassbox.runtime.eval_baseline_contracts import build_expectation
from glassbox.runtime.eval_baseline_contracts import build_release_contract
from glassbox.runtime.eval_baseline_contracts import merge_expectation
from glassbox.runtime.eval_baseline_contracts import merge_release_contract
from glassbox.runtime.eval_baseline_contracts import refresh_requires_acknowledgement
from glassbox.runtime.eval_baseline_contracts import validate_curated_release_contract
from glassbox.runtime.eval_baseline_impact import (
    build_baseline_impact_summary_from_inputs,
)
from glassbox.runtime.eval_baseline_models import EvalBaselineUpdateReport
from glassbox.runtime.eval_baseline_reports import build_update_report
from glassbox.runtime.eval_baseline_reports import resolve_report_path
from glassbox.runtime.eval_baseline_reports import write_report
from glassbox.runtime.evals import DEFAULT_EVAL_BUNDLES_DIR
from glassbox.runtime.evals import DEFAULT_EVAL_CASES_DIR
from glassbox.runtime.evals import EvalBaselineHistoryEntry
from glassbox.runtime.evals import EvalCaseManifest
from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier
from glassbox.runtime.replay import ReplayRunner


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
    case_path = default_case_path(resolved_workspace_root, normalized_case_id)
    if case_path.exists():
        raise ValueError(f"eval case already exists: {normalized_case_id}")

    bundle_path = default_bundle_path(resolved_workspace_root, normalized_case_id)
    exported_bundle_path = replay_runner.export_session_bundle(session_id, bundle_path)

    expectation = build_expectation(
        expectation_mode=expectation_mode,
        invariants=invariants,
    )
    release_contract = build_release_contract(
        owner=owner,
        capabilities=capabilities,
        severity=severity,
        verification_stages=verification_stages,
        baseline_refresh_policy=baseline_refresh_policy,
    )
    validate_curated_release_contract(normalized_case_id, release_contract)

    manifest = EvalCaseManifest(
        case_id=normalized_case_id,
        title=title,
        bundle_path=bundle_path_relative_to_case(case_path, exported_bundle_path),
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
    write_manifest(case_path, manifest)

    report = build_update_report(
        workspace_root=resolved_workspace_root,
        operation="promote",
        session_id=session_id,
        rationale=manifest.baseline_history[-1].rationale,
        case_path=case_path,
        bundle_path=exported_bundle_path,
        report_path=resolve_report_path(
            resolved_workspace_root,
            normalized_case_id,
            report_path=report_path,
        ),
        manifest_before=None,
        manifest_after=manifest,
        bundle_payload_before=None,
        bundle_payload_after=load_json_file(exported_bundle_path),
        acknowledgement_required=False,
        acknowledgement_received=False,
    )
    write_report(report)
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
    case_path = default_case_path(resolved_workspace_root, normalized_case_id)
    if not case_path.is_file():
        raise ValueError(f"unknown eval case id: {normalized_case_id}")

    manifest_before = load_manifest(case_path)
    bundle_path = (case_path.parent / manifest_before.bundle_path).resolve()
    _ensure_path_within_root(
        bundle_path,
        resolved_workspace_root,
        kind="eval bundle path",
    )
    bundle_payload_before = (
        load_json_file(bundle_path) if bundle_path.exists() else None
    )

    expectation_after = merge_expectation(
        manifest_before.expectation,
        expectation_mode=expectation_mode,
        invariants=invariants,
    )
    release_contract_after = merge_release_contract(
        manifest_before.release_contract,
        owner=owner,
        capabilities=capabilities,
        severity=severity,
        verification_stages=verification_stages,
        baseline_refresh_policy=baseline_refresh_policy,
    )
    requires_acknowledgement = refresh_requires_acknowledgement(
        release_contract_after,
    )
    validate_curated_release_contract(normalized_case_id, release_contract_after)
    if requires_acknowledgement and not acknowledge_policy:
        impact_summary = build_baseline_impact_summary_from_inputs(
            resolved_workspace_root,
            before_owner=manifest_before.release_contract.owner,
            case_id=normalized_case_id,
            tags=list(tags) if tags is not None else list(manifest_before.tags),
            release_contract=release_contract_after,
        )
        blocking_profile_ids = impact_summary.blocking_profile_ids()
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
    write_manifest(case_path, manifest_after)

    report = build_update_report(
        workspace_root=resolved_workspace_root,
        operation="refresh",
        session_id=session_id,
        rationale=rationale,
        case_path=case_path,
        bundle_path=refreshed_bundle_path,
        report_path=resolve_report_path(
            resolved_workspace_root,
            normalized_case_id,
            report_path=report_path,
        ),
        manifest_before=manifest_before,
        manifest_after=manifest_after,
        bundle_payload_before=bundle_payload_before,
        bundle_payload_after=load_json_file(refreshed_bundle_path),
        acknowledgement_required=requires_acknowledgement,
        acknowledgement_received=acknowledge_policy,
    )
    write_report(report)
    return report


def default_case_path(workspace_root: Path, case_id: str) -> Path:
    return (workspace_root / DEFAULT_EVAL_CASES_DIR / f"{case_id}.json").resolve()


def default_bundle_path(workspace_root: Path, case_id: str) -> Path:
    return (workspace_root / DEFAULT_EVAL_BUNDLES_DIR / f"{case_id}.json").resolve()


def bundle_path_relative_to_case(case_path: Path, bundle_path: Path) -> Path:
    return Path("..") / bundle_path.relative_to(case_path.parent.parent)


def load_manifest(case_path: Path) -> EvalCaseManifest:
    try:
        raw_manifest = case_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing eval case file: {case_path}") from exc
    try:
        return EvalCaseManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(f"invalid eval case file {case_path}: {exc}") from exc


def write_manifest(case_path: Path, manifest: EvalCaseManifest) -> None:
    case_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_manifest = json.dumps(
        manifest.model_dump(mode="json", exclude_none=True),
        indent=2,
        sort_keys=True,
    )
    case_path.write_text(f"{serialized_manifest}\n", encoding="utf-8")


def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
