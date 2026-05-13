"""Verification plan Pydantic contracts shared across Glassbox surfaces."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.models_operator_flow import NextActionCommandRecipe
from glassbox.core.models_operator_flow import NextActionEvidenceRef
from glassbox.core.models_operator_flow import NextActionTarget
from glassbox.core.types_verification_plan import VerificationCheckKind
from glassbox.core.types_verification_plan import VerificationFailureCategory
from glassbox.core.types_verification_plan import VerificationPlanLifecycleState
from glassbox.core.types_verification_plan import VerificationPlanSource


class VerificationPlanEntry(BaseModel):
    """One explicit local verification check selected or proposed for a task."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str = Field(min_length=1, max_length=200)
    kind: VerificationCheckKind
    lifecycle_state: VerificationPlanLifecycleState = (
        VerificationPlanLifecycleState.SELECTED
    )
    target: NextActionTarget | None = None
    command: list[str] = Field(default_factory=list, max_length=64)
    command_recipe: NextActionCommandRecipe | None = None
    source: VerificationPlanSource
    rationale: str = Field(min_length=1, max_length=2000)
    selection_rationale: str | None = Field(default=None, min_length=1, max_length=2000)
    blocking: bool = True
    timeout_seconds: int = Field(default=300, ge=1, le=7200)
    expected_exit_codes: list[int] = Field(default_factory=lambda: [0], min_length=1)
    changed_paths: list[Path] = Field(default_factory=list, max_length=100)
    eval_case_id: str | None = Field(default=None, min_length=1, max_length=200)
    eval_profile_id: str | None = Field(default=None, min_length=1, max_length=200)
    release_surfaces: list[str] = Field(default_factory=list, max_length=20)
    evidence_references: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    stale_reasons: list[str] = Field(default_factory=list, max_length=20)
    manual_evidence_required: bool = False
    execution_requires_approval: bool = True
    superseded_by_verification_id: TaskVerificationId | None = None

    @field_validator("expected_exit_codes")
    @classmethod
    def normalize_expected_exit_codes(cls, value: list[int]) -> list[int]:
        normalized = list(dict.fromkeys(value))
        if not normalized:
            raise ValueError("expected_exit_codes must not be empty")
        for exit_code in normalized:
            if exit_code < 0 or exit_code > 255:
                raise ValueError("expected_exit_codes must be between 0 and 255")
        return normalized

    @model_validator(mode="after")
    def validate_verification_contract(self) -> VerificationPlanEntry:
        if self.kind == VerificationCheckKind.EVAL and (
            self.eval_case_id is None and self.eval_profile_id is None
        ):
            raise ValueError(
                "eval verification requires eval_case_id or eval_profile_id"
            )
        executable_states = {
            VerificationPlanLifecycleState.PROPOSED,
            VerificationPlanLifecycleState.SELECTED,
            VerificationPlanLifecycleState.RUNNING,
            VerificationPlanLifecycleState.PASSED,
            VerificationPlanLifecycleState.FAILED,
            VerificationPlanLifecycleState.STALE,
        }
        if (
            self.lifecycle_state in executable_states
            and not self.command
            and self.command_recipe is None
        ):
            raise ValueError(
                "executable verification entries require command or command_recipe"
            )
        if (
            self.lifecycle_state == VerificationPlanLifecycleState.MANUAL_ONLY
            and not self.manual_evidence_required
        ):
            raise ValueError("manual-only verification requires manual evidence")
        if (
            self.lifecycle_state == VerificationPlanLifecycleState.SUPERSEDED
            and self.superseded_by_verification_id is None
        ):
            raise ValueError("superseded verification requires replacement id")
        return self


class VerificationPlan(BaseModel):
    """A bounded collection of verification checks for one task."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    entries: list[VerificationPlanEntry] = Field(min_length=1, max_length=20)
    max_repair_attempts: int = Field(default=0, ge=0, le=10)
    selection_sources: list[VerificationPlanSource] = Field(
        default_factory=list,
        max_length=20,
    )
    residual_risk_policy: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_unique_verification_ids(self) -> VerificationPlan:
        verification_ids = [entry.verification_id for entry in self.entries]
        if len(verification_ids) != len(set(verification_ids)):
            raise ValueError("verification plan entries require unique verification_id")
        return self


class VerificationFailureDigest(BaseModel):
    """Compact failure evidence suitable for event payloads and artifacts."""

    model_config = ConfigDict(extra="forbid")

    category: VerificationFailureCategory
    summary: str = Field(min_length=1, max_length=4000)
    exit_code: int | None = Field(default=None, ge=0)
    timed_out: bool = False
    artifact_id: ArtifactId | None = None
    first_relevant_line: str | None = Field(default=None, max_length=1000)


__all__ = [
    "VerificationFailureDigest",
    "VerificationPlan",
    "VerificationPlanEntry",
]
