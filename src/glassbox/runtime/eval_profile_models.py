"""Pydantic models for named replay eval profiles."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.eval_constants import EVAL_PROFILE_MANIFEST_VERSION
from glassbox.runtime.eval_constants import EvalProfileTrack
from glassbox.runtime.eval_constants import EvalVerificationStage
from glassbox.runtime.eval_constants import normalize_identifier


class EvalProfileBudget(BaseModel):
    """Repository-owned size and determinism guardrails for one eval profile."""

    model_config = ConfigDict(extra="forbid")

    max_selected_case_count: int | None = Field(default=None, ge=1)
    max_selected_invariant_case_count: int | None = Field(default=None, ge=0)
    max_recorded_model_call_count: int | None = Field(default=None, ge=0)
    max_case_artifact_bytes: int | None = Field(default=None, ge=0)
    allow_unsupported_cases: bool | None = None
    allow_advisory_cases: bool | None = None
    promotion_policy: str | None = None
    demotion_policy: str | None = None

    @field_validator("promotion_policy", "demotion_policy")
    @classmethod
    def validate_policy_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EvalProfileDefinition(BaseModel):
    """Repository-owned selection rules for one named verification stage."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    title: str
    description: str | None = None
    verification_stage: EvalVerificationStage
    track: EvalProfileTrack = "deterministic"
    tags: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    blocking: bool = True
    budget: EvalProfileBudget | None = None

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        return normalize_identifier(value, kind="profile_id")

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
            candidate = normalize_identifier(tag, kind="tag")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for case_id in value:
            candidate = normalize_identifier(case_id, kind="case_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @model_validator(mode="after")
    def validate_track_contract(self) -> EvalProfileDefinition:
        if self.track != "live-provider-canary":
            return self
        if self.blocking:
            raise ValueError(
                "live-provider-canary eval profiles must stay non-blocking"
            )
        if self.verification_stage != "advisory":
            raise ValueError(
                "live-provider-canary eval profiles must use advisory "
                "verification_stage"
            )
        return self


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
