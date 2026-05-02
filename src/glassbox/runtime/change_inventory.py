"""Change inventory artifact contract for reviewable changesets."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.ids import ChangesetId
from glassbox.tools.workflow import DiffFileSummary
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope

CHANGE_INVENTORY_ARTIFACT_KIND = "changeset_change_inventory"
CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION = 1
CHANGE_INVENTORY_DEFAULT_MAX_PATHS = 500
CHANGE_INVENTORY_DEFAULT_MAX_BYTES = 1_000_000
CHANGE_INVENTORY_MAX_PATH_CHARS = 300
CHANGE_INVENTORY_REDACTION = "summary-only-no-raw-diff"

ChangeInventoryStageState = Literal[
    "staged",
    "unstaged",
    "mixed",
    "untracked",
    "unknown",
]
ChangeInventoryBinaryPosture = Literal["binary", "text", "unknown"]
ChangeInventoryProvenanceConfidence = Literal["direct", "inferred", "unknown"]
ChangeInventoryRiskLevel = Literal["low", "medium", "high", "unknown"]


class ChangeInventoryLimits(BaseModel):
    """Bounded artifact limits for one change inventory snapshot."""

    model_config = ConfigDict(extra="forbid")

    max_paths: int = Field(default=CHANGE_INVENTORY_DEFAULT_MAX_PATHS, ge=1, le=5000)
    max_json_bytes: int = Field(default=CHANGE_INVENTORY_DEFAULT_MAX_BYTES, ge=4096)


class ChangeInventorySourceRef(BaseModel):
    """Reference to retained evidence that caused or explained a file entry."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=100)
    identifier: str = Field(min_length=1, max_length=200)
    confidence: ChangeInventoryProvenanceConfidence = "unknown"
    event_sequence: int | None = Field(default=None, ge=0)
    event_type: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=500)


class _PathRisk(BaseModel):
    """Internal advisory risk classification for one changed path."""

    model_config = ConfigDict(extra="forbid")

    level: ChangeInventoryRiskLevel
    tags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ChangeInventoryPathEntry(BaseModel):
    """One path entry in a change inventory artifact."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=CHANGE_INVENTORY_MAX_PATH_CHARS)
    change_kind: str = Field(min_length=1, max_length=50)
    insertions: int | None = Field(default=None, ge=0)
    deletions: int | None = Field(default=None, ge=0)
    generated: bool
    test_file: bool
    docs_file: bool
    binary_posture: ChangeInventoryBinaryPosture
    policy_sensitive: bool
    staged_state: ChangeInventoryStageState = "unknown"
    source_evidence_refs: list[ChangeInventorySourceRef] = Field(default_factory=list)
    provenance_confidence: ChangeInventoryProvenanceConfidence = "unknown"
    provenance_note: str | None = Field(default=None, max_length=500)
    risk_level: ChangeInventoryRiskLevel = "unknown"
    risk_tags: list[str] = Field(default_factory=list, max_length=20)
    risk_reasons: list[str] = Field(default_factory=list, max_length=20)


class ChangeInventorySummary(BaseModel):
    """Aggregate file classification counts for a change inventory artifact."""

    model_config = ConfigDict(extra="forbid")

    changed_path_count: int = Field(ge=0)
    included_path_count: int = Field(ge=0)
    omitted_path_count: int = Field(ge=0)
    insertions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    generated_path_count: int = Field(ge=0)
    test_path_count: int = Field(ge=0)
    docs_path_count: int = Field(ge=0)
    binary_path_count: int = Field(ge=0)
    policy_sensitive_path_count: int = Field(ge=0)
    untracked_path_count: int = Field(ge=0)
    provenance_direct_path_count: int = Field(ge=0)
    provenance_inferred_path_count: int = Field(ge=0)
    provenance_unknown_path_count: int = Field(ge=0)
    externally_modified_path_count: int = Field(ge=0)
    risk_level: ChangeInventoryRiskLevel = "unknown"
    risk_summary: str | None = Field(default=None, max_length=4000)
    high_risk_path_count: int = Field(ge=0)
    medium_risk_path_count: int = Field(ge=0)
    low_risk_path_count: int = Field(ge=0)
    unresolved_risk_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)


class ChangeInventoryArtifact(BaseModel):
    """Artifact-ready changed-file inventory without raw file contents or diffs."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["changeset_change_inventory"] = (
        CHANGE_INVENTORY_ARTIFACT_KIND
    )
    schema_version: Literal[1] = CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION
    changeset_id: ChangesetId | None = None
    source: str = Field(min_length=1, max_length=100)
    scope: DiffSummaryScope | None = None
    path_filters: list[str] = Field(default_factory=list)
    redaction: Literal["summary-only-no-raw-diff"] = CHANGE_INVENTORY_REDACTION
    raw_diff_included: Literal[False] = False
    raw_file_contents_included: Literal[False] = False
    truncated: bool
    size_limited: bool
    limits: ChangeInventoryLimits
    summary: ChangeInventorySummary
    paths: list[ChangeInventoryPathEntry]
    limitations: list[str] = Field(default_factory=list)


