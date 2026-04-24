"""Shared typed models for runtime context assembly."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import SessionStatus
from glassbox.tools import ToolSchema

PYTEST_FAILURE_DIGEST_ARTIFACT_KIND = "context_pytest_failure_digest"


class RepositoryContextSnapshot(BaseModel):
    """Deterministic top-level repository summary for prompt context."""

    model_config = ConfigDict(extra="forbid")

    workspace_name: str
    high_signal_paths: list[str] = Field(default_factory=list)
    top_level_directories: list[str] = Field(default_factory=list)
    additional_directory_count: int = Field(default=0, ge=0)
    top_level_files: list[str] = Field(default_factory=list)
    additional_file_count: int = Field(default=0, ge=0)
    project_markers: list[str] = Field(default_factory=list)


class RuntimeContextNoteSnapshot(BaseModel):
    """Bounded runtime note summary for operator inspection."""

    model_config = ConfigDict(extra="forbid")

    category: str
    message: str
    inherited: bool = False
    source_session_id: SessionId | None = None


class WorkingSetItemSnapshot(BaseModel):
    """One bounded working-set item derived from explicit runtime signals."""

    model_config = ConfigDict(extra="forbid")

    subject_kind: str
    subject: str
    summary: str
    reasons: list[str] = Field(default_factory=list)
    signal_types: list[str] = Field(default_factory=list)
    inherited: bool = False


class WorkingSetSnapshot(BaseModel):
    """A deterministic summary of the current local slice of work."""

    model_config = ConfigDict(extra="forbid")

    items: list[WorkingSetItemSnapshot] = Field(default_factory=list)
    additional_item_count: int = Field(default=0, ge=0)


class PytestFailureDigestArtifact(BaseModel):
    """Stored artifact payload for a bounded failing-test digest."""

    model_config = ConfigDict(extra="forbid")

    summary_kind: Literal["pytest_failure_digest"] = "pytest_failure_digest"
    source_tool_name: Literal["run_tests"] = "run_tests"
    target_paths: list[str] = Field(default_factory=list)
    keyword_filter: str | None = None
    failure_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    timed_out: bool = False
    failing_tests: list[str] = Field(default_factory=list)


class ArtifactBackedContextSummarySnapshot(BaseModel):
    """One explicit artifact-backed context summary available to the runtime."""

    model_config = ConfigDict(extra="forbid")

    summary_kind: str
    provenance_class: Literal["artifact_backed_summary"] = "artifact_backed_summary"
    source_tool_name: str
    artifact_kind: str
    artifact_path: str
    summary: str
    freshness: Literal["fresh", "stale"] = "fresh"
    target_paths: list[str] = Field(default_factory=list)
    keyword_filter: str | None = None
    failing_tests: list[str] = Field(default_factory=list)
    failure_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    timed_out: bool = False
    source_tool_call_id: ToolCallId | None = None
    inherited: bool = False


class ArtifactBackedContextSnapshot(BaseModel):
    """Bounded artifact-backed context summaries for the current session."""

    model_config = ConfigDict(extra="forbid")

    summaries: list[ArtifactBackedContextSummarySnapshot] = Field(default_factory=list)
    additional_summary_count: int = Field(default=0, ge=0)


class RuntimeContextSnapshot(BaseModel):
    """Shared operator-facing runtime context summary."""

    model_config = ConfigDict(extra="forbid")

    repository_context: RepositoryContextSnapshot
    runtime_notes: list[RuntimeContextNoteSnapshot] = Field(default_factory=list)
    additional_runtime_note_count: int = Field(default=0, ge=0)
    working_set: WorkingSetSnapshot = Field(
        default_factory=lambda: WorkingSetSnapshot()
    )
    artifact_context: ArtifactBackedContextSnapshot = Field(
        default_factory=lambda: ArtifactBackedContextSnapshot()
    )


class PolicyContext(BaseModel):
    """Policy-relevant session context used for prompt assembly."""

    model_config = ConfigDict(extra="forbid")

    approval_mode: str
    pending_approval_id: ApprovalId | None = None


class TurnContext(BaseModel):
    """Structured context derived for one model turn."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    session_status: SessionStatus
    current_turn_id: TurnId | None = None
    last_sequence: int = Field(ge=0)
    transcript: list[TranscriptMessage]
    available_tools: list[ToolSchema]
    policy: PolicyContext
    repo_context: str | None = None
    memory_notes: list[str] = Field(default_factory=list)
    working_set: WorkingSetSnapshot | None = None
    artifact_context: ArtifactBackedContextSnapshot | None = None
