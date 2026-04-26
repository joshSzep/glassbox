"""Pydantic models for repository-local replay eval cases."""

from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.eval_constants import ALL_EVAL_INVARIANTS
from glassbox.runtime.eval_constants import EVAL_CASE_MANIFEST_VERSION
from glassbox.runtime.eval_constants import EvalBaselineOperation
from glassbox.runtime.eval_constants import EvalBaselineRefreshPolicy
from glassbox.runtime.eval_constants import EvalCaseSeverity
from glassbox.runtime.eval_constants import EvalInvariant
from glassbox.runtime.eval_constants import EvalVerificationStage
from glassbox.runtime.eval_constants import default_verification_stages
from glassbox.runtime.eval_constants import normalize_identifier


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
            return ALL_EVAL_INVARIANTS
        return tuple(self.invariants)


class EvalCaseReleaseContract(BaseModel):
    """Release-oriented metadata for one replay-backed eval case."""

    model_config = ConfigDict(extra="forbid")

    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    severity: EvalCaseSeverity = "medium"
    verification_stages: list[EvalVerificationStage] = Field(
        default_factory=default_verification_stages
    )
    baseline_refresh_policy: EvalBaselineRefreshPolicy = "review_required"

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value, kind="owner")

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for capability in value:
            candidate = normalize_identifier(capability, kind="capability")
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
        return normalize_identifier(value, kind="case_id")

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
            candidate = normalize_identifier(tag, kind="tag")
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