def change_inventory_from_diff_summary(
    diff_summary: DiffSummaryResult,
    *,
    changeset_id: ChangesetId | None = None,
    limits: ChangeInventoryLimits | None = None,
    provenance_events: Sequence[EventEnvelope] | None = None,
) -> ChangeInventoryArtifact:
    """Build a bounded change inventory artifact from workspace diff evidence."""

    resolved_limits = limits or ChangeInventoryLimits()
    source_files = _source_files(diff_summary)
    provenance_index = (
        change_inventory_provenance_from_events(
            provenance_events,
            candidate_paths=[file_summary.path for file_summary in source_files],
        )
        if provenance_events is not None
        else {}
    )
    entries = [
        change_inventory_entry_from_diff_file(
            file_summary,
            source_evidence_refs=provenance_index.get(
                _redacted_relative_path(file_summary.path),
                [],
            ),
            provenance_index_available=provenance_events is not None,
        )
        for file_summary in source_files[: resolved_limits.max_paths]
    ]
    artifact = ChangeInventoryArtifact(
        changeset_id=changeset_id,
        source="workspace_diff_summary",
        scope=diff_summary.scope,
        path_filters=_bounded_paths(diff_summary.path_filters),
        truncated=diff_summary.truncated or len(source_files) > len(entries),
        size_limited=False,
        limits=resolved_limits,
        summary=_summary_for_entries(
            entries,
            changed_path_count=len(source_files),
            omitted_path_count=max(0, len(source_files) - len(entries)),
        ),
        paths=entries,
        limitations=_limitations(diff_summary, source_files, entries),
    )
    return _enforce_size_limit(artifact, resolved_limits)


def change_inventory_entry_from_diff_file(
    file_summary: DiffFileSummary,
    *,
    source_evidence_refs: Sequence[ChangeInventorySourceRef] | None = None,
    provenance_index_available: bool = False,
) -> ChangeInventoryPathEntry:
    """Convert a diff file summary into the stable inventory path shape."""

    path = _redacted_relative_path(file_summary.path)
    evidence_refs = _dedupe_source_refs(source_evidence_refs or [])
    confidence = _path_provenance_confidence(evidence_refs)
    risk = _risk_for_diff_file(
        file_summary,
        path=path,
        provenance_confidence=confidence,
    )
    return ChangeInventoryPathEntry(
        path=path,
        change_kind=file_summary.change_kind,
        insertions=file_summary.insertions,
        deletions=file_summary.deletions,
        generated=file_summary.generated,
        test_file=file_summary.test_file,
        docs_file=file_summary.docs_file,
        binary_posture="binary" if file_summary.binary else "text",
        policy_sensitive=file_summary.policy_sensitive,
        staged_state=_stage_state_for_change_kind(file_summary.change_kind),
        source_evidence_refs=evidence_refs,
        provenance_confidence=confidence,
        provenance_note=_provenance_note(
            path,
            confidence,
            provenance_index_available=provenance_index_available,
        ),
        risk_level=risk.level,
        risk_tags=risk.tags,
        risk_reasons=risk.reasons,
    )


