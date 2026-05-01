"""Shared models for durable tool-attempt recovery actions."""

from dataclasses import dataclass

from pydantic import BaseModel

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ToolCallId
from glassbox.core.models import ToolAttemptRecord


class ToolAttemptRecoveryError(ValueError):
    """Raised when a tool-attempt recovery action is unsafe or impossible."""


class ToolAttemptArtifactReference(BaseModel):
    """Operator-facing pointer to retained output evidence."""

    artifact_id: ArtifactId
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = None


class ToolAttemptInspection(BaseModel):
    """Inspect result for one durable tool attempt."""

    attempt: ToolAttemptRecord
    source_tool_call_id: ToolCallId | None = None
    source_arguments: dict[str, object] | None = None
    output_artifact: ToolAttemptArtifactReference | None = None
    correlated_event_count: int
    recovery_actions: list[str]


class ToolAttemptRecoveryResult(BaseModel):
    """Result returned by retry and abandon recovery actions."""

    message: str
    original_attempt: ToolAttemptRecord
    retry_attempt: ToolAttemptRecord | None = None


@dataclass(frozen=True, slots=True)
class RecoveredToolCallRequest:
    """Minimal request shape used when replaying retained tool arguments."""

    tool_name: str
    arguments: dict[str, object]
    tool_call_id: str


__all__ = [
    "RecoveredToolCallRequest",
    "ToolAttemptArtifactReference",
    "ToolAttemptInspection",
    "ToolAttemptRecoveryError",
    "ToolAttemptRecoveryResult",
]
