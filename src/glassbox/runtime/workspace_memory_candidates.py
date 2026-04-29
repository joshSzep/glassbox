"""Workspace memory candidate models and pure filtering helpers."""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import SessionId
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import WorkspaceMemoryKind

SUPPRESSED_NOTE_CATEGORIES = {"debug", "scratch", "transient"}


class WorkspaceMemoryCandidate(BaseModel):
    """A deterministic, operator-reviewed memory proposal."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    session_id: SessionId
    kind: WorkspaceMemoryKind
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    provenance: WorkspaceMemoryProvenance
    tags: list[str] = Field(default_factory=list)
    redacted: bool = False
    source_label: str
    created_at: datetime | None = None


class ModelMemorySuggestion(BaseModel):
    """Model-proposed memory candidate text awaiting review."""

    model_config = ConfigDict(extra="forbid")

    kind: WorkspaceMemoryKind = WorkspaceMemoryKind.FACT
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    source_label: str = "model-assisted extraction"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class MemoryExtractionPolicy(BaseModel):
    """Review-gated controls for automatic memory candidate extraction."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_candidates: int | None = Field(default=None, ge=1)
    max_age_days: int = Field(default=30, ge=1)
    allow_model_assisted: bool = False
    min_model_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


def candidate_is_useful(candidate: WorkspaceMemoryCandidate) -> bool:
    content = " ".join(candidate.content.split())
    if len(content) < 16:
        return False
    if candidate.provenance.source_label is not None:
        label = candidate.provenance.source_label.casefold()
        if any(category in label for category in SUPPRESSED_NOTE_CATEGORIES):
            return False
    return True


def dedupe_candidates(
    candidates: Sequence[WorkspaceMemoryCandidate],
) -> list[WorkspaceMemoryCandidate]:
    seen: set[tuple[str, str]] = set()
    deduped: list[WorkspaceMemoryCandidate] = []
    for candidate in candidates:
        key = (candidate.kind.value, " ".join(candidate.content.casefold().split()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def filter_stale_candidates(
    candidates: Sequence[WorkspaceMemoryCandidate],
    *,
    now: datetime,
    max_age: timedelta,
) -> list[WorkspaceMemoryCandidate]:
    fresh: list[WorkspaceMemoryCandidate] = []
    for candidate in candidates:
        if candidate.created_at is not None and now - candidate.created_at > max_age:
            continue
        fresh.append(candidate)
    return fresh


def build_candidate(
    *,
    session_id: SessionId,
    kind: WorkspaceMemoryKind,
    content: str,
    summary: str | None,
    provenance: WorkspaceMemoryProvenance,
    tags: list[str],
    redacted: bool,
    source_label: str,
    created_at: datetime | None,
) -> WorkspaceMemoryCandidate:
    candidate_id = candidate_id_for(kind, content, provenance)
    return WorkspaceMemoryCandidate(
        candidate_id=candidate_id,
        session_id=session_id,
        kind=kind,
        content=content,
        summary=summary,
        provenance=provenance,
        tags=list(dict.fromkeys(tags)),
        redacted=redacted,
        source_label=source_label,
        created_at=created_at,
    )


def candidate_id_for(
    kind: WorkspaceMemoryKind,
    content: str,
    provenance: WorkspaceMemoryProvenance,
) -> str:
    payload = {
        "kind": kind.value,
        "content": content,
        "provenance": provenance.model_dump(mode="json", exclude_none=True),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return digest[:24]


def summarize_candidate_content(content: str) -> str:
    normalized = " ".join(content.split())
    return normalized[:497] + "..." if len(normalized) > 500 else normalized


__all__ = [
    "MemoryExtractionPolicy",
    "ModelMemorySuggestion",
    "WorkspaceMemoryCandidate",
    "build_candidate",
    "candidate_id_for",
    "candidate_is_useful",
    "dedupe_candidates",
    "filter_stale_candidates",
    "summarize_candidate_content",
]