def change_inventory_provenance_from_events(
    events: Sequence[EventEnvelope],
    *,
    candidate_paths: Sequence[str] = (),
) -> dict[str, list[ChangeInventorySourceRef]]:
    """Derive path-level provenance references from retained session events."""

    refs_by_path: dict[str, list[ChangeInventorySourceRef]] = {}
    known_paths = set(_normalized_candidate_paths(candidate_paths))
    verification_paths: dict[str, list[str]] = {}

    for event in events:
        payload = event.payload
        event_type = payload.event_type
        if isinstance(payload, ModelToolCallRequested):
            refs = _refs_from_tool_call_request(event, payload)
        elif isinstance(payload, ToolOutputChunk):
            refs = _refs_from_text_event(
                event,
                paths=sorted(known_paths),
                kind="tool_output",
                identifier=_identifier(event.tool_call_id, fallback=event.event_id),
                confidence="inferred",
                summary="tool output mentioned this path",
            )
        elif isinstance(payload, ToolExecutionCompleted):
            refs = _refs_from_text_event(
                event,
                paths=sorted(known_paths),
                kind="tool_execution",
                identifier=_identifier(event.tool_call_id, fallback=event.event_id),
                confidence="inferred",
                summary="tool completion summary mentioned this path",
            )
        elif isinstance(payload, ToolArtifactRecorded | ReplayArtifactRecorded):
            refs = _refs_from_artifact_event(event, payload)
        elif isinstance(payload, TaskStepCompleted):
            refs = _refs_from_text_event(
                event,
                paths=sorted(known_paths),
                kind="task_step",
                identifier=_identifier(event.task_id, fallback=event.event_id),
                confidence="inferred",
                summary="task step summary mentioned this path",
            )
        elif isinstance(payload, TaskCheckpointCreated):
            refs = _refs_from_explicit_paths(
                event,
                payload.touched_files,
                kind="task_checkpoint",
                identifier=_identifier(event.checkpoint_id, fallback=event.event_id),
                confidence="direct",
                summary="checkpoint recorded this path as touched",
            )
        elif isinstance(payload, TaskVerificationPlanned):
            changed_paths = [
                _path_to_string(path) for path in payload.verification.changed_paths
            ]
            verification_paths[str(payload.verification.verification_id)] = [
                _redacted_relative_path(path) for path in changed_paths
            ]
            refs = _refs_from_explicit_paths(
                event,
                changed_paths,
                kind="verification_plan",
                identifier=_identifier(payload.verification.verification_id),
                confidence="inferred",
                summary="verification plan targeted this path",
            )
        elif event_type in {
            "TaskVerificationStarted",
            "TaskVerificationStreamed",
            "TaskVerificationFailed",
            "TaskVerificationSkipped",
            "TaskVerificationCompleted",
            "TaskVerificationResidualRiskAccepted",
        }:
            refs = _refs_from_explicit_paths(
                event,
                verification_paths.get(str(event.verification_id), []),
                kind="verification_record",
                identifier=_identifier(event.verification_id, fallback=event.event_id),
                confidence="inferred",
                summary="verification record is linked to this path",
            )
        elif event_type in {
            "BranchCandidateExecuted",
            "BranchCandidateVerified",
            "BranchCandidatesCompared",
            "BranchCandidateSelected",
        }:
            refs = _refs_from_text_event(
                event,
                paths=sorted(known_paths),
                kind="branch_candidate",
                identifier=_identifier(event.candidate_id, fallback=event.event_id),
                confidence="inferred",
                summary="branch candidate evidence mentioned this path",
            )
        else:
            refs = {}

        for path, path_refs in refs.items():
            refs_by_path.setdefault(path, []).extend(path_refs)
            known_paths.add(path)

    return {
        path: _dedupe_source_refs(refs)
        for path, refs in refs_by_path.items()
        if path != "<redacted-path>"
    }


def change_inventory_artifact_json(artifact: ChangeInventoryArtifact) -> str:
    """Serialize a change inventory artifact with stable key ordering."""

    return json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _source_files(diff_summary: DiffSummaryResult) -> list[DiffFileSummary]:
    if diff_summary.artifact_payload is not None:
        return list(diff_summary.artifact_payload.files)
    return list(diff_summary.files)


