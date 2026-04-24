"""Declarative eval case schema and discovery for replay-backed suites."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVAL_CASE_MANIFEST_VERSION = 1
DEFAULT_EVALS_ROOT = Path("evals")
DEFAULT_EVAL_CASES_DIR = DEFAULT_EVALS_ROOT / "cases"
DEFAULT_EVAL_BUNDLES_DIR = DEFAULT_EVALS_ROOT / "bundles"

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
    )


def load_eval_suite(
    workspace_root: Path,
    *,
    case_ids: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    validate_bundle_exists: bool = True,
) -> list[EvalCase]:
    """Load, normalize, and filter the repository-local eval suite."""

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

    if case_ids:
        normalized_case_ids = [
            _normalize_identifier(case_id, kind="case_id") for case_id in case_ids
        ]
        cases_by_id = {case.case_id: case for case in loaded_cases}
        missing_case_ids = [
            case_id for case_id in normalized_case_ids if case_id not in cases_by_id
        ]
        if missing_case_ids:
            raise ValueError(
                "unknown eval case id"
                + ("s" if len(missing_case_ids) > 1 else "")
                + ": "
                + ", ".join(missing_case_ids)
            )
        loaded_cases = [cases_by_id[case_id] for case_id in normalized_case_ids]

    if tags:
        required_tags = {_normalize_identifier(tag, kind="tag") for tag in tags}
        loaded_cases = [
            case for case in loaded_cases if required_tags.issubset(set(case.tags))
        ]

    return loaded_cases


def _resolve_cases_dir(workspace_root: Path, *, cases_dir: Path | None) -> Path:
    if cases_dir is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_CASES_DIR).resolve()
    if cases_dir.is_absolute():
        return cases_dir.resolve()
    return (workspace_root.resolve() / cases_dir).resolve()


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
