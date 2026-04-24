"""Typed context assembly for model turns."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from glassbox.core.events import (
    ModelToolCallRequested,
    ToolArtifactRecorded,
)
from glassbox.core.ids import ApprovalId, SessionId, ToolCallId, TurnId
from glassbox.core.models import (
    ApprovalRecord,
    RuntimeNoteRecord,
    SessionRecord,
    ToolCallRecord,
    TranscriptMessage,
)
from glassbox.core.types import ApprovalStatus, SessionStatus, ToolExecutionStatus
from glassbox.services import ArtifactRepository, SessionRepository
from glassbox.tools import ToolRegistry, ToolSchema

_DEFAULT_REPOSITORY_CONTEXT_DIRECTORY_LIMIT = 8
_DEFAULT_REPOSITORY_CONTEXT_FILE_LIMIT = 8
_DEFAULT_RUNTIME_NOTE_LIMIT = 8
_DEFAULT_WORKING_SET_LIMIT = 8
_DEFAULT_ARTIFACT_CONTEXT_LIMIT = 4
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
PYTEST_FAILURE_DIGEST_ARTIFACT_KIND = "context_pytest_failure_digest"
_PYTEST_FAILURE_NODE_RE = re.compile(
    r"^(?:FAILED|ERROR)\s+([^\s]+)",
    re.MULTILINE,
)

_WORKING_SET_SIGNAL_PRIORITY = {
    "approval": 100,
    "tool_request_test_path": 92,
    "tool_request_path": 90,
    "tool_artifact": 80,
    "runtime_note": 70,
    "inherited_runtime_note": 60,
    "tool_call": 50,
    "lineage": 40,
}


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


class TurnContextBuilder:
    """Build a stable typed turn context from persisted session data."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def build(
        self,
        session_id: SessionId,
        *,
        tool_schemas: Sequence[ToolSchema] = (),
        tool_registry: ToolRegistry | None = None,
        repo_context: str | None = None,
        memory_notes: Sequence[str] = (),
        working_set: WorkingSetSnapshot | None = None,
        artifact_context: ArtifactBackedContextSnapshot | None = None,
    ) -> TurnContext:
        session = self._session_repository.get_session(session_id)
        session_state = self._session_repository.get_session_state(session_id)
        if session is None or session_state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        if tool_registry is not None and tool_schemas:
            raise ValueError("pass either tool_registry or tool_schemas, not both")

        transcript = sorted(
            self._session_repository.list_transcript_messages(session_id),
            key=lambda message: message.created_at,
        )
        normalized_tools = (
            tool_registry.list_schemas()
            if tool_registry is not None
            else normalize_tool_schemas(tool_schemas)
        )
        return TurnContext(
            session_id=session_id,
            session_status=session_state.status,
            current_turn_id=session_state.current_turn_id,
            last_sequence=session_state.last_sequence,
            transcript=transcript,
            available_tools=normalized_tools,
            policy=PolicyContext(
                approval_mode=session.approval_mode,
                pending_approval_id=session_state.pending_approval_id,
            ),
            repo_context=repo_context,
            memory_notes=list(memory_notes),
            working_set=working_set,
            artifact_context=artifact_context,
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


def format_repository_context_for_prompt(
    snapshot: RepositoryContextSnapshot,
) -> str:
    """Render a repository-context snapshot into a stable prompt fragment."""

    lines = [f"Workspace: {snapshot.workspace_name}"]
    if snapshot.high_signal_paths:
        lines.append("High-signal paths: " + ", ".join(snapshot.high_signal_paths))
    if snapshot.top_level_directories:
        directory_line = ", ".join(snapshot.top_level_directories)
        if snapshot.additional_directory_count:
            directory_line += f" (+{snapshot.additional_directory_count} more)"
        lines.append("Top-level directories: " + directory_line)
    if snapshot.top_level_files:
        file_line = ", ".join(snapshot.top_level_files)
        if snapshot.additional_file_count:
            file_line += f" (+{snapshot.additional_file_count} more)"
        lines.append("Top-level files: " + file_line)
    if snapshot.project_markers:
        lines.append("Project markers: " + ", ".join(snapshot.project_markers))
    return "\n".join(lines)


def build_runtime_context_snapshot(
    workspace_root: Path,
    runtime_notes: Sequence[RuntimeNoteRecord],
    *,
    note_limit: int = _DEFAULT_RUNTIME_NOTE_LIMIT,
    working_set: WorkingSetSnapshot | None = None,
    artifact_context: ArtifactBackedContextSnapshot | None = None,
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


def build_working_set_snapshot(
    session_repository: SessionRepository,
    session_id: SessionId,
    *,
    item_limit: int = _DEFAULT_WORKING_SET_LIMIT,
) -> WorkingSetSnapshot:
    """Derive a bounded working set from explicit session state and events."""

    session = session_repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")

    working_items: dict[tuple[str, str], _WorkingSetCandidate] = {}
    insertion_counter = 0

    def register_candidate(
        *,
        subject_kind: str,
        subject: str,
        summary: str,
        reason: str,
        signal_type: str,
        inherited: bool = False,
        recency_offset: int = 0,
    ) -> None:
        nonlocal insertion_counter
        normalized_subject = subject.strip()
        if normalized_subject == "":
            return

        key = (subject_kind, normalized_subject.casefold())
        candidate = working_items.get(key)
        score = _WORKING_SET_SIGNAL_PRIORITY[signal_type] - recency_offset
        if candidate is None:
            working_items[key] = _WorkingSetCandidate(
                item=WorkingSetItemSnapshot(
                    subject_kind=subject_kind,
                    subject=normalized_subject,
                    summary=summary,
                    reasons=[reason],
                    signal_types=[signal_type],
                    inherited=inherited,
                ),
                score=score,
                first_seen=insertion_counter,
            )
            insertion_counter += 1
            return

        candidate.score = max(candidate.score, score)
        candidate.item.summary = candidate.item.summary or summary
        candidate.item.inherited = candidate.item.inherited and inherited
        if reason not in candidate.item.reasons:
            candidate.item.reasons.append(reason)
        if signal_type not in candidate.item.signal_types:
            candidate.item.signal_types.append(signal_type)

    recent_events = list(reversed(session_repository.read_session_events(session_id)))
    for recency_offset, event in enumerate(recent_events):
        payload = event.payload
        if isinstance(payload, ModelToolCallRequested):
            _register_tool_request_candidates(
                payload,
                register_candidate,
                recency_offset=recency_offset,
            )
            continue
        if isinstance(payload, ToolArtifactRecorded) and payload.path:
            register_candidate(
                subject_kind="artifact",
                subject=payload.path,
                summary=_artifact_summary(payload.artifact_kind),
                reason=(f"{payload.artifact_kind} artifact recorded at {payload.path}"),
                signal_type="tool_artifact",
                recency_offset=recency_offset,
            )

    recent_approvals = sorted(
        session_repository.list_approvals(session_id),
        key=lambda approval: approval.requested_at,
        reverse=True,
    )
    for recency_offset, approval in enumerate(recent_approvals):
        register_candidate(
            subject_kind="approval",
            subject=approval.subject,
            summary=(
                "pending approval focus"
                if approval.status == ApprovalStatus.PENDING
                else "recent approval context"
            ),
            reason=_approval_reason(approval),
            signal_type="approval",
            recency_offset=recency_offset,
        )

    runtime_notes = sorted(
        session_repository.list_runtime_notes(session_id),
        key=lambda note: note.created_at,
        reverse=True,
    )
    for recency_offset, note in enumerate(runtime_notes):
        inherited = note.inherited
        register_candidate(
            subject_kind="note",
            subject=f"[{note.category}] {note.message}",
            summary=("inherited runtime note" if inherited else "runtime note"),
            reason=_runtime_note_reason(note),
            signal_type=("inherited_runtime_note" if inherited else "runtime_note"),
            inherited=inherited,
            recency_offset=recency_offset,
        )

    recent_tool_calls = sorted(
        session_repository.list_tool_calls(session_id),
        key=_tool_call_sort_key,
        reverse=True,
    )
    for recency_offset, tool_call in enumerate(recent_tool_calls):
        if (
            tool_call.status == ToolExecutionStatus.SUCCEEDED
            and tool_call.summary is None
        ):
            continue
        register_candidate(
            subject_kind="tool",
            subject=tool_call.tool_name,
            summary="recent tool execution",
            reason=_tool_call_reason(tool_call),
            signal_type="tool_call",
            recency_offset=recency_offset,
        )

    if session.parent_session_id is not None:
        lineage_subject = (
            session.branch_label
            if session.branch_label is not None
            else f"parent {str(session.parent_session_id)[:8]}"
        )
        register_candidate(
            subject_kind="branch",
            subject=lineage_subject,
            summary="inherited branch context",
            reason=_lineage_reason(session),
            signal_type="lineage",
            inherited=True,
        )

    ordered_candidates = sorted(
        working_items.values(),
        key=lambda candidate: (
            -candidate.score,
            candidate.first_seen,
            candidate.item.subject,
        ),
    )
    limited_candidates = ordered_candidates[:item_limit]

    return WorkingSetSnapshot(
        items=[candidate.item for candidate in limited_candidates],
        additional_item_count=max(len(ordered_candidates) - len(limited_candidates), 0),
    )


def normalize_tool_schemas(tool_schemas: Iterable[ToolSchema]) -> list[ToolSchema]:
    """Return tool schemas in stable name order with duplicate protection."""

    ordered_tools = sorted(tool_schemas, key=lambda tool: tool.name)
    seen_names: set[str] = set()
    for tool in ordered_tools:
        if tool.name in seen_names:
            raise ValueError(f"duplicate tool schema name: {tool.name}")
        seen_names.add(tool.name)
    return ordered_tools


def format_transcript_for_prompt(transcript: Sequence[TranscriptMessage]) -> str:
    """Render transcript summaries into a stable prompt-friendly text block."""

    lines: list[str] = []
    for message in transcript:
        content = "\n".join(part.text for part in message.parts)
        lines.append(f"{message.role.upper()}: {content}")
    return "\n\n".join(lines)


def format_tool_schemas_for_prompt(tool_schemas: Sequence[ToolSchema]) -> str:
    """Render tool schemas into a stable prompt-friendly text block."""

    lines: list[str] = []
    for tool in normalize_tool_schemas(tool_schemas):
        lines.append(f"- {tool.name}: {tool.description}")
    return "\n".join(lines)


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


class _WorkingSetCandidate:
    def __init__(
        self,
        *,
        item: WorkingSetItemSnapshot,
        score: int,
        first_seen: int,
    ) -> None:
        self.item = item
        self.score = score
        self.first_seen = first_seen


def _register_tool_request_candidates(
    payload: ModelToolCallRequested,
    register_candidate,
    *,
    recency_offset: int,
) -> None:
    arguments = _decode_tool_arguments(payload.arguments_json)
    if payload.tool_name == "run_tests":
        for raw_path in _string_list(arguments.get("paths")):
            register_candidate(
                subject_kind="test",
                subject=raw_path,
                summary="recent test target",
                reason=f"run_tests targeted {raw_path}",
                signal_type="tool_request_test_path",
                recency_offset=recency_offset,
            )
        return

    for raw_path in _extract_path_arguments(arguments):
        register_candidate(
            subject_kind="file",
            subject=raw_path,
            summary="recently targeted workspace path",
            reason=f"{payload.tool_name} targeted {raw_path}",
            signal_type="tool_request_path",
            recency_offset=recency_offset,
        )


def _decode_tool_arguments(arguments_json: str) -> dict[str, object]:
    try:
        decoded = json.loads(arguments_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return {str(key): value for key, value in decoded.items()}


def _extract_path_arguments(arguments: dict[str, object]) -> list[str]:
    extracted_paths: list[str] = []
    for key in ("path", "paths"):
        value = arguments.get(key)
        extracted_paths.extend(_string_list(value))
    return extracted_paths


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


def _artifact_summary(artifact_kind: str) -> str:
    if "test" in artifact_kind.casefold() or "pytest" in artifact_kind.casefold():
        return "recent test artifact"
    return "recent artifact"


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


def _approval_reason(approval: ApprovalRecord) -> str:
    status_text = "pending" if approval.status == ApprovalStatus.PENDING else "resolved"
    return f"{status_text} approval: {approval.reason}"


def _runtime_note_reason(note: RuntimeNoteRecord) -> str:
    note_prefix = "inherited runtime note" if note.inherited else "runtime note"
    return f"{note_prefix} [{note.category}] {note.message}"


def _tool_call_reason(tool_call: ToolCallRecord) -> str:
    summary = tool_call.summary or tool_call.status.value.replace("_", " ")
    return f"{tool_call.tool_name}: {summary}"


def _lineage_reason(session: SessionRecord) -> str:
    parent_prefix = (
        str(session.parent_session_id)[:8]
        if session.parent_session_id is not None
        else "unknown"
    )
    if session.branch_label is not None:
        return f"branch '{session.branch_label}' inherited from {parent_prefix}"
    return f"session inherited branch context from {parent_prefix}"


def _tool_call_sort_key(tool_call: ToolCallRecord):
    timestamp = tool_call.completed_at or tool_call.started_at
    return (timestamp is not None, timestamp or datetime.min.replace(tzinfo=UTC))
