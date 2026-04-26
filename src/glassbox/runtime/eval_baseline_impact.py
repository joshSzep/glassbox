"""Impact resolution for eval baseline promotion and refresh reports."""

from pathlib import Path

from glassbox.runtime.eval_baseline_models import EvalBaselineCapabilityImpact
from glassbox.runtime.eval_baseline_models import EvalBaselineImpactSummary
from glassbox.runtime.eval_baseline_models import EvalBaselineProfileImpact
from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest
from glassbox.runtime.evals import EvalCaseManifest
from glassbox.runtime.evals import EvalCaseReleaseContract
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import load_eval_profiles


def build_baseline_impact_summary(
    workspace_root: Path,
    *,
    manifest_before: EvalCaseManifest | None,
    manifest_after: EvalCaseManifest,
) -> EvalBaselineImpactSummary:
    return build_baseline_impact_summary_from_inputs(
        workspace_root,
        before_owner=(
            None if manifest_before is None else manifest_before.release_contract.owner
        ),
        case_id=manifest_after.case_id,
        tags=list(manifest_after.tags),
        release_contract=manifest_after.release_contract,
    )


def build_baseline_impact_summary_from_inputs(
    workspace_root: Path,
    *,
    before_owner: str | None,
    case_id: str,
    tags: list[str],
    release_contract: EvalCaseReleaseContract,
) -> EvalBaselineImpactSummary:
    likely_change_owners = collect_likely_change_owners(
        before_owner=before_owner,
        after_owner=release_contract.owner,
    )
    impacted_capabilities = resolve_impacted_capabilities(
        workspace_root,
        case_id=case_id,
        release_contract=release_contract,
    )
    impacted_profiles = resolve_impacted_profiles(
        workspace_root,
        case_id=case_id,
        tags=tags,
        release_contract=release_contract,
    )
    return EvalBaselineImpactSummary(
        likely_change_owners=likely_change_owners,
        impacted_verification_stages=list(release_contract.verification_stages),
        impacted_capabilities=impacted_capabilities,
        impacted_profiles=impacted_profiles,
    )


def collect_likely_change_owners(
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


def resolve_impacted_capabilities(
    workspace_root: Path,
    *,
    case_id: str,
    release_contract: EvalCaseReleaseContract,
) -> list[EvalBaselineCapabilityImpact]:
    definitions_by_id = load_capability_definitions_by_id(workspace_root)
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


def resolve_impacted_profiles(
    workspace_root: Path,
    *,
    case_id: str,
    tags: list[str],
    release_contract: EvalCaseReleaseContract,
) -> list[EvalBaselineProfileImpact]:
    impacts: list[EvalBaselineProfileImpact] = []
    for profile in load_profiles_for_baseline_report(workspace_root):
        selection_reasons = build_profile_selection_reasons(
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


def load_capability_definitions_by_id(
    workspace_root: Path,
) -> dict[str, EvalCapabilityDefinition]:
    try:
        manifest = load_eval_coverage_manifest(workspace_root)
    except ValueError:
        return {}
    return {
        capability.capability_id: capability for capability in manifest.capabilities
    }


def load_profiles_for_baseline_report(
    workspace_root: Path,
) -> list[EvalProfileDefinition]:
    try:
        return load_eval_profiles(workspace_root)
    except ValueError:
        return []


def build_profile_selection_reasons(
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
