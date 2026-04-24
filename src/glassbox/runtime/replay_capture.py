"""Helpers for recording replay manifests during live turn execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextContent,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from glassbox.core.events import EventEnvelope, ReplayArtifactRecorded
from glassbox.core.ids import SessionId, ToolCallId, TurnId
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.context_builder import TurnContext
from glassbox.services import ArtifactRepository, SessionRepository
from glassbox.tools import PreparedToolExecution, ToolExecutionResult

REPLAY_MODEL_CALL_ARTIFACT = "replay_model_call"
REPLAY_TOOL_REQUEST_ARTIFACT = "replay_tool_request"
REPLAY_TOOL_RESULT_ARTIFACT = "replay_tool_result"
REPLAY_TURN_OUTPUT_ARTIFACT = "replay_turn_output"

_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "auth",
)


class ReplayMessagePartSnapshot(BaseModel):
    """Normalized representation of one provider-facing message part."""

    model_config = ConfigDict(extra="forbid")

    part_kind: str
    content: Any = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    arguments: Any = None


class ReplayMessageSnapshot(BaseModel):
    """Normalized representation of one provider-facing message."""

    model_config = ConfigDict(extra="forbid")

    message_kind: Literal["request", "response"]
    parts: list[ReplayMessagePartSnapshot]


class ReplayRuntimeConfigSnapshot(BaseModel):
    """Non-secret summary of runtime config relevant to replay."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    model_settings: dict[str, Any] = Field(default_factory=dict)
    allow_text_output: bool
    allow_image_output: bool
    tool_names: list[str] = Field(default_factory=list)
    fingerprint: str


class ReplayPreparedTurnSnapshot(BaseModel):
    """Normalized prepared model input for one model call."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    user_prompt: str | None = None
    message_history: list[ReplayMessageSnapshot]
    request_parameters: dict[str, Any] = Field(default_factory=dict)
    model_settings: dict[str, Any] = Field(default_factory=dict)


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


class ReplayModelCallManifest(BaseModel):
    """Replay baseline for one model call inside a turn."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_model_call"] = REPLAY_MODEL_CALL_ARTIFACT
    call_index: int = Field(ge=1)
    turn_context: dict[str, Any]
    enriched_context_fingerprint: str | None = None
    enriched_context_sources: list[ReplayEnrichedContextSourceManifest] = Field(
        default_factory=list
    )
    runtime_config: ReplayRuntimeConfigSnapshot
    prepared_turn: ReplayPreparedTurnSnapshot


class ReplayToolRequestManifest(BaseModel):
    """Replay baseline for one validated tool request."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_tool_request"] = REPLAY_TOOL_REQUEST_ARTIFACT
    tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    validated_arguments: dict[str, Any]
    policy_decision: dict[str, Any]


class ReplayToolResultManifest(BaseModel):
    """Replay baseline for one tool execution result."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_tool_result"] = REPLAY_TOOL_RESULT_ARTIFACT
    tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    success: bool
    output_payload: dict[str, Any] | None = None
    summary: str
    error_message: str | None = None


