"""Typed models for workspace knowledge posture."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

type KnowledgePostureStatus = Literal[
    "fresh",
    "stale",
    "missing",
    "invalidated",
    "degraded",
    "advisory",
    "historical-only",
]
type KnowledgeCueSourceKind = Literal[
    "workspace-memory",
    "repository-index",
    "checkpoint",
    "context-compaction",
    "verification-summary",
    "provider-evidence",
    "session",
]


class KnowledgeCueProvenance(BaseModel):
    """Bounded source reference behind one knowledge posture cue."""

    model_config = ConfigDict(extra="forbid")

    label: str
    source_kind: KnowledgeCueSourceKind
    source_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    artifact_id: str | None = None
    path: str | None = None
    source_start_sequence: int | None = Field(default=None, ge=0)
    source_end_sequence: int | None = Field(default=None, ge=0)
    last_sequence: int | None = Field(default=None, ge=0)
    timestamp: str | None = None
    freshness: str | None = None
    detail: str | None = None


class KnowledgePostureCue(BaseModel):
    """One derived freshness cue for a local knowledge source."""

    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    status: KnowledgePostureStatus
    summary: str
    authoritative_source: str
    inspect_commands: list[str] = Field(default_factory=list)
    source_count: int = Field(default=0, ge=0)
    provenance: list[KnowledgeCueProvenance] = Field(default_factory=list)


class WorkspaceKnowledgePosture(BaseModel):
    """Unified operator-facing knowledge posture."""

    model_config = ConfigDict(extra="forbid")

    overall_status: KnowledgePostureStatus
    cues: list[KnowledgePostureCue]
    next_actions: list[str] = Field(default_factory=list)


__all__ = [
    "KnowledgeCueProvenance",
    "KnowledgeCueSourceKind",
    "KnowledgePostureCue",
    "KnowledgePostureStatus",
    "WorkspaceKnowledgePosture",
]
