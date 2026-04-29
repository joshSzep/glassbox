"""HTTP transport models and serializers for repository index APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.task_api import BackgroundJobResponse


class RepositoryIndexProvenanceResponse(BaseModel):
    source_type: str
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    source_label: str | None = None
    content_sha256: str | None = None
    tool_name: str | None = None
    note: str | None = None


class RepositoryIndexEntryResponse(BaseModel):
    entry_id: str
    kind: str
    name: str
    summary: str | None = None
    path: str | None = None
    symbol: str | None = None
    language: str | None = None
    provenance: list[RepositoryIndexProvenanceResponse]
    tags: list[str]
    updated_at: datetime


class RepositoryIndexStatusResponse(BaseModel):
    status: str
    path: str
    entry_count: int
    built_at: datetime | None = None
    schema_version: int | None = None
    builder_version: str | None = None
    source_digest: str | None = None
    detail: str | None = None


class RepositoryIndexSearchPageResponse(BaseModel):
    query: str
    page: PageInfoResponse
    items: list[RepositoryIndexEntryResponse]


class RepositoryIndexEntryDetailResponse(BaseModel):
    entry: RepositoryIndexEntryResponse


class RepositoryIndexRebuildRequest(BaseModel):
    session_id: str | None = None
    requested_by: str = "operator"
    background: bool = True


class RepositoryIndexRebuildResponse(BaseModel):
    mode: str
    status: str
    index: RepositoryIndexStatusResponse | None = None
    job: BackgroundJobResponse | None = None
    detail: str | None = None


def build_repository_index_status_response(
    snapshot: RepositoryIndexSnapshot,
    *,
    path: str,
) -> RepositoryIndexStatusResponse:
    return RepositoryIndexStatusResponse(
        status=snapshot.status.value,
        path=path,
        entry_count=len(snapshot.entries),
        built_at=snapshot.built_at,
        schema_version=snapshot.schema_version,
        builder_version=snapshot.builder_version,
        source_digest=snapshot.source_digest,
    )


def build_repository_index_entry_response(
    entry: RepositoryIndexEntry,
) -> RepositoryIndexEntryResponse:
    return RepositoryIndexEntryResponse(
        entry_id=entry.entry_id,
        kind=entry.kind.value,
        name=entry.name,
        summary=entry.summary,
        path=entry.path.as_posix() if entry.path is not None else None,
        symbol=entry.symbol,
        language=entry.language,
        provenance=[_provenance_response(item) for item in entry.provenance],
        tags=entry.tags,
        updated_at=entry.updated_at,
    )


def build_repository_index_entry_responses(
    entries: Sequence[RepositoryIndexEntry],
) -> list[RepositoryIndexEntryResponse]:
    return [build_repository_index_entry_response(entry) for entry in entries]


def _provenance_response(
    provenance: RepositoryIndexProvenance,
) -> RepositoryIndexProvenanceResponse:
    return RepositoryIndexProvenanceResponse(
        source_type=provenance.source_type.value,
        path=provenance.path.as_posix() if provenance.path is not None else None,
        line_start=provenance.line_start,
        line_end=provenance.line_end,
        source_label=provenance.source_label,
        content_sha256=provenance.content_sha256,
        tool_name=provenance.tool_name,
        note=provenance.note,
    )
