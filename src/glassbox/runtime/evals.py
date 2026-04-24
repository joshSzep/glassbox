"""Declarative eval case schema and discovery for replay-backed suites."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVAL_CASE_MANIFEST_VERSION = 1
EVAL_PROFILE_MANIFEST_VERSION = 1
DEFAULT_EVALS_ROOT = Path("evals")
DEFAULT_EVAL_CASES_DIR = DEFAULT_EVALS_ROOT / "cases"
DEFAULT_EVAL_BUNDLES_DIR = DEFAULT_EVALS_ROOT / "bundles"
DEFAULT_EVAL_PROFILES_PATH = DEFAULT_EVALS_ROOT / "profiles.json"

type EvalInvariant = Literal[
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
]
type EvalCaseSeverity = Literal["critical", "high", "medium", "low"]
type EvalVerificationStage = Literal[
    "commit-time",
    "push-time",
    "release-candidate",
    "advisory",
]
type EvalBaselineRefreshPolicy = Literal[
    "review_required",
    "intentional_only",
    "advisory",
]
type EvalBaselineOperation = Literal["promote", "refresh"]

_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_ALL_EVAL_INVARIANTS: tuple[EvalInvariant, ...] = (
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
)


def _default_verification_stages() -> list[EvalVerificationStage]:
    return ["advisory"]


class EvalCaseExpectation(BaseModel):
    """Comparison contract for one replay-backed eval case."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["exact_match", "selected_invariants"] = "exact_match"
    invariants: list[EvalInvariant] = Field(default_factory=list)

    @field_validator("invariants")
    @classmethod
    def validate_invariants(cls, value: list[EvalInvariant]) -> list[EvalInvariant]:
        normalized: list[EvalInvariant] = []
        for invariant in value:
            if invariant not in normalized:
                normalized.append(invariant)
        return normalized

    @model_validator(mode="after")
    def validate_mode(self) -> EvalCaseExpectation:
        if self.mode == "exact_match" and self.invariants:
            raise ValueError(
                "exact_match expectation must not declare explicit invariants"
            )
        if self.mode == "selected_invariants" and not self.invariants:
            raise ValueError(
                "selected_invariants expectation must include at least one invariant"
            )
        return self

    def selected_invariants(self) -> tuple[EvalInvariant, ...]:
        if self.mode == "exact_match":
            return _ALL_EVAL_INVARIANTS
        return tuple(self.invariants)


class EvalCaseReleaseContract(BaseModel):
    """Release-oriented metadata for one replay-backed eval case."""

    model_config = ConfigDict(extra="forbid")

    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    severity: EvalCaseSeverity = "medium"
    verification_stages: list[EvalVerificationStage] = Field(
        default_factory=_default_verification_stages
    )
    baseline_refresh_policy: EvalBaselineRefreshPolicy = "review_required"

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_identifier(value, kind="owner")

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for capability in value:
            candidate = _normalize_identifier(capability, kind="capability")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

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

    @model_validator(mode="after")
    def validate_release_contract(self) -> EvalCaseReleaseContract:
        if not self.verification_stages:
            raise ValueError(
                "release_contract.verification_stages must include at least one stage"
            )
        if self.baseline_refresh_policy == "advisory" and (
            "advisory" not in self.verification_stages
        ):
            raise ValueError(
                "advisory baseline_refresh_policy requires "
                "an advisory verification stage"
            )
        return self


class EvalBaselineHistoryEntry(BaseModel):
    """One reviewable promotion or refresh note for an eval baseline."""

    model_config = ConfigDict(extra="forbid")

    operation: EvalBaselineOperation
    recorded_at: datetime
    source_session_id: UUID
    rationale: str

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        rationale = value.strip()
        if not rationale:
            raise ValueError("baseline rationale must not be empty")
        return rationale


