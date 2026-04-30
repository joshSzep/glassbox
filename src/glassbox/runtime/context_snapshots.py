"""Structured snapshot builders for runtime context assembly."""

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.ids import SessionId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.context_models import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_models import ArtifactBackedContextSnapshot
from glassbox.runtime.context_models import ArtifactBackedContextSummarySnapshot
from glassbox.runtime.context_models import CheckpointResumeSnapshot
from glassbox.runtime.context_models import ContextCompactionContextSnapshot
from glassbox.runtime.context_models import PytestFailureDigestArtifact
from glassbox.runtime.context_models import RepositoryContextSnapshot
from glassbox.runtime.context_models import RepositoryIndexContextItemSnapshot
from glassbox.runtime.context_models import RepositoryIndexContextSnapshot
from glassbox.runtime.context_models import RuntimeContextNoteSnapshot
from glassbox.runtime.context_models import RuntimeContextSnapshot
from glassbox.runtime.context_models import WorkingSetSnapshot
from glassbox.runtime.context_models import WorkspaceMemoryContextItemSnapshot
from glassbox.runtime.context_models import WorkspaceMemoryContextProvenanceSnapshot
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

_DEFAULT_REPOSITORY_CONTEXT_DIRECTORY_LIMIT = 8
_DEFAULT_REPOSITORY_CONTEXT_FILE_LIMIT = 8
_DEFAULT_RUNTIME_NOTE_LIMIT = 8
_DEFAULT_ARTIFACT_CONTEXT_LIMIT = 4
_DEFAULT_WORKSPACE_MEMORY_LIMIT = 5
_DEFAULT_REPOSITORY_INDEX_ITEM_LIMIT = 8
_DEFAULT_WORKSPACE_MEMORY_CONTEXT_BYTES = 2000
_DEFAULT_REPOSITORY_INDEX_CONTEXT_BYTES = 2000
_HIGH_SIGNAL_REPOSITORY_ENTRIES = (
    "README.md",
    "pyproject.toml",
    "package.json",
    "src",
    "tests",
    "docs",
    "evals",
    "frontend",
)
_PYTEST_FAILURE_NODE_RE = re.compile(
    r"^(?:FAILED|ERROR)\s+([^\s]+)",
    re.MULTILINE,
)


def build_repository_context_snapshot(
    workspace_root: Path,
    *,
    directory_limit: int = _DEFAULT_REPOSITORY_CONTEXT_DIRECTORY_LIMIT,
    file_limit: int = _DEFAULT_REPOSITORY_CONTEXT_FILE_LIMIT,
) -> RepositoryContextSnapshot:
    """Return a bounded deterministic summary of the workspace root."""

    resolved_root = workspace_root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        return RepositoryContextSnapshot(
            workspace_name=resolved_root.name or str(resolved_root),
        )

    entries = sorted(
        (entry for entry in resolved_root.iterdir() if not entry.name.startswith(".")),
        key=lambda entry: entry.name,
    )
    directory_names = [entry.name for entry in entries if entry.is_dir()]
    file_names = [entry.name for entry in entries if entry.is_file()]

    limited_directories = directory_names[:directory_limit]
    limited_files = file_names[:file_limit]

    return RepositoryContextSnapshot(
        workspace_name=resolved_root.name or str(resolved_root),
        high_signal_paths=[
            _repository_entry_display_name(entry_name)
            for entry_name in _HIGH_SIGNAL_REPOSITORY_ENTRIES
            if entry_name in directory_names or entry_name in file_names
        ],
        top_level_directories=[
            _repository_entry_display_name(directory_name)
            for directory_name in limited_directories
        ],
        additional_directory_count=max(
            len(directory_names) - len(limited_directories),
            0,
        ),
        top_level_files=limited_files,
        additional_file_count=max(len(file_names) - len(limited_files), 0),
        project_markers=_repository_project_markers(directory_names, file_names),
    )


