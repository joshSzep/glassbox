"""HTTP transport models and serializers for workspace memory APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.web.session_api import PageInfoResponse


class WorkspaceMemoryProvenanceResponse(BaseModel):
    source_type: str
    source_label: str | None = None
    session_id: str | None = None
    source_sequence: int | None = None
    task_id: str | None = None
    artifact_id: str | None = None
    tool_call_id: str | None = None
    note: str | None = None


class WorkspaceMemoryEntryResponse(BaseModel):
    memory_id: str
    session_id: str
    kind: str
    state: str
    content: str
    summary: str | None = None
    provenance: WorkspaceMemoryProvenanceResponse
    created_by: str
    created_at: datetime
    updated_at: datetime
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    invalidated_by: str | None = None
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None
    last_used_at: datetime | None = None
    use_count: int
    tags: list[str]
    redacted: bool
    import_source: str | None = None
    pruned_by: str | None = None
    pruned_at: datetime | None = None
    prune_reason: str | None = None
    last_sequence: int


class WorkspaceMemoryListPageResponse(BaseModel):
    page: PageInfoResponse
    items: list[WorkspaceMemoryEntryResponse]


class WorkspaceMemoryDetailResponse(BaseModel):
    entry: WorkspaceMemoryEntryResponse


def build_workspace_memory_entry_response(
    entry: WorkspaceMemoryEntry,
) -> WorkspaceMemoryEntryResponse:
    """Serialize a projected workspace memory entry into HTTP output."""

    payload = entry.model_dump(mode="json")
    payload["provenance"] = _provenance_response(entry.provenance).model_dump(
        mode="json"
    )
    return WorkspaceMemoryEntryResponse.model_validate(payload)


def build_workspace_memory_entry_responses(
    entries: Sequence[WorkspaceMemoryEntry],
) -> list[WorkspaceMemoryEntryResponse]:
    """Serialize multiple projected workspace memory entries."""

    return [build_workspace_memory_entry_response(entry) for entry in entries]


def _provenance_response(
    provenance: WorkspaceMemoryProvenance,
) -> WorkspaceMemoryProvenanceResponse:
    return WorkspaceMemoryProvenanceResponse.model_validate(
        provenance.model_dump(mode="json")
    )
