"""Runtime-local models for imported handoff guidance."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffSafeCommand

type HandoffGuidanceState = Literal[
    "inspect-only",
    "fork-recommended",
    "continue-new-session",
    "run-verification",
    "refresh-repository",
    "reject-handoff",
]


class HandoffGuidanceBlocker(BaseModel):
    """One explicit reason that blocks or limits continuation."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=1000)
    severity: str = Field(default="medium", min_length=1, max_length=40)


class HandoffContinuationPath(BaseModel):
    """One possible recipient path after inspecting an imported handoff."""

    model_config = ConfigDict(extra="forbid")

    path_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    recommended: bool = False
    requires_explicit_mutation: bool = False


class HandoffGuidance(BaseModel):
    """Recipient-facing fork-or-continue guidance."""

    model_config = ConfigDict(extra="forbid")

    package_id: str = Field(min_length=1, max_length=300)
    session_id: str = Field(min_length=1, max_length=80)
    state: HandoffGuidanceState
    summary: str = Field(min_length=1, max_length=2000)
    blockers: list[HandoffGuidanceBlocker] = Field(default_factory=list, max_length=20)
    paths: list[HandoffContinuationPath] = Field(default_factory=list, max_length=10)
    safe_commands: list[HandoffSafeCommand] = Field(default_factory=list, max_length=20)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


__all__ = [
    "HandoffContinuationPath",
    "HandoffGuidance",
    "HandoffGuidanceBlocker",
    "HandoffGuidanceState",
]
