"""Repository-owned workspace defaults for local Glassbox workflows."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from pydantic import field_validator

from glassbox.core.models import AutonomyBudget
from glassbox.core.types import AutonomyMode
from glassbox.runtime.autonomy import DEFAULT_AUTONOMY_MODE
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode

WORKSPACE_PROFILE_VERSION = 1
DEFAULT_WORKSPACE_PROFILE_PATH = Path("glassbox.profile.json")
DEFAULT_MODEL_NAME = "openai:gpt-5.4"
DEFAULT_APPROVAL_MODE = "confirm"

type WorkspaceApprovalMode = Literal["confirm", "review", "on-request", "never"]
type WorkspaceDefaultSource = Literal["cli", "workspace-profile", "built-in"]


class WorkspaceRuntimeDefaults(BaseModel):
    """Session-start defaults that are safe to keep in source control."""

    model_config = ConfigDict(extra="forbid")

    model_name: str | None = Field(default=None, min_length=1)
    approval_mode: WorkspaceApprovalMode | None = None
    autonomy_mode: AutonomyMode | None = None
    autonomy_budget_preset: str | None = Field(default=None, min_length=1)

    @field_validator("autonomy_budget_preset")
    @classmethod
    def normalize_autonomy_budget_preset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        if not candidate:
            raise ValueError("autonomy_budget_preset must not be empty")
        return candidate


class WorkspaceAutonomyDefaults(BaseModel):
    """Repository-owned autonomy budget presets."""

    model_config = ConfigDict(extra="forbid")

    budget_presets: dict[str, AutonomyBudget] = Field(default_factory=dict)

    @field_validator("budget_presets")
    @classmethod
    def validate_budget_preset_names(
        cls,
        value: dict[str, AutonomyBudget],
    ) -> dict[str, AutonomyBudget]:
        for name in value:
            if not name.strip():
                raise ValueError("budget preset names must not be empty")
        return value


class WorkspaceVerificationDefaults(BaseModel):
    """Verification-routing defaults for repository-local eval workflows."""

    model_config = ConfigDict(extra="forbid")

    eval_profile: str | None = Field(default=None, min_length=1)

    @field_validator("eval_profile")
    @classmethod
    def normalize_eval_profile(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        if not candidate:
            raise ValueError("eval_profile must not be empty")
        return candidate


class WorkspaceProfile(BaseModel):
    """Versioned workspace profile loaded from a repository-owned JSON file."""

    model_config = ConfigDict(extra="forbid")

    profile_version: int = WORKSPACE_PROFILE_VERSION
    runtime: WorkspaceRuntimeDefaults = Field(default_factory=WorkspaceRuntimeDefaults)
    autonomy: WorkspaceAutonomyDefaults = Field(
        default_factory=WorkspaceAutonomyDefaults
    )
    verification: WorkspaceVerificationDefaults = Field(
        default_factory=WorkspaceVerificationDefaults
    )

    @field_validator("profile_version")
    @classmethod
    def validate_profile_version(cls, value: int) -> int:
        if value != WORKSPACE_PROFILE_VERSION:
            raise ValueError(f"unsupported workspace profile version: {value}")
        return value


@dataclass(frozen=True, slots=True)
class SessionStartDefaults:
    """Resolved session defaults and their operator-facing sources."""

    model_name: str
    model_name_source: WorkspaceDefaultSource
    approval_mode: WorkspaceApprovalMode
    approval_mode_source: WorkspaceDefaultSource
    autonomy_mode: AutonomyMode
    autonomy_mode_source: WorkspaceDefaultSource
    autonomy_budget: AutonomyBudget
    autonomy_budget_source: WorkspaceDefaultSource
    autonomy_budget_preset: str


@dataclass(frozen=True, slots=True)
class EvalProfileDefault:
    """Resolved eval profile routing and its source."""

    profile_id: str | None
    source: WorkspaceDefaultSource | None


def load_workspace_profile(workspace_root: Path) -> WorkspaceProfile | None:
    """Load the repository-owned workspace profile if one exists."""

    profile_path = workspace_profile_path(workspace_root)
    if not profile_path.exists():
        return None

    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        return WorkspaceProfile.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid workspace profile {profile_path}: {exc.msg}"
        ) from exc
    except ValidationError as exc:
        raise ValueError(f"invalid workspace profile {profile_path}: {exc}") from exc


def workspace_profile_path(workspace_root: Path) -> Path:
    """Return the resolved default workspace profile path."""

    return (workspace_root / DEFAULT_WORKSPACE_PROFILE_PATH).resolve()


def resolve_session_start_defaults(
    workspace_root: Path,
    *,
    explicit_model_name: str | None,
    explicit_approval_mode: WorkspaceApprovalMode | None,
    explicit_autonomy_mode: AutonomyMode | str | None = None,
    explicit_autonomy_budget_preset: str | None = None,
) -> SessionStartDefaults:
    """Resolve session-start defaults using CLI, profile, then built-ins."""

    profile = load_workspace_profile(workspace_root)
    profile_runtime = profile.runtime if profile is not None else None

    model_name = explicit_model_name
    model_name_source: WorkspaceDefaultSource = "cli"
    if model_name is None:
        model_name_source = "workspace-profile"
        model_name = profile_runtime.model_name if profile_runtime is not None else None
    if model_name is None:
        model_name_source = "built-in"
        model_name = DEFAULT_MODEL_NAME

    approval_mode = explicit_approval_mode
    approval_mode_source: WorkspaceDefaultSource = "cli"
    if approval_mode is None:
        approval_mode_source = "workspace-profile"
        approval_mode = (
            profile_runtime.approval_mode if profile_runtime is not None else None
        )
    if approval_mode is None:
        approval_mode_source = "built-in"
        approval_mode = DEFAULT_APPROVAL_MODE

    autonomy_mode = (
        None if explicit_autonomy_mode is None else AutonomyMode(explicit_autonomy_mode)
    )
    autonomy_mode_source: WorkspaceDefaultSource = "cli"
    if autonomy_mode is None:
        autonomy_mode_source = "workspace-profile"
        autonomy_mode = (
            profile_runtime.autonomy_mode if profile_runtime is not None else None
        )
    if autonomy_mode is None:
        autonomy_mode_source = "built-in"
        autonomy_mode = DEFAULT_AUTONOMY_MODE

    budget_preset = explicit_autonomy_budget_preset
    autonomy_budget_source: WorkspaceDefaultSource = "cli"
    if budget_preset is None:
        autonomy_budget_source = "workspace-profile"
        budget_preset = (
            profile_runtime.autonomy_budget_preset
            if profile_runtime is not None
            else None
        )
    if budget_preset is None:
        autonomy_budget_source = "built-in"
        budget_preset = autonomy_mode.value

    autonomy_budget = _resolve_autonomy_budget(
        budget_preset,
        profile,
        source=autonomy_budget_source,
    )

    return SessionStartDefaults(
        model_name=model_name,
        model_name_source=model_name_source,
        approval_mode=approval_mode,
        approval_mode_source=approval_mode_source,
        autonomy_mode=autonomy_mode,
        autonomy_mode_source=autonomy_mode_source,
        autonomy_budget=autonomy_budget,
        autonomy_budget_source=autonomy_budget_source,
        autonomy_budget_preset=budget_preset,
    )


def _resolve_autonomy_budget(
    budget_preset: str,
    profile: WorkspaceProfile | None,
    *,
    source: WorkspaceDefaultSource,
) -> AutonomyBudget:
    if profile is not None and budget_preset in profile.autonomy.budget_presets:
        return profile.autonomy.budget_presets[budget_preset].model_copy(deep=True)

    try:
        return default_budget_for_autonomy_mode(AutonomyMode(budget_preset))
    except ValueError as exc:
        if source == "workspace-profile":
            raise ValueError(
                f"unknown autonomy budget preset in workspace profile: {budget_preset}"
            ) from exc
        raise ValueError(f"unknown autonomy budget preset: {budget_preset}") from exc


def resolve_eval_profile_default(
    workspace_root: Path,
    *,
    explicit_profile: str | None,
) -> EvalProfileDefault:
    """Resolve the eval profile route using CLI, then workspace profile."""

    profile = load_workspace_profile(workspace_root)
    if explicit_profile is not None:
        return EvalProfileDefault(profile_id=explicit_profile, source="cli")

    if profile is None or profile.verification.eval_profile is None:
        return EvalProfileDefault(profile_id=None, source=None)
    return EvalProfileDefault(
        profile_id=profile.verification.eval_profile,
        source="workspace-profile",
    )
