"""Capability coverage manifests and audits for replay-backed eval suites."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalVerificationStage
from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier
from glassbox.runtime.evals import load_eval_suite
from glassbox.runtime.evals import resolve_eval_suite_selection

EVAL_COVERAGE_MANIFEST_VERSION = 1
DEFAULT_EVAL_COVERAGE_PATH = Path("evals") / "coverage.json"

type EvalCapabilityKind = Literal["operator_workflow", "product_behavior"]
type EvalCapabilityCriticality = Literal[
    "release-critical",
    "important",
    "advisory",
]
type EvalCapabilityCoverageMode = Literal["single_case", "multi_case"]


class EvalCapabilityDefinition(BaseModel):
    """One repository-owned product capability and the cases expected to cover it."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    title: str
    kind: EvalCapabilityKind = "product_behavior"
    criticality: EvalCapabilityCriticality = "important"
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    expected_case_ids: list[str] = Field(default_factory=list)
    coverage_mode: EvalCapabilityCoverageMode = "single_case"
    notes: str | None = None

    @field_validator("capability_id")
    @classmethod
    def validate_capability_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="capability_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("verification_stages")
    @classmethod
    def validate_verification_stages(
        cls,
        value: list[EvalVerificationStage],
    ) -> list[EvalVerificationStage]:
        normalized: list[EvalVerificationStage] = []
        for stage in value:
            if stage not in normalized:
                normalized.append(stage)
        return normalized

    @field_validator("expected_case_ids")
    @classmethod
    def validate_expected_case_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for case_id in value:
            candidate = _normalize_identifier(case_id, kind="case_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        notes = value.strip()
        return notes or None

    @model_validator(mode="after")
    def validate_coverage_mode(self) -> EvalCapabilityDefinition:
        if self.coverage_mode == "single_case" and len(self.expected_case_ids) > 1:
            raise ValueError(
                "single_case coverage_mode must not declare more than one expected case"
            )
        if self.coverage_mode == "multi_case" and len(self.expected_case_ids) < 2:
            raise ValueError(
                "multi_case coverage_mode must declare at least two expected cases"
            )
        return self


class EvalCoverageManifest(BaseModel):
    """On-disk manifest for repository-owned capability coverage expectations."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_COVERAGE_MANIFEST_VERSION
    capabilities: list[EvalCapabilityDefinition] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_COVERAGE_MANIFEST_VERSION:
            raise ValueError(f"unsupported eval coverage manifest version: {value}")
        return value

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(
        cls,
        value: list[EvalCapabilityDefinition],
    ) -> list[EvalCapabilityDefinition]:
        seen_capability_ids: set[str] = set()
        for capability in value:
            if capability.capability_id in seen_capability_ids:
                raise ValueError(
                    f"duplicate eval capability id: {capability.capability_id}"
                )
            seen_capability_ids.add(capability.capability_id)
        return value


class EvalCapabilityCoverageStatus(BaseModel):
    """Coverage state for one capability under one evaluated portfolio."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    title: str
    criticality: EvalCapabilityCriticality
    verification_stages: list[EvalVerificationStage] = Field(default_factory=list)
    coverage_mode: EvalCapabilityCoverageMode
    expected_case_ids: list[str] = Field(default_factory=list)
    selected_case_ids: list[str] = Field(default_factory=list)
    covered: bool


class EvalCoverageAuditResult(BaseModel):
    """Audit summary for capability coverage against one selected case portfolio."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str | None = None
    profile_title: str | None = None
    verification_stage: EvalVerificationStage | None = None
    audited_case_ids: list[str] = Field(default_factory=list)
    capability_count: int
    covered_capability_count: int
    uncovered_capability_count: int
    uncovered_release_critical_capability_ids: list[str] = Field(default_factory=list)
    unmapped_case_ids: list[str] = Field(default_factory=list)
    redundant_case_ids: list[str] = Field(default_factory=list)
    capability_statuses: list[EvalCapabilityCoverageStatus] = Field(
        default_factory=list
    )


def load_eval_coverage_manifest(
    workspace_root: Path,
    *,
    coverage_path: Path | None = None,
) -> EvalCoverageManifest:
    """Load the repository-local eval coverage manifest from disk."""

    resolved_coverage_path = _resolve_coverage_path(
        workspace_root,
        coverage_path=coverage_path,
    )
    try:
        raw_manifest = resolved_coverage_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval coverage manifest: {resolved_coverage_path}"
        ) from exc

    try:
        manifest = EvalCoverageManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval coverage manifest {resolved_coverage_path}: {exc}"
        ) from exc

    _ensure_path_within_root(
        resolved_coverage_path,
        workspace_root.resolve(),
        kind="eval coverage manifest",
    )
    return manifest


def maybe_audit_eval_coverage(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    coverage_path: Path | None = None,
) -> EvalCoverageAuditResult | None:
    """Try to audit capability coverage and return None when no manifest exists."""

    resolved_workspace_root = workspace_root.resolve()
    resolved_coverage_path = _resolve_coverage_path(
        resolved_workspace_root,
        coverage_path=coverage_path,
    )
    if not resolved_coverage_path.is_file():
        return None
    return audit_eval_coverage(
        resolved_workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
        coverage_path=coverage_path,
    )


def audit_eval_coverage(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    coverage_path: Path | None = None,
) -> EvalCoverageAuditResult:
    """Audit repository-local capability coverage against one selected case set."""

    resolved_workspace_root = workspace_root.resolve()
    selection = resolve_eval_suite_selection(
        resolved_workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
    )
    all_cases = load_eval_suite(resolved_workspace_root)
    manifest = load_eval_coverage_manifest(
        resolved_workspace_root,
        coverage_path=coverage_path,
    )
    return _build_coverage_audit(
        selected_cases=selection.cases,
        all_cases=all_cases,
        capabilities=manifest.capabilities,
        profile=selection.profile,
    )


def build_eval_coverage_summary_lines(result: EvalCoverageAuditResult) -> list[str]:
    """Render a compact human-readable coverage summary."""

    lines = [
        "Capability coverage:",
        f"  - Audited cases: {len(result.audited_case_ids)}",
        "  - Covered capabilities: "
        f"{result.covered_capability_count}/{result.capability_count}",
        f"  - Uncovered capabilities: {result.uncovered_capability_count}",
    ]
    if result.uncovered_release_critical_capability_ids:
        lines.append(
            "  - Uncovered release-critical capabilities: "
            + ", ".join(result.uncovered_release_critical_capability_ids)
        )
    if result.unmapped_case_ids:
        lines.append("  - Unmapped cases: " + ", ".join(result.unmapped_case_ids))
    if result.redundant_case_ids:
        lines.append("  - Redundant cases: " + ", ".join(result.redundant_case_ids))
    return lines


def _build_coverage_audit(
    *,
    selected_cases: list[EvalCase],
    all_cases: list[EvalCase],
    capabilities: list[EvalCapabilityDefinition],
    profile: EvalProfileDefinition | None,
) -> EvalCoverageAuditResult:
    all_case_ids = {case.case_id for case in all_cases}
    selected_case_ids = {case.case_id for case in selected_cases}
    verification_stage = _profile_stage(profile)

    relevant_capabilities = [
        capability
        for capability in capabilities
        if verification_stage is None
        or verification_stage in capability.verification_stages
    ]

    _validate_expected_case_ids(
        all_case_ids=all_case_ids,
        capabilities=relevant_capabilities,
    )

    capability_statuses: list[EvalCapabilityCoverageStatus] = []
    capability_to_selected_cases: dict[str, list[str]] = {}
    case_to_expected_capabilities: dict[str, set[str]] = {
        case.case_id: set() for case in selected_cases
    }

    for capability in relevant_capabilities:
        selected_expected_case_ids = [
            case_id
            for case_id in capability.expected_case_ids
            if case_id in selected_case_ids
        ]
        capability_to_selected_cases[capability.capability_id] = [
            case.case_id
            for case in selected_cases
            if capability.capability_id in case.release_contract.capabilities
        ]
        for case_id in selected_expected_case_ids:
            case_to_expected_capabilities[case_id].add(capability.capability_id)

        capability_statuses.append(
            EvalCapabilityCoverageStatus(
                capability_id=capability.capability_id,
                title=capability.title,
                criticality=capability.criticality,
                verification_stages=list(capability.verification_stages),
                coverage_mode=capability.coverage_mode,
                expected_case_ids=list(capability.expected_case_ids),
                selected_case_ids=selected_expected_case_ids,
                covered=_capability_is_covered(
                    capability,
                    selected_expected_case_ids=selected_expected_case_ids,
                ),
            )
        )

    uncovered_release_critical_capability_ids = [
        status.capability_id
        for status in capability_statuses
        if not status.covered and status.criticality == "release-critical"
    ]
    unmapped_case_ids = sorted(
        case.case_id
        for case in selected_cases
        if not case_to_expected_capabilities[case.case_id]
    )
    redundant_case_ids = sorted(
        {
            case_id
            for capability in relevant_capabilities
            if capability.coverage_mode == "single_case"
            for case_id in capability_to_selected_cases[capability.capability_id]
            if case_id not in capability.expected_case_ids
        }
    )

    return EvalCoverageAuditResult(
        profile_id=_profile_id(profile),
        profile_title=_profile_title(profile),
        verification_stage=verification_stage,
        audited_case_ids=sorted(selected_case_ids),
        capability_count=len(capability_statuses),
        covered_capability_count=sum(
            1 for status in capability_statuses if status.covered
        ),
        uncovered_capability_count=sum(
            1 for status in capability_statuses if not status.covered
        ),
        uncovered_release_critical_capability_ids=(
            uncovered_release_critical_capability_ids
        ),
        unmapped_case_ids=unmapped_case_ids,
        redundant_case_ids=redundant_case_ids,
        capability_statuses=capability_statuses,
    )


def _resolve_coverage_path(
    workspace_root: Path,
    *,
    coverage_path: Path | None,
) -> Path:
    if coverage_path is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_COVERAGE_PATH).resolve()
    if coverage_path.is_absolute():
        return coverage_path.resolve()
    return (workspace_root.resolve() / coverage_path).resolve()


def _validate_expected_case_ids(
    *,
    all_case_ids: set[str],
    capabilities: list[EvalCapabilityDefinition],
) -> None:
    missing_case_ids = sorted(
        {
            case_id
            for capability in capabilities
            for case_id in capability.expected_case_ids
            if case_id not in all_case_ids
        }
    )
    if missing_case_ids:
        raise ValueError(
            "eval coverage manifest references unknown eval case id"
            + ("s" if len(missing_case_ids) > 1 else "")
            + ": "
            + ", ".join(missing_case_ids)
        )


def _capability_is_covered(
    capability: EvalCapabilityDefinition,
    *,
    selected_expected_case_ids: list[str],
) -> bool:
    if capability.coverage_mode == "single_case":
        return bool(selected_expected_case_ids)
    return len(selected_expected_case_ids) == len(capability.expected_case_ids)


def _profile_id(profile: EvalProfileDefinition | None) -> str | None:
    if profile is None:
        return None
    return profile.profile_id


def _profile_title(profile: EvalProfileDefinition | None) -> str | None:
    if profile is None:
        return None
    return profile.title


def _profile_stage(
    profile: EvalProfileDefinition | None,
) -> EvalVerificationStage | None:
    if profile is None:
        return None
    return profile.verification_stage