class EvalCaseManifest(BaseModel):
    """On-disk manifest for one repository-local eval case."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_CASE_MANIFEST_VERSION
    case_id: str
    title: str
    bundle_path: Path
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    expectation: EvalCaseExpectation = Field(default_factory=EvalCaseExpectation)
    release_contract: EvalCaseReleaseContract = Field(
        default_factory=EvalCaseReleaseContract
    )
    baseline_history: list[EvalBaselineHistoryEntry] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_CASE_MANIFEST_VERSION:
            raise ValueError(f"unsupported eval case manifest version: {value}")
        return value

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="case_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("bundle_path")
    @classmethod
    def validate_bundle_path(cls, value: Path) -> Path:
        if value.is_absolute():
            raise ValueError("bundle_path must be relative to the eval case file")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in value:
            candidate = _normalize_identifier(tag, kind="tag")
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


class EvalCase(BaseModel):
    """Resolved eval case ready for discovery, filtering, and future execution."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_CASE_MANIFEST_VERSION
    case_id: str
    title: str
    case_path: Path
    bundle_path: Path
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    expectation: EvalCaseExpectation
    release_contract: EvalCaseReleaseContract
    baseline_history: list[EvalBaselineHistoryEntry] = Field(default_factory=list)


class EvalProfileDefinition(BaseModel):
    """Repository-owned selection rules for one named verification stage."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    title: str
    description: str | None = None
    verification_stage: EvalVerificationStage
    tags: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    blocking: bool = True

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="profile_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        description = value.strip()
        return description or None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in value:
            candidate = _normalize_identifier(tag, kind="tag")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for case_id in value:
            candidate = _normalize_identifier(case_id, kind="case_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized


class EvalProfileManifest(BaseModel):
    """On-disk manifest for named eval verification profiles."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_PROFILE_MANIFEST_VERSION
    profiles: list[EvalProfileDefinition] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_PROFILE_MANIFEST_VERSION:
            raise ValueError(f"unsupported eval profile manifest version: {value}")
        return value

    @field_validator("profiles")
    @classmethod
    def validate_profiles(
        cls,
        value: list[EvalProfileDefinition],
    ) -> list[EvalProfileDefinition]:
        seen_profile_ids: set[str] = set()
        for profile in value:
            if profile.profile_id in seen_profile_ids:
                raise ValueError(f"duplicate eval profile id: {profile.profile_id}")
            seen_profile_ids.add(profile.profile_id)
        return value


class EvalSuiteSelection(BaseModel):
    """Resolved eval suite selection, including an optional named profile."""

    model_config = ConfigDict(extra="forbid")

    profile: EvalProfileDefinition | None = None
    cases: list[EvalCase] = Field(default_factory=list)


def discover_eval_case_files(
    workspace_root: Path,
    *,
    cases_dir: Path | None = None,
) -> list[Path]:
    """Return discovered eval case manifest files under the repository layout."""

    root = _resolve_cases_dir(workspace_root, cases_dir=cases_dir)
    if not root.exists():
        return []
    return sorted(path.resolve() for path in root.rglob("*.json") if path.is_file())


def load_eval_case(
    case_path: Path,
    *,
    workspace_root: Path | None = None,
    validate_bundle_exists: bool = True,
) -> EvalCase:
    """Load and resolve one eval case manifest from disk."""

    resolved_case_path = case_path.resolve()
    try:
        raw_manifest = resolved_case_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing eval case file: {resolved_case_path}") from exc

    try:
        manifest = EvalCaseManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(f"invalid eval case file {resolved_case_path}: {exc}") from exc

    resolved_workspace_root = (
        workspace_root.resolve() if workspace_root is not None else None
    )
    if resolved_workspace_root is not None:
        _ensure_path_within_root(
            resolved_case_path,
            resolved_workspace_root,
            kind="eval case file",
        )

    resolved_bundle_path = (resolved_case_path.parent / manifest.bundle_path).resolve()
    if resolved_workspace_root is not None:
        _ensure_path_within_root(
            resolved_bundle_path,
            resolved_workspace_root,
            kind="eval bundle path",
        )
    if validate_bundle_exists and not resolved_bundle_path.is_file():
        raise ValueError(
            f"eval case bundle_path does not exist: {resolved_bundle_path}"
        )

    return EvalCase(
        manifest_version=manifest.manifest_version,
        case_id=manifest.case_id,
        title=manifest.title,
        case_path=resolved_case_path,
        bundle_path=resolved_bundle_path,
        tags=manifest.tags,
        notes=manifest.notes,
        expectation=manifest.expectation,
        release_contract=manifest.release_contract,
        baseline_history=list(manifest.baseline_history),
    )


