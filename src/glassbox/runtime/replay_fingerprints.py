"""Semantic replay fingerprinting for enriched runtime context."""

import hashlib
import json
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.context_builder import TurnContext


class ReplayEnrichedContextSourceManifest(BaseModel):
    """Semantic replay metadata for one enriched-context source."""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    schema_version: int = Field(default=1, ge=1)
    provenance_class: Literal[
        "recomputed_summary",
        "persisted_session_state",
        "artifact_backed_summary",
    ]
    fingerprint: str
    inherited: bool = False
    item_count: int | None = Field(default=None, ge=0)
    additional_item_count: int | None = Field(default=None, ge=0)
    summary: str | None = None


def fingerprint_replay_payload(payload: dict[str, Any]) -> str:
    """Return a deterministic replay fingerprint for one JSON-compatible payload."""

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_replay_enriched_context_fingerprint(turn_context: TurnContext) -> str:
    """Fingerprint the enriched-context slice of one turn context."""

    return fingerprint_replay_enriched_context_payload(
        turn_context.model_dump(mode="json")
    )


def build_replay_enriched_context_sources(
    turn_context_payload: dict[str, Any],
) -> list[ReplayEnrichedContextSourceManifest]:
    """Return typed per-source semantic fingerprints for enriched context."""

    manifests: list[ReplayEnrichedContextSourceManifest] = []

    repo_context = turn_context_payload.get("repo_context")
    if isinstance(repo_context, str) and repo_context.strip() != "":
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="repository_context",
                provenance_class="recomputed_summary",
                fingerprint=fingerprint_replay_payload(
                    {"repo_context": _normalize_repo_context(repo_context)}
                ),
                summary=_repo_context_summary(repo_context),
            )
        )

    memory_notes = [
        str(note).strip()
        for note in list(turn_context_payload.get("memory_notes") or [])
        if str(note).strip() != ""
        and not str(note).strip().casefold().startswith("[workspace-memory ")
    ]
    if memory_notes:
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="runtime_notes",
                provenance_class="persisted_session_state",
                fingerprint=fingerprint_replay_payload(
                    {
                        "memory_notes": sorted(memory_notes, key=str.casefold),
                        "inherited_count": sum(
                            1
                            for note in memory_notes
                            if note.casefold().startswith("[inherited ")
                        ),
                    }
                ),
                inherited=any(
                    note.casefold().startswith("[inherited ") for note in memory_notes
                ),
                item_count=len(memory_notes),
                summary=(
                    f"{len(memory_notes)} runtime note(s)"
                    if len(memory_notes) != 1
                    else "1 runtime note"
                ),
            )
        )

    workspace_memory_payload = turn_context_payload.get("workspace_memory")
    workspace_memory_items = []
    if isinstance(workspace_memory_payload, list):
        workspace_memory_items = [
            item for item in workspace_memory_payload if isinstance(item, dict)
        ]
    if workspace_memory_items:
        normalized_memory = sorted(
            [
                _normalize_workspace_memory_payload(item)
                for item in workspace_memory_items
            ],
            key=lambda item: (item["kind"], item["summary"], item["memory_id"]),
        )
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="workspace_memory",
                provenance_class="persisted_session_state",
                fingerprint=fingerprint_replay_payload({"items": normalized_memory}),
                item_count=len(normalized_memory),
                summary=(
                    f"{len(normalized_memory)} workspace memory item(s)"
                    if len(normalized_memory) != 1
                    else "1 workspace memory item"
                ),
            )
        )

    repository_index_payload = turn_context_payload.get("repository_index")
    if isinstance(repository_index_payload, dict):
        normalized_index = _normalize_repository_index_payload(repository_index_payload)
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="repository_index",
                provenance_class="recomputed_summary",
                fingerprint=fingerprint_replay_payload(normalized_index),
                item_count=len(normalized_index["items"]),
                additional_item_count=normalized_index["additional_item_count"],
                summary=(
                    f"repository index {normalized_index['status']} with "
                    f"{len(normalized_index['items'])} item(s)"
                ),
            )
        )

    working_set_payload = turn_context_payload.get("working_set")
    working_set_items = []
    additional_item_count = 0
    if isinstance(working_set_payload, dict):
        working_set_items = list(working_set_payload.get("items") or [])
        additional_item_count = int(
            working_set_payload.get("additional_item_count") or 0
        )
    if working_set_items:
        normalized_items = sorted(
            [
                _normalize_working_set_item_payload(item)
                for item in working_set_items
                if isinstance(item, dict)
            ],
            key=lambda item: (
                item["subject_kind"],
                item["subject"],
                item["summary"],
                item["inherited"],
            ),
        )
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="working_set",
                provenance_class="recomputed_summary",
                fingerprint=fingerprint_replay_payload({"items": normalized_items}),
                inherited=any(
                    item.get("inherited") is True for item in normalized_items
                ),
                item_count=len(normalized_items),
                additional_item_count=additional_item_count,
                summary=(
                    f"{len(normalized_items)} working-set item(s)"
                    if len(normalized_items) != 1
                    else "1 working-set item"
                ),
            )
        )

    artifact_context_payload = turn_context_payload.get("artifact_context")
    artifact_context_summaries = []
    artifact_context_additional_count = 0
    if isinstance(artifact_context_payload, dict):
        artifact_context_summaries = list(
            artifact_context_payload.get("summaries") or []
        )
        artifact_context_additional_count = int(
            artifact_context_payload.get("additional_summary_count") or 0
        )
    if artifact_context_summaries:
        normalized_summaries = sorted(
            [
                _normalize_artifact_context_summary_payload(summary)
                for summary in artifact_context_summaries
                if isinstance(summary, dict)
            ],
            key=lambda summary: (
                summary["summary_kind"],
                summary["summary"],
                summary["failure_count"],
                summary["error_count"],
            ),
        )
        summary_kinds = {summary["summary_kind"] for summary in normalized_summaries}
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name=(
                    next(iter(summary_kinds))
                    if len(summary_kinds) == 1
                    else "artifact_context"
                ),
                provenance_class="artifact_backed_summary",
                fingerprint=fingerprint_replay_payload(
                    {"summaries": normalized_summaries}
                ),
                inherited=any(
                    summary.get("inherited") is True for summary in normalized_summaries
                ),
                item_count=len(normalized_summaries),
                additional_item_count=artifact_context_additional_count,
                summary=(
                    f"{len(normalized_summaries)} artifact-backed summary item(s)"
                    if len(normalized_summaries) != 1
                    else "1 artifact-backed summary item"
                ),
            )
        )

    return manifests


