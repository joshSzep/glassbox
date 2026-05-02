"""Change inventory artifact contract for reviewable changesets."""

import json
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

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
    summary: str | None = Field(default=None, max_length=500)


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
) -> ChangeInventoryArtifact:
    """Build a bounded change inventory artifact from workspace diff evidence."""

    resolved_limits = limits or ChangeInventoryLimits()
    source_files = _source_files(diff_summary)
    entries = [
        change_inventory_entry_from_diff_file(file_summary)
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
) -> ChangeInventoryPathEntry:
    """Convert a diff file summary into the stable inventory path shape."""

    path = _redacted_relative_path(file_summary.path)
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
        provenance_note="file provenance is not attached until GBX-1221",
    )


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
    )


def _limitations(
    diff_summary: DiffSummaryResult,
    source_files: Sequence[DiffFileSummary],
    entries: Sequence[ChangeInventoryPathEntry],
) -> list[str]:
    limitations = [
        "inventory is summary-only and does not include raw diffs or file contents",
        "file provenance is unknown until provenance derivation is attached",
    ]
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


def _stage_state_for_change_kind(change_kind: str) -> ChangeInventoryStageState:
    if change_kind == "untracked":
        return "untracked"
    return "unknown"


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
]