def _summary_for_entries(
    entries: Sequence[ChangeInventoryPathEntry],
    *,
    changed_path_count: int,
    omitted_path_count: int,
) -> ChangeInventorySummary:
    risk_level = _aggregate_risk_level(entries)
    unresolved_risk_count = sum(
        1 for entry in entries if entry.risk_level in {"high", "medium"}
    )
    return ChangeInventorySummary(
        changed_path_count=changed_path_count,
        included_path_count=len(entries),
        omitted_path_count=omitted_path_count,
        insertions=sum(entry.insertions or 0 for entry in entries),
        deletions=sum(entry.deletions or 0 for entry in entries),
        generated_path_count=sum(1 for entry in entries if entry.generated),
        test_path_count=sum(1 for entry in entries if entry.test_file),
        docs_path_count=sum(1 for entry in entries if entry.docs_file),
        binary_path_count=sum(
            1 for entry in entries if entry.binary_posture == "binary"
        ),
        policy_sensitive_path_count=sum(
            1 for entry in entries if entry.policy_sensitive
        ),
        untracked_path_count=sum(
            1 for entry in entries if entry.change_kind == "untracked"
        ),
        provenance_direct_path_count=sum(
            1 for entry in entries if entry.provenance_confidence == "direct"
        ),
        provenance_inferred_path_count=sum(
            1 for entry in entries if entry.provenance_confidence == "inferred"
        ),
        provenance_unknown_path_count=sum(
            1 for entry in entries if entry.provenance_confidence == "unknown"
        ),
        externally_modified_path_count=sum(
            1
            for entry in entries
            if entry.provenance_confidence == "unknown"
            and entry.staged_state != "untracked"
        ),
        risk_level=risk_level,
        risk_summary=_risk_summary(entries, risk_level),
        high_risk_path_count=sum(1 for entry in entries if entry.risk_level == "high"),
        medium_risk_path_count=sum(
            1 for entry in entries if entry.risk_level == "medium"
        ),
        low_risk_path_count=sum(1 for entry in entries if entry.risk_level == "low"),
        unresolved_risk_count=unresolved_risk_count,
        accepted_risk_count=0,
    )


def _limitations(
    diff_summary: DiffSummaryResult,
    source_files: Sequence[DiffFileSummary],
    entries: Sequence[ChangeInventoryPathEntry],
) -> list[str]:
    limitations = [
        "inventory is summary-only and does not include raw diffs or file contents",
    ]
    if any(entry.provenance_confidence == "unknown" for entry in entries):
        limitations.append(
            "some files have no matching Glassbox provenance and may be manual "
            "or externally modified"
        )
    if diff_summary.error is not None:
        limitations.append(f"source diff summary error: {diff_summary.error}")
    if diff_summary.truncated or len(source_files) > len(entries):
        limitations.append("path list is truncated by inventory limits")
    return limitations