def build_runtime_context_snapshot(
    workspace_root: Path,
    runtime_notes: Sequence[RuntimeNoteRecord],
    *,
    note_limit: int = _DEFAULT_RUNTIME_NOTE_LIMIT,
    working_set: WorkingSetSnapshot | None = None,
    artifact_context: ArtifactBackedContextSnapshot | None = None,
    workspace_memory: Sequence[WorkspaceMemoryContextItemSnapshot] = (),
    additional_workspace_memory_count: int = 0,
    workspace_memory_context_bytes: int = 0,
    repository_index: RepositoryIndexContextSnapshot | None = None,
    checkpoint_resume: CheckpointResumeSnapshot | None = None,
    context_compactions: ContextCompactionContextSnapshot | None = None,
) -> RuntimeContextSnapshot:
    """Return a bounded operator-facing summary of the current runtime context."""

    limited_notes = list(runtime_notes[:note_limit])
    return RuntimeContextSnapshot(
        repository_context=build_repository_context_snapshot(workspace_root),
        runtime_notes=[
            RuntimeContextNoteSnapshot(
                category=note.category,
                message=note.message,
                inherited=note.inherited,
                source_session_id=note.source_session_id,
            )
            for note in limited_notes
        ],
        additional_runtime_note_count=max(len(runtime_notes) - len(limited_notes), 0),
        working_set=working_set or WorkingSetSnapshot(),
        artifact_context=artifact_context or ArtifactBackedContextSnapshot(),
        workspace_memory=list(workspace_memory),
        additional_workspace_memory_count=additional_workspace_memory_count,
        workspace_memory_context_bytes=workspace_memory_context_bytes,
        repository_index=repository_index,
        checkpoint_resume=checkpoint_resume,
        context_compactions=context_compactions or ContextCompactionContextSnapshot(),
    )


def build_workspace_memory_context_snapshot(
    session_repository: SessionRepository,
    *,
    memory_limit: int = _DEFAULT_WORKSPACE_MEMORY_LIMIT,
    context_byte_limit: int = _DEFAULT_WORKSPACE_MEMORY_CONTEXT_BYTES,
) -> tuple[list[WorkspaceMemoryContextItemSnapshot], int, int]:
    """Return bounded confirmed workspace memory for prompt context."""

    rows = session_repository.list_workspace_memory(
        state=WorkspaceMemoryState.ACTIVE,
        limit=memory_limit + 25,
    )
    candidates = [row for row in rows if row.confirmed_at is not None]
    selected: list[WorkspaceMemoryContextItemSnapshot] = []
    used_bytes = 0
    for row in candidates:
        if len(selected) >= memory_limit:
            break
        item = _workspace_memory_context_item(row)
        item_bytes = _workspace_memory_item_bytes(item)
        if selected and used_bytes + item_bytes > context_byte_limit:
            break
        selected.append(item)
        used_bytes += item_bytes
        if used_bytes >= context_byte_limit:
            break

    return selected, max(len(candidates) - len(selected), 0), used_bytes


def build_repository_index_context_snapshot(
    workspace_root: Path,
    *,
    item_limit: int = _DEFAULT_REPOSITORY_INDEX_ITEM_LIMIT,
    context_byte_limit: int = _DEFAULT_REPOSITORY_INDEX_CONTEXT_BYTES,
) -> RepositoryIndexContextSnapshot:
    """Return bounded repository-index context with explicit freshness posture."""

    path = repository_index_path(workspace_root)
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return RepositoryIndexContextSnapshot(
            status="missing",
            path=str(path),
            detail="repository index has not been built",
        )

    selected: list[RepositoryIndexContextItemSnapshot] = []
    used_bytes = 0
    if snapshot.status == RepositoryIndexFreshness.FRESH:
        for entry in sorted(snapshot.entries, key=_repository_index_entry_sort_key):
            if len(selected) >= item_limit:
                break
            item = RepositoryIndexContextItemSnapshot(
                entry_id=entry.entry_id,
                kind=entry.kind.value,
                name=entry.name,
                summary=entry.summary,
                path=entry.path.as_posix() if entry.path is not None else None,
                symbol=entry.symbol,
                source_type=(
                    entry.provenance[0].source_type.value if entry.provenance else None
                ),
                line_start=(
                    entry.provenance[0].line_start if entry.provenance else None
                ),
                line_end=(entry.provenance[0].line_end if entry.provenance else None),
                tags=list(entry.tags),
            )
            item_bytes = _repository_index_item_bytes(item)
            if selected and used_bytes + item_bytes > context_byte_limit:
                break
            selected.append(item)
            used_bytes += item_bytes
            if used_bytes >= context_byte_limit:
                break

    return RepositoryIndexContextSnapshot(
        status=snapshot.status.value,
        path=str(path),
        schema_version=snapshot.schema_version,
        builder_version=snapshot.builder_version,
        source_digest=snapshot.source_digest,
        entry_count=len(snapshot.entries),
        items=selected,
        additional_item_count=max(len(snapshot.entries) - len(selected), 0),
        context_bytes=used_bytes,
        detail=(
            "repository index is stale; items omitted until refresh"
            if snapshot.status != RepositoryIndexFreshness.FRESH
            else None
        ),
    )


