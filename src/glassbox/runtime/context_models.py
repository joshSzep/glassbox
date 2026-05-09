"""Shared typed models for runtime context assembly."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
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


class WorkspaceMemoryContextProvenanceSnapshot(BaseModel):
    """Bounded provenance for a workspace-memory prompt item."""

    model_config = ConfigDict(extra="forbid")

    source_type: str
    source_label: str | None = None
    session_id: SessionId | None = None
    source_sequence: int | None = Field(default=None, ge=0)
    task_id: TaskId | None = None
    artifact_id: ArtifactId | None = None
    tool_call_id: ToolCallId | None = None


class WorkspaceMemoryContextItemSnapshot(BaseModel):
    """One confirmed workspace-memory item selected for turn context."""

    model_config = ConfigDict(extra="forbid")

    memory_id: WorkspaceMemoryId
    kind: str
    summary: str
    content: str
    provenance: WorkspaceMemoryContextProvenanceSnapshot
    confirmed_by: str | None = None
    redacted: bool = False
    use_count: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


class RepositoryIndexContextItemSnapshot(BaseModel):
    """One repository-index item selected for turn context."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    kind: str
    name: str
    summary: str | None = None
    path: str | None = None
    symbol: str | None = None
    source_type: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    tags: list[str] = Field(default_factory=list)


class RepositoryIndexContextSnapshot(BaseModel):
    """Bounded repository-index context with freshness posture."""

    model_config = ConfigDict(extra="forbid")

    status: str
    path: str
    schema_version: int | None = None
    builder_version: str | None = None
    source_digest: str | None = None
    entry_count: int = Field(default=0, ge=0)
    items: list[RepositoryIndexContextItemSnapshot] = Field(default_factory=list)
    additional_item_count: int = Field(default=0, ge=0)
    context_bytes: int = Field(default=0, ge=0)
    detail: str | None = None


class RepositoryIntelligenceContextSourceSnapshot(BaseModel):
    """One repository-intelligence source considered for prompt context."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_kind: str
    freshness: Literal[
        "fresh",
        "stale",
        "missing",
        "degraded",
        "conflicting",
        "partial",
    ]
    confidence: str
    included: bool
    provenance: str | None = None
    source_digest: str | None = None
    item_count: int | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)


class RepositoryIntelligenceContextItemSnapshot(BaseModel):
    """One bounded repository-intelligence item selected for turn context."""

    model_config = ConfigDict(extra="forbid")

    item_kind: str
    title: str
    summary: str
    source_names: list[str] = Field(default_factory=list)
    freshness: Literal[
        "fresh",
        "stale",
        "missing",
        "degraded",
        "conflicting",
        "partial",
    ] = "fresh"
    confidence: str = "unknown"
    provenance: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RepositoryIntelligenceContextSnapshot(BaseModel):
    """Bounded repository-intelligence context with replay-visible sources."""

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "fresh",
        "stale",
        "missing",
        "degraded",
        "conflicting",
        "partial",
    ]
    schema_version: int = Field(default=1, ge=1)
    source_digest: str | None = None
    sources: list[RepositoryIntelligenceContextSourceSnapshot] = Field(
        default_factory=list
    )
    items: list[RepositoryIntelligenceContextItemSnapshot] = Field(default_factory=list)
    additional_item_count: int = Field(default=0, ge=0)
    excluded_sources: list[RepositoryIntelligenceContextSourceSnapshot] = Field(
        default_factory=list
    )
    context_bytes: int = Field(default=0, ge=0)
    budget_bytes: int | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class CheckpointResumeSnapshot(BaseModel):
    """Checkpoint-derived resume context with explicit trust posture."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: TaskCheckpointId
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    objective: str
    current_phase: LongRunPhase | None = None
    completed_step: str | None = None
    next_action: str
    blockers: list[str] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    verification_status: str | None = None
    budget_status: str | None = None
    recovery_guidance: str
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    checkpoint_sequence: int = Field(ge=0)
    latest_session_sequence: int = Field(ge=0)
    status: Literal[
        "usable",
        "stale",
        "blocked",
        "workspace_drift",
        "non_resumable",
    ]
    safe_to_use: bool
    context_source: Literal["checkpoint", "replay"]
    reason: str
    limitations: list[str] = Field(default_factory=list)
    workspace_drift_paths: list[str] = Field(default_factory=list)


class ContextCompactionContextItemSnapshot(BaseModel):
    """Fresh compaction selected for prompt context."""

    model_config = ConfigDict(extra="forbid")

    compaction_id: ContextCompactionId
    scope: ContextCompactionScope
    artifact_id: ArtifactId
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    summary: str
    freshness: ContextCompactionFreshness
    limitations: list[str] = Field(default_factory=list)
    decision_count: int = Field(default=0, ge=0)
    unresolved_question_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    freshness_reason: str | None = None
    superseded_by_compaction_id: ContextCompactionId | None = None


class ContextCompactionFreshnessCueSnapshot(BaseModel):
    """Operator-facing cue for a stale or invalidated compaction."""

    model_config = ConfigDict(extra="forbid")

    compaction_id: ContextCompactionId
    scope: ContextCompactionScope
    artifact_id: ArtifactId
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    freshness: ContextCompactionFreshness
    reason: str
    superseded_by_compaction_id: ContextCompactionId | None = None


class ContextCompactionContextSnapshot(BaseModel):
    """Bounded fresh context compactions available to the turn."""

    model_config = ConfigDict(extra="forbid")

    items: list[ContextCompactionContextItemSnapshot] = Field(default_factory=list)
    stale_items: list[ContextCompactionFreshnessCueSnapshot] = Field(
        default_factory=list
    )
    additional_item_count: int = Field(default=0, ge=0)
    stale_item_count: int = Field(default=0, ge=0)


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
    workspace_memory: list[WorkspaceMemoryContextItemSnapshot] = Field(
        default_factory=list
    )
    additional_workspace_memory_count: int = Field(default=0, ge=0)
    workspace_memory_context_bytes: int = Field(default=0, ge=0)
    repository_index: RepositoryIndexContextSnapshot | None = None
    repository_intelligence: RepositoryIntelligenceContextSnapshot | None = None
    checkpoint_resume: CheckpointResumeSnapshot | None = None
    context_compactions: ContextCompactionContextSnapshot = Field(
        default_factory=lambda: ContextCompactionContextSnapshot()
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
    workspace_memory: list[WorkspaceMemoryContextItemSnapshot] = Field(
        default_factory=list
    )
    repository_index: RepositoryIndexContextSnapshot | None = None
    repository_intelligence: RepositoryIntelligenceContextSnapshot | None = None
    checkpoint_context: CheckpointResumeSnapshot | None = None
    context_compactions: ContextCompactionContextSnapshot | None = None