def load_eval_suite(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    profiles_path: Path | None = None,
    validate_bundle_exists: bool = True,
) -> list[EvalCase]:
    """Load, normalize, and filter the repository-local eval suite."""

    return resolve_eval_suite_selection(
        workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
        cases_dir=cases_dir,
        profiles_path=profiles_path,
        validate_bundle_exists=validate_bundle_exists,
    ).cases


def resolve_eval_suite_selection(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    profiles_path: Path | None = None,
    validate_bundle_exists: bool = True,
) -> EvalSuiteSelection:
    """Resolve one suite selection from optional profile, case, and tag filters."""

    workspace_root = workspace_root.resolve()
    loaded_cases = [
        load_eval_case(
            case_path,
            workspace_root=workspace_root,
            validate_bundle_exists=validate_bundle_exists,
        )
        for case_path in discover_eval_case_files(workspace_root, cases_dir=cases_dir)
    ]
    loaded_cases.sort(key=lambda case: case.case_id)

    profile: EvalProfileDefinition | None = None
    if profile_id is not None:
        profile = load_eval_profile(
            workspace_root,
            profile_id=profile_id,
            profiles_path=profiles_path,
        )
        loaded_cases = _select_cases_for_profile(loaded_cases, profile)

    if case_ids:
        loaded_cases = _filter_cases_by_case_ids(
            loaded_cases,
            case_ids,
            profile=profile,
        )

    if tags:
        loaded_cases = _filter_cases_by_tags(loaded_cases, tags)

    return EvalSuiteSelection(profile=profile, cases=loaded_cases)


def load_eval_profile(
    workspace_root: Path,
    *,
    profile_id: str,
    profiles_path: Path | None = None,
) -> EvalProfileDefinition:
    """Load one named eval verification profile from the repository manifest."""

    normalized_profile_id = _normalize_identifier(profile_id, kind="profile_id")
    manifest = load_eval_profile_manifest(
        workspace_root,
        profiles_path=profiles_path,
    )
    profiles_by_id = {profile.profile_id: profile for profile in manifest.profiles}
    try:
        return profiles_by_id[normalized_profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown eval profile: {normalized_profile_id}") from exc


def load_eval_profile_manifest(
    workspace_root: Path,
    *,
    profiles_path: Path | None = None,
) -> EvalProfileManifest:
    """Load the repository-local eval profile manifest from disk."""

    resolved_profile_path = _resolve_profiles_path(
        workspace_root,
        profiles_path=profiles_path,
    )
    try:
        raw_manifest = resolved_profile_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval profile manifest: {resolved_profile_path}"
        ) from exc

    try:
        manifest = EvalProfileManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval profile manifest {resolved_profile_path}: {exc}"
        ) from exc

    _ensure_path_within_root(
        resolved_profile_path,
        workspace_root.resolve(),
        kind="eval profile manifest",
    )
    return manifest


def _resolve_cases_dir(workspace_root: Path, *, cases_dir: Path | None) -> Path:
    if cases_dir is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_CASES_DIR).resolve()
    if cases_dir.is_absolute():
        return cases_dir.resolve()
    return (workspace_root.resolve() / cases_dir).resolve()


def _resolve_profiles_path(
    workspace_root: Path,
    *,
    profiles_path: Path | None,
) -> Path:
    if profiles_path is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_PROFILES_PATH).resolve()
    if profiles_path.is_absolute():
        return profiles_path.resolve()
    return (workspace_root.resolve() / profiles_path).resolve()