def build_artifact_backed_context_snapshot(
    session_repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    *,
    include_stale: bool = True,
    summary_limit: int = _DEFAULT_ARTIFACT_CONTEXT_LIMIT,
) -> ArtifactBackedContextSnapshot:
    """Return bounded artifact-backed summaries derived from explicit artifacts."""

    session = session_repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")

    session_events = session_repository.read_session_events(session_id)
    latest_run_tests_request_sequence = max(
        (
            event.sequence
            for event in session_events
            if isinstance(event.payload, ModelToolCallRequested)
            and event.payload.tool_name == "run_tests"
        ),
        default=-1,
    )
    summaries: list[ArtifactBackedContextSummarySnapshot] = []
    for event in reversed(session_events):
        payload = event.payload
        if not isinstance(payload, ToolArtifactRecorded):
            continue
        if payload.artifact_kind != PYTEST_FAILURE_DIGEST_ARTIFACT_KIND:
            continue
        if payload.path is None:
            raise ValueError(
                "context artifact event is missing its relative artifact path"
            )

        raw_artifact = artifact_repository.read_text_artifact(Path(payload.path))
        artifact = PytestFailureDigestArtifact.model_validate_json(raw_artifact)
        freshness = (
            "stale" if latest_run_tests_request_sequence > event.sequence else "fresh"
        )
        if not include_stale and freshness != "fresh":
            continue

        summaries.append(
            ArtifactBackedContextSummarySnapshot(
                summary_kind=artifact.summary_kind,
                source_tool_name=artifact.source_tool_name,
                artifact_kind=payload.artifact_kind,
                artifact_path=payload.path,
                summary=_pytest_failure_digest_summary(artifact),
                freshness=freshness,
                target_paths=list(artifact.target_paths),
                keyword_filter=artifact.keyword_filter,
                failing_tests=list(artifact.failing_tests),
                failure_count=artifact.failure_count,
                error_count=artifact.error_count,
                timed_out=artifact.timed_out,
                source_tool_call_id=payload.tool_call_id,
            )
        )

    limited_summaries = summaries[:summary_limit]
    return ArtifactBackedContextSnapshot(
        summaries=limited_summaries,
        additional_summary_count=max(len(summaries) - len(limited_summaries), 0),
    )


def build_pytest_failure_digest_artifact(
    tool_arguments: dict[str, Any],
    tool_output_payload: dict[str, Any],
) -> PytestFailureDigestArtifact | None:
    """Build a compact artifact-backed digest from one failing pytest run."""

    failure_count = int(tool_output_payload.get("failed") or 0)
    error_count = int(tool_output_payload.get("errors") or 0)
    timed_out = bool(tool_output_payload.get("timed_out"))
    if failure_count <= 0 and error_count <= 0 and not timed_out:
        return None

    stdout = str(tool_output_payload.get("stdout") or "")
    stderr = str(tool_output_payload.get("stderr") or "")
    return PytestFailureDigestArtifact(
        target_paths=_string_list(tool_arguments.get("paths")),
        keyword_filter=(
            str(tool_arguments.get("keywords"))
            if tool_arguments.get("keywords") not in (None, "")
            else None
        ),
        failure_count=failure_count,
        error_count=error_count,
        timed_out=timed_out,
        failing_tests=_extract_pytest_failure_nodes(stdout + "\n" + stderr),
    )