class ReplayTurnOutputManifest(BaseModel):
    """Replay baseline for the observable outcome of one turn."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = 1
    artifact_kind: Literal["replay_turn_output"] = REPLAY_TURN_OUTPUT_ARTIFACT
    outcome: Literal[
        "completed",
        "awaiting_approval",
        "awaiting_user_input",
        "failed",
    ]
    assistant_text: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


type ReplayManifest = (
    ReplayModelCallManifest
    | ReplayToolRequestManifest
    | ReplayToolResultManifest
    | ReplayTurnOutputManifest
)


def build_replay_runtime_config_snapshot(
    prepared_turn: PreparedModelTurn,
    *,
    tool_names: Sequence[str],
) -> ReplayRuntimeConfigSnapshot:
    redacted_model_settings = _redact_json(prepared_turn.model_settings)
    runtime_config = {
        "model_name": prepared_turn.model_name,
        "model_settings": redacted_model_settings,
        "allow_text_output": prepared_turn.request_parameters.allow_text_output,
        "allow_image_output": prepared_turn.request_parameters.allow_image_output,
        "tool_names": list(tool_names),
    }
    runtime_config["fingerprint"] = _fingerprint_payload(runtime_config)
    return ReplayRuntimeConfigSnapshot.model_validate(runtime_config)


def build_replay_prepared_turn_snapshot(
    prepared_turn: PreparedModelTurn,
    *,
    tool_names: Sequence[str],
    normalize_system_prompt: bool = True,
) -> ReplayPreparedTurnSnapshot:
    return ReplayPreparedTurnSnapshot(
        model_name=prepared_turn.model_name,
        user_prompt=prepared_turn.user_prompt,
        message_history=[
            _snapshot_model_message(
                message,
                normalize_system_prompt=normalize_system_prompt,
            )
            for message in prepared_turn.message_history
        ],
        request_parameters={
            "allow_text_output": prepared_turn.request_parameters.allow_text_output,
            "allow_image_output": prepared_turn.request_parameters.allow_image_output,
            "tool_names": list(tool_names),
        },
        model_settings=_redact_json(prepared_turn.model_settings),
    )


def build_replay_model_call_manifest(
    *,
    call_index: int,
    turn_context: TurnContext,
    prepared_turn: PreparedModelTurn,
) -> ReplayModelCallManifest:
    turn_context_payload = _redact_json(turn_context.model_dump(mode="json"))
    return ReplayModelCallManifest(
        call_index=call_index,
        turn_context=turn_context_payload,
        enriched_context_fingerprint=build_replay_enriched_context_fingerprint(
            turn_context
        ),
        enriched_context_sources=build_replay_enriched_context_sources(
            turn_context_payload
        ),
        runtime_config=build_replay_runtime_config_snapshot(
            prepared_turn,
            tool_names=[tool.name for tool in turn_context.available_tools],
        ),
        prepared_turn=build_replay_prepared_turn_snapshot(
            prepared_turn,
            tool_names=[tool.name for tool in turn_context.available_tools],
        ),
    )


def build_replay_tool_request_manifest(
    prepared_tool_call: PreparedToolExecution,
) -> ReplayToolRequestManifest:
    return ReplayToolRequestManifest(
        tool_call_id=prepared_tool_call.event_tool_call_id,
        provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
        tool_name=prepared_tool_call.tool_name,
        validated_arguments=_redact_json(
            prepared_tool_call.validated_arguments.model_dump(mode="json")
        ),
        policy_decision=_redact_json(
            prepared_tool_call.policy_decision.model_dump(mode="json")
        ),
    )


def build_replay_tool_result_manifest(
    *,
    tool_call_id: ToolCallId,
    provider_tool_call_id: str,
    tool_name: str,
    success: bool,
    summary: str,
    output_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> ReplayToolResultManifest:
    return ReplayToolResultManifest(
        tool_call_id=tool_call_id,
        provider_tool_call_id=provider_tool_call_id,
        tool_name=tool_name,
        success=success,
        output_payload=(
            _redact_json(output_payload) if output_payload is not None else None
        ),
        summary=summary,
        error_message=error_message,
    )


def build_replay_turn_output_manifest(
    *,
    outcome: Literal[
        "completed",
        "awaiting_approval",
        "awaiting_user_input",
        "failed",
    ],
    assistant_text: str | None = None,
    details: dict[str, Any] | None = None,
) -> ReplayTurnOutputManifest:
    return ReplayTurnOutputManifest(
        outcome=outcome,
        assistant_text=assistant_text,
        details=_redact_json(details or {}),
    )


def load_replay_manifest(raw_text: str) -> ReplayManifest:
    manifest_data = json.loads(raw_text)
    if not isinstance(manifest_data, dict):
        raise ValueError("replay artifact must decode to a JSON object")

    artifact_kind = manifest_data.get("artifact_kind")
    if artifact_kind == REPLAY_MODEL_CALL_ARTIFACT:
        return ReplayModelCallManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TOOL_REQUEST_ARTIFACT:
        return ReplayToolRequestManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TOOL_RESULT_ARTIFACT:
        return ReplayToolResultManifest.model_validate(manifest_data)
    if artifact_kind == REPLAY_TURN_OUTPUT_ARTIFACT:
        return ReplayTurnOutputManifest.model_validate(manifest_data)
    raise ValueError(f"unsupported replay artifact kind: {artifact_kind!r}")


class ReplayArtifactRecorder:
    """Persist replay manifests as artifact files linked from session events."""

    def __init__(
        self,
        session_repository: SessionRepository,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def record_model_call(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        call_index: int,
        turn_context: TurnContext,
        prepared_turn: PreparedModelTurn,
    ) -> EventEnvelope:
        manifest = build_replay_model_call_manifest(
            call_index=call_index,
            turn_context=turn_context,
            prepared_turn=prepared_turn,
        )
        return self._record_manifest(session_id, turn_id, manifest)

    def record_tool_request(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        prepared_tool_call: PreparedToolExecution,
    ) -> EventEnvelope:
        manifest = build_replay_tool_request_manifest(prepared_tool_call)
        return self._record_manifest(
            session_id,
            turn_id,
            manifest,
            tool_call_id=prepared_tool_call.event_tool_call_id,
        )

    def record_tool_result(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        tool_call_id: ToolCallId,
        provider_tool_call_id: str,
        tool_name: str,
        success: bool,
        summary: str,
        output_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> EventEnvelope:
        manifest = build_replay_tool_result_manifest(
            tool_call_id=tool_call_id,
            provider_tool_call_id=provider_tool_call_id,
            tool_name=tool_name,
            success=success,
            summary=summary,
            output_payload=output_payload,
            error_message=error_message,
        )
        return self._record_manifest(
            session_id,
            turn_id,
            manifest,
            tool_call_id=tool_call_id,
        )

    def record_tool_execution_result(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        execution_result: ToolExecutionResult,
    ) -> EventEnvelope:
        return self.record_tool_result(
            session_id,
            turn_id,
            tool_call_id=execution_result.event_tool_call_id,
            provider_tool_call_id=execution_result.provider_tool_call_id,
            tool_name=execution_result.tool_name,
            success=True,
            output_payload=execution_result.output_payload,
            summary=execution_result.summary,
        )

    def record_turn_output(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        *,
        outcome: Literal[
            "completed",
            "awaiting_approval",
            "awaiting_user_input",
            "failed",
        ],
        assistant_text: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> EventEnvelope:
        manifest = build_replay_turn_output_manifest(
            outcome=outcome,
            assistant_text=assistant_text,
            details=details,
        )
        return self._record_manifest(session_id, turn_id, manifest)

    def _record_manifest(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        manifest: ReplayManifest,
        *,
        tool_call_id: ToolCallId | None = None,
    ) -> EventEnvelope:
        stored_artifact = self._artifact_repository.write_text_artifact(
            session_id,
            manifest.model_dump_json(indent=2),
            suffix=".json",
        )
        stored_events = self._session_repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReplayArtifactRecorded(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        artifact_id=stored_artifact.artifact_id,
                        artifact_kind=manifest.artifact_kind,
                        path=stored_artifact.relative_path.as_posix(),
                    ),
                )
            ]
        )
        return stored_events[0]


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_replay_enriched_context_fingerprint(turn_context: TurnContext) -> str:
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
                fingerprint=_fingerprint_payload(
                    {"repo_context": _normalize_repo_context(repo_context)}
                ),
                summary=_repo_context_summary(repo_context),
            )
        )

    memory_notes = [
        str(note).strip()
        for note in list(turn_context_payload.get("memory_notes") or [])
        if str(note).strip() != ""
    ]
    if memory_notes:
        manifests.append(
            ReplayEnrichedContextSourceManifest(
                source_name="runtime_notes",
                provenance_class="persisted_session_state",
                fingerprint=_fingerprint_payload(
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
                fingerprint=_fingerprint_payload({"items": normalized_items}),
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
                fingerprint=_fingerprint_payload({"summaries": normalized_summaries}),
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
    return _fingerprint_payload(
        {
            "repo_context": turn_context_payload.get("repo_context"),
            "memory_notes": list(turn_context_payload.get("memory_notes") or []),
            "working_set": turn_context_payload.get("working_set"),
            "artifact_context": turn_context_payload.get("artifact_context"),
        }
    )


def fingerprint_replay_enriched_context_sources(
    sources: Sequence[ReplayEnrichedContextSourceManifest],
) -> str:
    return _fingerprint_payload(
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


def _snapshot_model_message(
    message: ModelMessage,
    *,
    normalize_system_prompt: bool = True,
) -> ReplayMessageSnapshot:
    if isinstance(message, ModelRequest):
        return ReplayMessageSnapshot(
            message_kind="request",
            parts=[
                _snapshot_request_part(
                    part,
                    normalize_system_prompt=normalize_system_prompt,
                )
                for part in message.parts
            ],
        )
    if isinstance(message, ModelResponse):
        return ReplayMessageSnapshot(
            message_kind="response",
            parts=[_snapshot_response_part(part) for part in message.parts],
        )
    raise TypeError(f"unsupported model message type: {type(message)!r}")


def _snapshot_request_part(
    part: Any,
    *,
    normalize_system_prompt: bool = True,
) -> ReplayMessagePartSnapshot:
    if isinstance(part, SystemPromptPart):
        return ReplayMessagePartSnapshot(
            part_kind="system_prompt",
            content=(
                _normalize_system_prompt_content(part.content)
                if normalize_system_prompt
                else part.content
            ),
        )
    if isinstance(part, UserPromptPart):
        return ReplayMessagePartSnapshot(
            part_kind="user_prompt",
            content=_normalize_user_prompt_content(part.content),
        )
    if isinstance(part, ToolReturnPart):
        return ReplayMessagePartSnapshot(
            part_kind="tool_return",
            tool_name=part.tool_name,
            tool_call_id=part.tool_call_id,
            content=_redact_json(_json_compatible(part.content)),
        )
    return ReplayMessagePartSnapshot(
        part_kind=type(part).__name__,
        content=_redact_json(_json_compatible(getattr(part, "content", None))),
    )


def _snapshot_response_part(part: Any) -> ReplayMessagePartSnapshot:
    if isinstance(part, TextPart):
        return ReplayMessagePartSnapshot(part_kind="text", content=part.content)
    if isinstance(part, ToolCallPart):
        return ReplayMessagePartSnapshot(
            part_kind="tool_call",
            tool_name=part.tool_name,
            tool_call_id=part.tool_call_id,
            arguments=_redact_json(_json_compatible(part.args)),
        )
    return ReplayMessagePartSnapshot(
        part_kind=type(part).__name__,
        content=_redact_json(_json_compatible(getattr(part, "content", None))),
    )


def _normalize_user_prompt_content(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(
        content,
        (str, bytes, bytearray),
    ):
        return [_normalize_user_prompt_content(item) for item in content]
    if isinstance(content, TextContent):
        return content.content
    return _redact_json(_json_compatible(content))


def _normalize_system_prompt_content(content: str) -> str:
    sections = [section.strip() for section in content.split("\n\n")]
    filtered_sections = [
        section
        for section in sections
        if section != ""
        and not section.startswith("Repository context:")
        and not section.startswith("Memory notes:")
        and not section.startswith("Working set:")
        and not section.startswith("Artifact-backed context:")
    ]
    return "\n\n".join(filtered_sections)


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


def _json_compatible(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_compatible(item) for item in value]
    return value


def _redact_json(value: Any) -> Any:
    normalized = _json_compatible(value)
    if isinstance(normalized, dict):
        redacted: dict[str, Any] = {}
        for key, item in normalized.items():
            if _looks_sensitive(key):
                redacted[key] = _REDACTED
            else:
                redacted[key] = _redact_json(item)
        return redacted
    if isinstance(normalized, list):
        return [_redact_json(item) for item in normalized]
    return normalized


def _looks_sensitive(key: str) -> bool:
    normalized_key = key.lower().replace("-", "_")
    return any(fragment in normalized_key for fragment in _SENSITIVE_KEY_FRAGMENTS)
