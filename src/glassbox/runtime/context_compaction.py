"""Artifact contract for v10 context compactions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TurnId
from glassbox.core.types import ContextCompactionScope

CONTEXT_COMPACTION_ARTIFACT_KIND = "context_compaction_v1"
CONTEXT_COMPACTION_ARTIFACT_SCHEMA_VERSION = 1


class ContextCompactionSourceReference(BaseModel):
    """One source item that the compaction can be traced back to."""

    model_config = ConfigDict(extra="forbid")

    source_type: Literal[
        "event",
        "artifact",
        "transcript",
        "task",
        "tool",
        "verification",
        "checkpoint",
    ]
    label: str = Field(min_length=1, max_length=500)
    sequence: int | None = Field(default=None, ge=0)
    artifact_id: ArtifactId | None = None
    artifact_path: str | None = Field(default=None, max_length=1000)


class ContextCompactionEvidenceItem(BaseModel):
    """A compacted assertion with explicit source references."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    source_refs: list[str] = Field(min_length=1, max_length=20)


class ContextCompactionFailureItem(BaseModel):
    """Failure evidence retained inside a compaction artifact."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    status: str | None = Field(default=None, max_length=200)
    source_refs: list[str] = Field(min_length=1, max_length=20)


class ContextCompactionArtifact(BaseModel):
    """Artifact payload for an inspectable context compaction."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["context_compaction_v1"] = CONTEXT_COMPACTION_ARTIFACT_KIND
    schema_version: Literal[1] = CONTEXT_COMPACTION_ARTIFACT_SCHEMA_VERSION
    compaction_id: ContextCompactionId
    session_id: SessionId
    scope: ContextCompactionScope
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    created_at: datetime
    summary: str = Field(min_length=1, max_length=4000)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    transcript_start_sequence: int | None = Field(default=None, ge=0)
    transcript_end_sequence: int | None = Field(default=None, ge=0)
    task_start_sequence: int | None = Field(default=None, ge=0)
    task_end_sequence: int | None = Field(default=None, ge=0)
    source_references: list[ContextCompactionSourceReference] = Field(
        min_length=1,
        max_length=200,
    )
    source_artifact_ids: list[ArtifactId] = Field(default_factory=list, max_length=50)
    decisions: list[ContextCompactionEvidenceItem] = Field(
        default_factory=list,
        max_length=100,
    )
    unresolved_questions: list[ContextCompactionEvidenceItem] = Field(
        default_factory=list,
        max_length=100,
    )
    assumptions: list[ContextCompactionEvidenceItem] = Field(
        default_factory=list,
        max_length=100,
    )
    touched_files: list[str] = Field(default_factory=list, max_length=200)
    verification_state: list[ContextCompactionEvidenceItem] = Field(
        default_factory=list,
        max_length=100,
    )
    failures: list[ContextCompactionFailureItem] = Field(
        default_factory=list,
        max_length=100,
    )
    accepted_risks: list[ContextCompactionEvidenceItem] = Field(
        default_factory=list,
        max_length=100,
    )
    limitations: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_ranges(self) -> ContextCompactionArtifact:
        _validate_ordered_range(
            self.source_start_sequence,
            self.source_end_sequence,
            "source",
        )
        _validate_optional_range(
            self.transcript_start_sequence,
            self.transcript_end_sequence,
            "transcript",
        )
        _validate_optional_range(
            self.task_start_sequence,
            self.task_end_sequence,
            "task",
        )
        reference_labels = {reference.label for reference in self.source_references}
        for item in [
            *self.decisions,
            *self.unresolved_questions,
            *self.assumptions,
            *self.verification_state,
            *self.failures,
            *self.accepted_risks,
        ]:
            missing = [ref for ref in item.source_refs if ref not in reference_labels]
            if missing:
                raise ValueError(
                    "compaction evidence source_refs must reference "
                    f"source_references labels: {missing[0]}"
                )
        return self


def _validate_optional_range(
    start: int | None,
    end: int | None,
    label: str,
) -> None:
    if start is None and end is None:
        return
    if start is None or end is None:
        raise ValueError(f"{label} range must include both start and end")
    _validate_ordered_range(start, end, label)


def _validate_ordered_range(start: int, end: int, label: str) -> None:
    if end < start:
        raise ValueError(f"{label} range end must be greater than or equal to start")


__all__ = [
    "CONTEXT_COMPACTION_ARTIFACT_KIND",
    "CONTEXT_COMPACTION_ARTIFACT_SCHEMA_VERSION",
    "ContextCompactionArtifact",
    "ContextCompactionEvidenceItem",
    "ContextCompactionFailureItem",
    "ContextCompactionSourceReference",
]