def _repository_entry_display_name(entry_name: str) -> str:
    if "." not in entry_name:
        return f"{entry_name}/"
    return entry_name


def _repository_project_markers(
    directory_names: Sequence[str],
    file_names: Sequence[str],
) -> list[str]:
    markers: list[str] = []
    if "pyproject.toml" in file_names:
        markers.append("python_pyproject")
    if "package.json" in file_names:
        markers.append("javascript_package")
    if "src" in directory_names:
        markers.append("src_layout")
    if "tests" in directory_names:
        markers.append("tests_present")
    if "docs" in directory_names:
        markers.append("docs_present")
    if "evals" in directory_names:
        markers.append("evals_present")
    if "frontend" in directory_names:
        markers.append("frontend_present")
    return markers


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip() != ""
        ]
    return []


def _pytest_failure_digest_summary(artifact: PytestFailureDigestArtifact) -> str:
    target_scope = (
        ", ".join(artifact.target_paths) if artifact.target_paths else "full suite"
    )
    if artifact.timed_out:
        return f"timed out pytest run for {target_scope}"
    if artifact.error_count and artifact.failure_count:
        return (
            f"{artifact.failure_count} failing test(s) and {artifact.error_count} "
            f"error(s) for {target_scope}"
        )
    if artifact.error_count:
        return f"{artifact.error_count} pytest error(s) for {target_scope}"
    return f"{artifact.failure_count} failing test(s) for {target_scope}"


def _workspace_memory_context_item(
    row: WorkspaceMemoryEntry,
) -> WorkspaceMemoryContextItemSnapshot:
    return WorkspaceMemoryContextItemSnapshot(
        memory_id=row.memory_id,
        kind=row.kind.value,
        summary=row.summary or row.content[:160],
        content=row.content,
        provenance=WorkspaceMemoryContextProvenanceSnapshot(
            source_type=row.provenance.source_type.value,
            source_label=row.provenance.source_label,
            session_id=row.provenance.session_id,
            source_sequence=row.provenance.source_sequence,
            task_id=row.provenance.task_id,
            artifact_id=row.provenance.artifact_id,
            tool_call_id=row.provenance.tool_call_id,
        ),
        confirmed_by=row.confirmed_by,
        redacted=row.redacted,
        use_count=row.use_count,
        tags=list(row.tags),
    )


def _workspace_memory_item_bytes(item: WorkspaceMemoryContextItemSnapshot) -> int:
    return len(item.summary.encode()) + len(item.content.encode())


def _repository_index_entry_sort_key(entry) -> tuple[int, str, str]:
    return (
        _repository_index_kind_priority(entry.kind),
        entry.path.as_posix() if entry.path is not None else "",
        entry.name.casefold(),
    )


def _repository_index_kind_priority(kind: RepositoryIndexEntityKind) -> int:
    return {
        RepositoryIndexEntityKind.PROJECT_MARKER: 0,
        RepositoryIndexEntityKind.COMMAND: 1,
        RepositoryIndexEntityKind.DOC: 2,
        RepositoryIndexEntityKind.TEST: 3,
        RepositoryIndexEntityKind.FILE: 4,
        RepositoryIndexEntityKind.MODULE: 5,
        RepositoryIndexEntityKind.SYMBOL: 6,
        RepositoryIndexEntityKind.EVAL_CASE: 7,
        RepositoryIndexEntityKind.DEPENDENCY_HINT: 8,
    }.get(kind, 99)


def _repository_index_item_bytes(item: RepositoryIndexContextItemSnapshot) -> int:
    return sum(
        len(value.encode())
        for value in [
            item.kind,
            item.name,
            item.summary or "",
            item.path or "",
            item.symbol or "",
            " ".join(item.tags),
        ]
    )


def _extract_pytest_failure_nodes(output: str, *, limit: int = 5) -> list[str]:
    seen: set[str] = set()
    failing_nodes: list[str] = []
    for match in _PYTEST_FAILURE_NODE_RE.finditer(output):
        node_id = match.group(1).strip()
        if node_id in seen:
            continue
        seen.add(node_id)
        failing_nodes.append(node_id)
        if len(failing_nodes) >= limit:
            break
    return failing_nodes
