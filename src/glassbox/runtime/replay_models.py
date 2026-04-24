"""Typed replay models shared across replay bundle, execution, and reporting."""

from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import SessionId
from glassbox.core.models import InheritedTranscriptMessage
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.replay_manifests import ReplayModelCallManifest
from glassbox.runtime.replay_manifests import ReplayToolRequestManifest
from glassbox.runtime.replay_manifests import ReplayToolResultManifest
from glassbox.runtime.replay_manifests import ReplayTurnOutputManifest

type ReplayOutcome = Literal[
    "exact_match",
    "manifest_drift",
    "behavioral_drift",
    "unsupported_session",
    "replay_failure",
]
type ReplayTriageClassification = Literal[
    "exact_match",
    "manifest_drift",
    "context_source_drift",
    "behavioral_drift",
    "unsupported_session",
    "replay_failure",
]
type ReplayTriageSeverity = Literal["info", "warning", "error"]

REPLAY_BUNDLE_KIND = "glassbox_replay_bundle"
REPLAY_BUNDLE_VERSION = 1


class ReplayAction(BaseModel):
    """One source-session input that should be re-applied during replay."""

    model_config = ConfigDict(extra="forbid")

    action_type: Literal["user_message", "approval", "user_answer", "runtime_note"]
    text: str | None = None
    decision: ApprovalDecision | None = None
    answer: str | None = None
    category: str | None = None
    message: str | None = None


class ReplayRecordedToolCall(BaseModel):
    """Recorded tool call reconstructed for one model response."""

    model_config = ConfigDict(extra="forbid")

    provider_tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ReplayRecordedModelCall(BaseModel):
    """Recorded model call input manifest and output fixture."""

    model_config = ConfigDict(extra="forbid")

    manifest: ReplayModelCallManifest
    assistant_text: str | None = None
    text_deltas: list[str] = Field(default_factory=list)
    tool_calls: list[ReplayRecordedToolCall] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None


class ReplayTranscriptPart(BaseModel):
    """Normalized transcript part used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    text: str


class ReplayTranscriptMessage(BaseModel):
    """Normalized transcript message used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    role: str
    parts: list[ReplayTranscriptPart]


class ReplayToolCallSnapshot(BaseModel):
    """Normalized tool call projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: str
    summary: str | None = None


class ReplayApprovalSnapshot(BaseModel):
    """Normalized approval projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    reason: str
    status: str
    decided_by: str | None = None


class ReplayQuestionSnapshot(BaseModel):
    """Normalized ask_user flow record used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str | None = None


class ReplayLineageSnapshot(BaseModel):
    """Normalized session lineage metadata used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    parent_session_id: str
    forked_from_turn_id: str
    forked_from_sequence: int = Field(ge=0)
    branch_label: str | None = None


class ReplayFinalStateSnapshot(BaseModel):
    """Normalized final session projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    status: str
    has_active_turn: bool = False
    has_pending_approval: bool = False
    has_pending_question: bool = False


class ReplayNormalizedSession(BaseModel):
    """Behavior-focused normalized session snapshot for replay diffs."""

    model_config = ConfigDict(extra="forbid")

    transcript: list[ReplayTranscriptMessage]
    lineage: ReplayLineageSnapshot | None = None
    inherited_transcript: list[ReplayTranscriptMessage] = Field(default_factory=list)
    post_fork_transcript: list[ReplayTranscriptMessage] = Field(default_factory=list)
    tool_calls: list[ReplayToolCallSnapshot]
    approvals: list[ReplayApprovalSnapshot]
    questions: list[ReplayQuestionSnapshot]
    event_families: list[str]
    final_state: ReplayFinalStateSnapshot


class ReplayBundle(BaseModel):
    """Typed replay input bundle loaded from a persisted session."""

    model_config = ConfigDict(extra="forbid")

    bundle_kind: Literal["glassbox_replay_bundle"] = REPLAY_BUNDLE_KIND
    bundle_version: int = REPLAY_BUNDLE_VERSION
    source_session_id: SessionId
    session_config: SessionConfig
    inherited_messages: list[InheritedTranscriptMessage] = Field(default_factory=list)
    inherited_runtime_notes: list[RuntimeNoteRecord] = Field(default_factory=list)
    actions: list[ReplayAction]
    model_calls: list[ReplayRecordedModelCall]
    tool_requests: list[ReplayToolRequestManifest]
    tool_results: list[ReplayToolResultManifest]
    turn_outputs: list[ReplayTurnOutputManifest]
    baseline: ReplayNormalizedSession


class ReplayTriage(BaseModel):
    """Operator-facing triage summary for one replay outcome."""

    model_config = ConfigDict(extra="forbid")

    severity: ReplayTriageSeverity
    classification: ReplayTriageClassification
    headline: str
    first_relevant_change: str | None = None
    drift_sources: list[str] = Field(default_factory=list)
    impacted_dimensions: list[str] = Field(default_factory=list)
    recommended_inspection_path: str | None = None


class ReplayResult(BaseModel):
    """Outcome and normalized comparison payload for one replay run."""

    model_config = ConfigDict(extra="forbid")

    outcome: ReplayOutcome
    source_session_id: SessionId | None = None
    message: str | None = None
    mismatches: list[str] = Field(default_factory=list)
    baseline: ReplayNormalizedSession | None = None
    replay: ReplayNormalizedSession | None = None
    triage: ReplayTriage | None = None
