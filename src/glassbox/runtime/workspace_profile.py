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

    return SessionStartDefaults(
        model_name=model_name,
        model_name_source=model_name_source,
        approval_mode=approval_mode,
        approval_mode_source=approval_mode_source,
    )


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