def fingerprint_replay_enriched_context_payload(
    turn_context_payload: dict[str, Any],
) -> str:
    """Fingerprint the enriched-context fields of a turn-context payload."""

    return fingerprint_replay_payload(
        {
            "repo_context": turn_context_payload.get("repo_context"),
            "memory_notes": list(turn_context_payload.get("memory_notes") or []),
            "working_set": turn_context_payload.get("working_set"),
            "artifact_context": turn_context_payload.get("artifact_context"),
            "workspace_memory": turn_context_payload.get("workspace_memory"),
            "repository_index": turn_context_payload.get("repository_index"),
        }
    )


def fingerprint_replay_enriched_context_sources(
    sources: list[ReplayEnrichedContextSourceManifest],
) -> str:
    """Fingerprint per-source enriched-context manifests with stable ordering."""

    return fingerprint_replay_payload(
        {
            "sources": [
                {
                    "source_name": source.source_name,
                    "schema_version": source.schema_version,
                    "provenance_class": source.provenance_class,
                    "fingerprint": source.fingerprint,
                    "inherited": source.inherited,
                    "item_count": source.item_count,
                    "additional_item_count": source.additional_item_count,
                }
                for source in sorted(sources, key=lambda source: source.source_name)
            ]
        }
    )


def _normalize_repo_context(repo_context: str) -> str:
    high_signal_paths: list[str] = []
    project_markers: list[str] = []
    for raw_line in repo_context.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        if line.startswith("High-signal paths: "):
            high_signal_paths = _parse_repo_context_csv(
                line.removeprefix("High-signal paths: ")
            )
            continue
        if line.startswith("Project markers: "):
            project_markers = _parse_repo_context_csv(
                line.removeprefix("Project markers: ")
            )
    return json.dumps(
        {
            "high_signal_paths": high_signal_paths,
            "project_markers": project_markers,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _repo_context_summary(repo_context: str) -> str:
    first_line = next(
        (line.strip() for line in repo_context.splitlines() if line.strip() != ""),
        "repository context",
    )
    return first_line


def _parse_repo_context_csv(value: str) -> list[str]:
    return sorted(
        {item.strip() for item in value.split(",") if item.strip() != ""},
        key=str.casefold,
    )


def _normalize_working_set_item_payload(item: dict[str, Any]) -> dict[str, Any]:
    subject_kind = str(item.get("subject_kind") or "").strip()
    normalized_subject = str(item.get("subject") or "").strip()
    normalized_reasons = sorted(
        {
            _normalize_working_set_reason(subject_kind, reason)
            for reason in list(item.get("reasons") or [])
            if isinstance(reason, str) and reason.strip() != ""
        },
        key=str.casefold,
    )
    if subject_kind == "artifact":
        normalized_subject = _normalize_working_set_artifact_subject(
            normalized_subject,
            normalized_reasons,
        )
    normalized_signal_types = sorted(
        {
            signal_type.strip()
            for signal_type in list(item.get("signal_types") or [])
            if isinstance(signal_type, str) and signal_type.strip() != ""
        },
        key=str.casefold,
    )
    return {
        "subject_kind": subject_kind,
        "subject": normalized_subject,
        "summary": str(item.get("summary") or "").strip(),
        "reasons": normalized_reasons,
        "signal_types": normalized_signal_types,
        "inherited": bool(item.get("inherited")),
    }


def _normalize_workspace_memory_payload(item: dict[str, Any]) -> dict[str, Any]:
    raw_provenance = item.get("provenance")
    provenance: dict[str, Any] = (
        raw_provenance if isinstance(raw_provenance, dict) else {}
    )
    return {
        "memory_id": str(item.get("memory_id") or ""),
        "kind": str(item.get("kind") or ""),
        "summary": str(item.get("summary") or "").strip(),
        "content": str(item.get("content") or "").strip(),
        "redacted": bool(item.get("redacted")),
        "provenance": {
            "source_type": str(provenance.get("source_type") or ""),
            "session_id": str(provenance.get("session_id") or "") or None,
            "source_sequence": provenance.get("source_sequence"),
            "task_id": str(provenance.get("task_id") or "") or None,
            "artifact_id": str(provenance.get("artifact_id") or "") or None,
            "tool_call_id": str(provenance.get("tool_call_id") or "") or None,
        },
    }


def _normalize_repository_index_payload(payload: dict[str, Any]) -> dict[str, Any]:
    items = [
        item for item in list(payload.get("items") or []) if isinstance(item, dict)
    ]
    return {
        "status": str(payload.get("status") or ""),
        "schema_version": payload.get("schema_version"),
        "builder_version": payload.get("builder_version"),
        "source_digest": payload.get("source_digest"),
        "entry_count": int(payload.get("entry_count") or 0),
        "additional_item_count": int(payload.get("additional_item_count") or 0),
        "items": sorted(
            [_normalize_repository_index_item_payload(item) for item in items],
            key=lambda item: (
                item["kind"],
                item["path"] or "",
                item["name"],
                item["entry_id"],
            ),
        ),
    }


def _normalize_repository_index_item_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(item.get("entry_id") or ""),
        "kind": str(item.get("kind") or ""),
        "name": str(item.get("name") or ""),
        "summary": str(item.get("summary") or "").strip(),
        "path": str(item.get("path") or "") or None,
        "symbol": str(item.get("symbol") or "") or None,
        "source_type": str(item.get("source_type") or "") or None,
        "line_start": item.get("line_start"),
        "line_end": item.get("line_end"),
        "tags": sorted(
            {
                tag.strip()
                for tag in list(item.get("tags") or [])
                if isinstance(tag, str) and tag.strip() != ""
            },
            key=str.casefold,
        ),
    }


def _normalize_working_set_reason(subject_kind: str, reason: str) -> str:
    normalized_reason = reason.strip()
    if subject_kind == "artifact":
        marker = " artifact recorded at "
        prefix, separator, _ = normalized_reason.partition(marker)
        if separator:
            return f"{prefix}{marker}<artifact-path>"
    return normalized_reason


def _normalize_working_set_artifact_subject(
    subject: str,
    normalized_reasons: list[str],
) -> str:
    for reason in normalized_reasons:
        prefix, separator, _ = reason.partition(" artifact recorded at ")
        if separator:
            return prefix.strip()
    return "<artifact-path>" if subject != "" else subject


def _normalize_artifact_context_summary_payload(
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "summary_kind": str(summary.get("summary_kind") or "").strip(),
        "summary": str(summary.get("summary") or "").strip(),
        "source_tool_name": str(summary.get("source_tool_name") or "").strip(),
        "target_paths": sorted(
            {
                path.strip()
                for path in list(summary.get("target_paths") or [])
                if isinstance(path, str) and path.strip() != ""
            },
            key=str.casefold,
        ),
        "keyword_filter": (
            str(summary.get("keyword_filter")).strip()
            if summary.get("keyword_filter") not in (None, "")
            else None
        ),
        "failing_tests": sorted(
            {
                failing_test.strip()
                for failing_test in list(summary.get("failing_tests") or [])
                if isinstance(failing_test, str) and failing_test.strip() != ""
            },
            key=str.casefold,
        ),
        "failure_count": int(summary.get("failure_count") or 0),
        "error_count": int(summary.get("error_count") or 0),
        "timed_out": bool(summary.get("timed_out")),
        "inherited": bool(summary.get("inherited")),
    }