def _select_cases_for_profile(
    loaded_cases: list[EvalCase],
    profile: EvalProfileDefinition,
) -> list[EvalCase]:
    selected_cases = loaded_cases
    if profile.case_ids:
        selected_cases = _filter_cases_by_case_ids(
            selected_cases,
            profile.case_ids,
            profile=profile,
            selection_scope="definition",
        )
        if profile.tags:
            required_tags = set(profile.tags)
            missing_tags = [
                case.case_id
                for case in selected_cases
                if not required_tags.issubset(set(case.tags))
            ]
            if missing_tags:
                raise ValueError(
                    f"eval profile {profile.profile_id} defines case ids missing "
                    f"required tag"
                    f"{'s' if len(required_tags) > 1 else ''}: "
                    + ", ".join(missing_tags)
                )

    if profile.tags:
        selected_cases = _filter_cases_by_tags(selected_cases, profile.tags)

    if profile.case_ids:
        missing_stage = [
            case.case_id
            for case in selected_cases
            if profile.verification_stage
            not in case.release_contract.verification_stages
        ]
        if missing_stage:
            raise ValueError(
                f"eval profile {profile.profile_id} includes case"
                f"{'s' if len(missing_stage) > 1 else ''} without verification stage "
                f"{profile.verification_stage}: " + ", ".join(missing_stage)
            )

    selected_cases = [
        case
        for case in selected_cases
        if profile.verification_stage in case.release_contract.verification_stages
    ]
    _validate_profile_selection(profile, selected_cases)
    return selected_cases


def _validate_profile_selection(
    profile: EvalProfileDefinition,
    selected_cases: list[EvalCase],
) -> None:
    if not profile.blocking:
        return
    advisory_case_ids = [
        case.case_id
        for case in selected_cases
        if case.release_contract.baseline_refresh_policy == "advisory"
    ]
    if advisory_case_ids:
        raise ValueError(
            f"blocking eval profile {profile.profile_id} cannot include advisory "
            f"baseline case"
            f"{'s' if len(advisory_case_ids) > 1 else ''}: "
            + ", ".join(advisory_case_ids)
        )


def _filter_cases_by_case_ids(
    loaded_cases: list[EvalCase],
    case_ids: Sequence[str],
    *,
    profile: EvalProfileDefinition | None,
    selection_scope: Literal["selection", "definition"] = "selection",
) -> list[EvalCase]:
    normalized_case_ids = [
        _normalize_identifier(case_id, kind="case_id") for case_id in case_ids
    ]
    cases_by_id = {case.case_id: case for case in loaded_cases}
    missing_case_ids = [
        case_id for case_id in normalized_case_ids if case_id not in cases_by_id
    ]
    if missing_case_ids:
        if profile is None:
            raise ValueError(
                "unknown eval case id"
                + ("s" if len(missing_case_ids) > 1 else "")
                + ": "
                + ", ".join(missing_case_ids)
            )
        scope_phrase = (
            "defines" if selection_scope == "definition" else "does not select"
        )
        raise ValueError(
            f"eval profile {profile.profile_id} {scope_phrase} eval case id"
            f"{'s' if len(missing_case_ids) > 1 else ''}: "
            + ", ".join(missing_case_ids)
        )
    return [cases_by_id[case_id] for case_id in normalized_case_ids]


def _filter_cases_by_tags(
    loaded_cases: list[EvalCase],
    tags: Sequence[str],
) -> list[EvalCase]:
    required_tags = {_normalize_identifier(tag, kind="tag") for tag in tags}
    return [case for case in loaded_cases if required_tags.issubset(set(case.tags))]


def _normalize_identifier(value: str, *, kind: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{kind} must not be empty")
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"{kind} must match {_IDENTIFIER_PATTERN.pattern}: {value!r}")
    return normalized


def _ensure_path_within_root(path: Path, root: Path, *, kind: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{kind} must stay within workspace root: {path}") from exc