def _enforce_size_limit(
    artifact: ChangeInventoryArtifact,
    limits: ChangeInventoryLimits,
) -> ChangeInventoryArtifact:
    current = artifact
    while (
        len(change_inventory_artifact_json(current).encode("utf-8"))
        > limits.max_json_bytes
        and current.paths
    ):
        next_paths = current.paths[: max(0, len(current.paths) // 2)]
        omitted = current.summary.changed_path_count - len(next_paths)
        current = current.model_copy(
            update={
                "paths": next_paths,
                "truncated": True,
                "size_limited": True,
                "summary": _summary_for_entries(
                    next_paths,
                    changed_path_count=current.summary.changed_path_count,
                    omitted_path_count=max(0, omitted),
                ),
                "limitations": sorted(
                    {
                        *current.limitations,
                        "path list was reduced to satisfy artifact byte limit",
                    }
                ),
            }
        )
    return current


def _bounded_paths(paths: Sequence[str]) -> list[str]:
    return [_redacted_relative_path(path) for path in paths[:50]]


def _redacted_relative_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if (
        normalized.startswith("/")
        or normalized.startswith("../")
        or "/../" in normalized
    ):
        return "<redacted-path>"
    if len(normalized) > CHANGE_INVENTORY_MAX_PATH_CHARS:
        return normalized[: CHANGE_INVENTORY_MAX_PATH_CHARS - 15] + "...<truncated>"
    return normalized or "<unknown-path>"


def _dedupe_source_refs(
    source_refs: Sequence[ChangeInventorySourceRef],
    *,
    max_refs: int = 8,
) -> list[ChangeInventorySourceRef]:
    deduped: list[ChangeInventorySourceRef] = []
    seen: set[tuple[str, str, int | None]] = set()
    for source_ref in sorted(source_refs, key=_source_ref_sort_key):
        key = (
            source_ref.kind,
            source_ref.identifier,
            source_ref.event_sequence,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source_ref)
        if len(deduped) >= max_refs:
            break
    return deduped


def _source_ref_sort_key(
    source_ref: ChangeInventorySourceRef,
) -> tuple[int, int, str, str]:
    confidence_rank = {
        "direct": 0,
        "inferred": 1,
        "unknown": 2,
    }
    return (
        confidence_rank[source_ref.confidence],
        source_ref.event_sequence or 0,
        source_ref.kind,
        source_ref.identifier,
    )


def _path_provenance_confidence(
    source_refs: Sequence[ChangeInventorySourceRef],
) -> ChangeInventoryProvenanceConfidence:
    if any(source_ref.confidence == "direct" for source_ref in source_refs):
        return "direct"
    if any(source_ref.confidence == "inferred" for source_ref in source_refs):
        return "inferred"
    return "unknown"


def _provenance_note(
    path: str,
    confidence: ChangeInventoryProvenanceConfidence,
    *,
    provenance_index_available: bool,
) -> str:
    if confidence == "direct":
        return "matched to retained Glassbox evidence that directly names this path"
    if confidence == "inferred":
        return (
            "matched to retained Glassbox evidence that mentions or targets this path"
        )
    if not provenance_index_available:
        return "file provenance was not derived because no event evidence was provided"
    if path == "<redacted-path>":
        return "file provenance is unknown because the path was redacted"
    return (
        "no retained Glassbox event names this path; treat it as manual or "
        "externally modified until inspected"
    )


def _risk_for_diff_file(
    file_summary: DiffFileSummary,
    *,
    path: str,
    provenance_confidence: ChangeInventoryProvenanceConfidence,
) -> _PathRisk:
    tags: list[str] = []
    reasons: list[str] = []
    levels: list[ChangeInventoryRiskLevel] = []

    if path == "<redacted-path>":
        tags.append("redacted_path")
        reasons.append("path was redacted, so review sensitivity is unknown")
        levels.append("high")
    if file_summary.policy_sensitive:
        tags.append("policy_sensitive")
        reasons.append("policy-sensitive path changed")
        levels.append("high")
    if file_summary.binary:
        tags.append("binary")
        reasons.append("binary path changed and cannot be summarized by text diff")
        levels.append("high")
    if _change_size(file_summary) >= 500:
        tags.append("large_change")
        reasons.append("large insertion/deletion count needs focused review")
        levels.append("high")
    if _is_provider_or_security_path(path):
        tags.append("provider_security")
        reasons.append(
            "provider, credential, security, or policy-adjacent path changed"
        )
        levels.append("high")
    if _is_runtime_or_schema_path(path):
        tags.append("runtime_schema")
        reasons.append("runtime, store, schema, or projection path changed")
        levels.append("high")
    if _is_packaging_or_release_path(path):
        tags.append("packaging_release")
        reasons.append("packaging, dependency, script, or release path changed")
        levels.append("high")
    if file_summary.generated:
        tags.append("generated")
        reasons.append("generated path changed; source regeneration should be reviewed")
        levels.append("medium")
    if provenance_confidence == "unknown":
        tags.append("missing_provenance")
        reasons.append("no retained Glassbox provenance names this changed path")
        levels.append("medium")
    if file_summary.test_file:
        tags.append("test")
    if file_summary.docs_file:
        tags.append("docs")
    if not levels:
        levels.append("low")
        if file_summary.docs_file:
            reasons.append("docs-only path changed")
        elif file_summary.test_file:
            reasons.append("test path changed")
        else:
            reasons.append("no high-risk path pattern matched")

    return _PathRisk(
        level=_max_risk(levels),
        tags=sorted(dict.fromkeys(tags)),
        reasons=list(dict.fromkeys(reasons)),
    )


def _aggregate_risk_level(
    entries: Sequence[ChangeInventoryPathEntry],
) -> ChangeInventoryRiskLevel:
    if not entries:
        return "unknown"
    return _max_risk([entry.risk_level for entry in entries])


def _risk_summary(
    entries: Sequence[ChangeInventoryPathEntry],
    risk_level: ChangeInventoryRiskLevel,
) -> str | None:
    if not entries:
        return "no changed paths were included in the inventory"
    top_tags: list[str] = []
    for entry in entries:
        if entry.risk_level == risk_level:
            top_tags.extend(entry.risk_tags[:3])
    tags = ", ".join(sorted(dict.fromkeys(top_tags))[:5])
    if risk_level == "high":
        return f"high review risk from {tags or 'path classifications'}"
    if risk_level == "medium":
        return f"medium review risk from {tags or 'path classifications'}"
    if risk_level == "low":
        return "low review risk from changed-path classifications"
    return "risk is unknown because no path classification was available"


def _max_risk(
    levels: Sequence[ChangeInventoryRiskLevel],
) -> ChangeInventoryRiskLevel:
    rank: dict[ChangeInventoryRiskLevel, int] = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "unknown": -1,
    }
    return max(levels, key=lambda level: rank[level], default="unknown")


def _change_size(file_summary: DiffFileSummary) -> int:
    return (file_summary.insertions or 0) + (file_summary.deletions or 0)


def _is_runtime_or_schema_path(path: str) -> bool:
    normalized = path.lower()
    return (
        normalized.startswith("src/glassbox/runtime/")
        or normalized.startswith("src/glassbox/store/")
        or "sqlite_schema" in normalized
        or "sqlite_projection" in normalized
        or normalized.endswith("database.md")
    )


def _is_provider_or_security_path(path: str) -> bool:
    normalized = path.lower()
    sensitive_fragments = (
        "provider",
        "policy",
        "security",
        "secret",
        "credential",
        "auth",
        ".env",
    )
    return any(fragment in normalized for fragment in sensitive_fragments)


def _is_packaging_or_release_path(path: str) -> bool:
    normalized = path.lower()
    return (
        normalized in {"pyproject.toml", "uv.lock", "package.json", "pnpm-lock.yaml"}
        or normalized.startswith("scripts/")
        or normalized.startswith("frontend/package")
        or normalized.startswith("frontend/pnpm-lock")
        or "release" in normalized
    )


def _stage_state_for_change_kind(change_kind: str) -> ChangeInventoryStageState:
    if change_kind == "untracked":
        return "untracked"
    return "unknown"


def _refs_from_tool_call_request(
    event: EventEnvelope,
    payload: ModelToolCallRequested,
) -> dict[str, list[ChangeInventorySourceRef]]:
    try:
        arguments = json.loads(payload.arguments_json)
    except TypeError, json.JSONDecodeError:
        arguments = payload.arguments_json
    candidate_paths = _extract_review_paths(arguments)
    if not candidate_paths:
        return {}
    tool_name = str(payload.tool_name)
    confidence: ChangeInventoryProvenanceConfidence = (
        "direct" if _tool_directly_mutates_files(tool_name) else "inferred"
    )
    return _refs_from_explicit_paths(
        event,
        candidate_paths,
        kind="tool_call",
        identifier=_identifier(event.tool_call_id, fallback=event.event_id),
        confidence=confidence,
        summary=f"{tool_name} call referenced this path",
    )


def _refs_from_artifact_event(
    event: EventEnvelope,
    payload: ToolArtifactRecorded | ReplayArtifactRecorded,
) -> dict[str, list[ChangeInventorySourceRef]]:
    if payload.path is None:
        return {}
    return _refs_from_explicit_paths(
        event,
        [payload.path],
        kind="artifact",
        identifier=_identifier(event.artifact_id, fallback=event.event_id),
        confidence="inferred",
        summary="artifact evidence path matched this changed path",
    )


def _refs_from_text_event(
    event: EventEnvelope,
    *,
    paths: Sequence[str],
    kind: str,
    identifier: str,
    confidence: ChangeInventoryProvenanceConfidence,
    summary: str,
) -> dict[str, list[ChangeInventorySourceRef]]:
    text = event.payload.model_dump_json()
    refs: dict[str, list[ChangeInventorySourceRef]] = {}
    for path in paths:
        if path != "<redacted-path>" and path in text:
            refs.setdefault(path, []).append(
                _source_ref(
                    event,
                    kind=kind,
                    identifier=identifier,
                    confidence=confidence,
                    summary=summary,
                )
            )
    return refs


def _refs_from_explicit_paths(
    event: EventEnvelope,
    paths: Sequence[object],
    *,
    kind: str,
    identifier: str,
    confidence: ChangeInventoryProvenanceConfidence,
    summary: str,
) -> dict[str, list[ChangeInventorySourceRef]]:
    refs: dict[str, list[ChangeInventorySourceRef]] = {}
    for raw_path in paths:
        path = _redacted_relative_path(_path_to_string(raw_path))
        if path == "<redacted-path>":
            continue
        refs.setdefault(path, []).append(
            _source_ref(
                event,
                kind=kind,
                identifier=identifier,
                confidence=confidence,
                summary=summary,
            )
        )
    return refs


def _source_ref(
    event: EventEnvelope,
    *,
    kind: str,
    identifier: str,
    confidence: ChangeInventoryProvenanceConfidence,
    summary: str,
) -> ChangeInventorySourceRef:
    return ChangeInventorySourceRef(
        kind=kind,
        identifier=identifier,
        confidence=confidence,
        event_sequence=event.sequence,
        event_type=event.payload.event_type,
        summary=summary,
    )


def _normalized_candidate_paths(paths: Sequence[str]) -> list[str]:
    return [
        path
        for path in (_redacted_relative_path(candidate) for candidate in paths)
        if path != "<redacted-path>"
    ]


def _identifier(value: object | None, *, fallback: object | None = None) -> str:
    resolved = value if value is not None else fallback
    return str(resolved) if resolved is not None else "unknown"


def _path_to_string(path: object) -> str:
    if isinstance(path, Path):
        return path.as_posix()
    return str(path)


def _extract_review_paths(value: object) -> list[str]:
    paths: list[str] = []
    for text in _extract_strings(value):
        normalized = _redacted_relative_path(text)
        if _looks_like_review_path(normalized):
            paths.append(normalized)
    return sorted(dict.fromkeys(paths))


def _extract_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value, *_split_path_tokens(value)]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_extract_strings(item))
        return strings
    if isinstance(value, list | tuple | set):
        strings = []
        for item in value:
            strings.extend(_extract_strings(item))
        return strings
    return []


def _split_path_tokens(value: str) -> list[str]:
    separators = "\n\t ,;:'\"`()[]{}"
    translation = str.maketrans({separator: " " for separator in separators})
    return [
        token.strip() for token in value.translate(translation).split() if token.strip()
    ]


def _looks_like_review_path(path: str) -> bool:
    if path in {"<redacted-path>", "<unknown-path>"}:
        return False
    if "/" in path:
        return True
    return "." in path and not path.startswith(".")


def _tool_directly_mutates_files(tool_name: str) -> bool:
    normalized = tool_name.lower().replace("-", "_")
    return normalized in {
        "apply_patch",
        "patch",
        "write_file",
        "edit_file",
        "replace_file",
    }


__all__ = [
    "CHANGE_INVENTORY_ARTIFACT_KIND",
    "CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION",
    "CHANGE_INVENTORY_REDACTION",
    "ChangeInventoryArtifact",
    "ChangeInventoryLimits",
    "ChangeInventoryPathEntry",
    "ChangeInventorySourceRef",
    "ChangeInventorySummary",
    "change_inventory_artifact_json",
    "change_inventory_entry_from_diff_file",
    "change_inventory_from_diff_summary",
    "change_inventory_provenance_from_events",
]
