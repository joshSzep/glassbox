"""Offline deterministic replay runner for persisted Glassbox sessions."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart

from glassbox.core.events import (
    ApprovalResolved,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    EventEnvelope,
    ModelCallCompleted,
    ModelCallStarted,
    ModelToolCallRequested,
    ReplayArtifactRecorded,
    RuntimeNoteImported,
    RuntimeNoteRecorded,
    TranscriptMessageImported,
    TurnCompleted,
    TurnFailed,
    UserAnswerProvided,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import SessionId
from glassbox.core.models import (
    InheritedTranscriptMessage,
    ResolvedForkPoint,
    RuntimeNoteRecord,
    SessionConfig,
    SessionRecord,
)
from glassbox.core.types import ApprovalDecision
from glassbox.llm import (
    ModelExecutionResult,
    ModelExecutor,
    ModelProviderConfig,
    ModelTextDelta,
    ModelToolCall,
    PreparedModelTurn,
    PydanticAIModelAdapter,
    PydanticAIStreamTranslator,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.replay_capture import (
    ReplayModelCallManifest,
    ReplayToolRequestManifest,
    ReplayToolResultManifest,
    ReplayTurnOutputManifest,
    build_replay_enriched_context_sources,
    build_replay_prepared_turn_snapshot,
    build_replay_runtime_config_snapshot,
    build_replay_tool_request_manifest,
    fingerprint_replay_enriched_context_payload,
    fingerprint_replay_enriched_context_sources,
    load_replay_manifest,
)
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.services import ArtifactRepository, SessionRepository
from glassbox.store import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
from glassbox.tools import (
    ApprovalMode,
    ToolExecutionResult,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRegistry,
    ToolRuntime,
    build_ask_user_tool_registry,
)

type ReplayOutcome = Literal[
    "exact_match",
    "manifest_drift",
    "behavioral_drift",
    "unsupported_session",
    "replay_failure",
]

REPLAY_BUNDLE_KIND = "glassbox_replay_bundle"
REPLAY_BUNDLE_VERSION = 1


class ReplayAction(BaseModel):
    """One source-session input that should be re-applied during replay."""

    model_config = ConfigDict(extra="forbid")

    action_type: Literal["user_message", "approval", "user_answer", "runtime_note"]
    text: str | None = None
    decision: ApprovalDecision | None = None
    answer: str | None = None
    category: str | None = None
    message: str | None = None


class ReplayRecordedToolCall(BaseModel):
    """Recorded tool call reconstructed for one model response."""

    model_config = ConfigDict(extra="forbid")

    provider_tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ReplayRecordedModelCall(BaseModel):
    """Recorded model call input manifest and output fixture."""

    model_config = ConfigDict(extra="forbid")

    manifest: ReplayModelCallManifest
    assistant_text: str | None = None
    text_deltas: list[str] = Field(default_factory=list)
    tool_calls: list[ReplayRecordedToolCall] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None


class ReplayTranscriptPart(BaseModel):
    """Normalized transcript part used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    text: str


class ReplayTranscriptMessage(BaseModel):
    """Normalized transcript message used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    role: str
    parts: list[ReplayTranscriptPart]


class ReplayToolCallSnapshot(BaseModel):
    """Normalized tool call projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: str
    summary: str | None = None


class ReplayApprovalSnapshot(BaseModel):
    """Normalized approval projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    reason: str
    status: str
    decided_by: str | None = None


class ReplayQuestionSnapshot(BaseModel):
    """Normalized ask_user flow record used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str | None = None


class ReplayLineageSnapshot(BaseModel):
    """Normalized session lineage metadata used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    parent_session_id: str
    forked_from_turn_id: str
    forked_from_sequence: int = Field(ge=0)
    branch_label: str | None = None


class ReplayFinalStateSnapshot(BaseModel):
    """Normalized final session projection used for replay comparison."""

    model_config = ConfigDict(extra="forbid")

    status: str
    has_active_turn: bool = False
    has_pending_approval: bool = False
    has_pending_question: bool = False


class ReplayNormalizedSession(BaseModel):
    """Behavior-focused normalized session snapshot for replay diffs."""

    model_config = ConfigDict(extra="forbid")

    transcript: list[ReplayTranscriptMessage]
    lineage: ReplayLineageSnapshot | None = None
    inherited_transcript: list[ReplayTranscriptMessage] = Field(default_factory=list)
    post_fork_transcript: list[ReplayTranscriptMessage] = Field(default_factory=list)
    tool_calls: list[ReplayToolCallSnapshot]
    approvals: list[ReplayApprovalSnapshot]
    questions: list[ReplayQuestionSnapshot]
    event_families: list[str]
    final_state: ReplayFinalStateSnapshot


class ReplayBundle(BaseModel):
    """Typed replay input bundle loaded from a persisted session."""

    model_config = ConfigDict(extra="forbid")

    bundle_kind: Literal["glassbox_replay_bundle"] = REPLAY_BUNDLE_KIND
    bundle_version: int = REPLAY_BUNDLE_VERSION
    source_session_id: SessionId
    session_config: SessionConfig
    inherited_messages: list[InheritedTranscriptMessage] = Field(default_factory=list)
    inherited_runtime_notes: list[RuntimeNoteRecord] = Field(default_factory=list)
    actions: list[ReplayAction]
    model_calls: list[ReplayRecordedModelCall]
    tool_requests: list[ReplayToolRequestManifest]
    tool_results: list[ReplayToolResultManifest]
    turn_outputs: list[ReplayTurnOutputManifest]
    baseline: ReplayNormalizedSession


class ReplayResult(BaseModel):
    """Outcome and normalized comparison payload for one replay run."""

    model_config = ConfigDict(extra="forbid")

    outcome: ReplayOutcome
    source_session_id: SessionId | None = None
    message: str | None = None
    mismatches: list[str] = Field(default_factory=list)
    baseline: ReplayNormalizedSession | None = None
    replay: ReplayNormalizedSession | None = None


class ReplayRunner:
    """Load and replay persisted sessions through an isolated runtime."""

    def __init__(
        self,
        session_repository: SessionRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def load_session_bundle(self, session_id: SessionId) -> ReplayBundle:
        session_repository, _artifact_repository = self._require_recorded_repositories()

        source_session = session_repository.get_session(session_id)
        if source_session is None:
            raise ValueError(f"unknown session_id: {session_id}")

        source_events = session_repository.read_session_events(session_id)
        replay_payloads = [
            event.payload
            for event in source_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        if not replay_payloads:
            raise _ReplayFailure("session does not contain replay artifacts")

        manifests = [self._load_manifest(payload) for payload in replay_payloads]
        model_calls = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayModelCallManifest)
        ]
        tool_requests = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayToolRequestManifest)
        ]
        tool_results = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayToolResultManifest)
        ]
        turn_outputs = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayTurnOutputManifest)
        ]
        if not model_calls:
            raise _ReplayFailure("session does not contain replay model call manifests")

        return ReplayBundle(
            source_session_id=session_id,
            session_config=_build_replay_bundle_session_config(source_session),
            inherited_messages=_build_inherited_messages(source_events),
            inherited_runtime_notes=_build_inherited_runtime_notes(
                session_id,
                source_session,
                source_events,
                session_repository,
            ),
            actions=_build_replay_actions(source_events),
            model_calls=_build_recorded_model_calls(
                source_events,
                model_calls,
                tool_requests,
            ),
            tool_requests=tool_requests,
            tool_results=tool_results,
            turn_outputs=turn_outputs,
            baseline=_normalize_session(
                session_id,
                session_repository,
                source_events,
            ),
        )

    def export_session_bundle(
        self,
        session_id: SessionId,
        output_path: Path,
    ) -> Path:
        bundle = self.load_session_bundle(session_id)
        resolved_output = output_path.resolve()
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        serialized_bundle = json.dumps(
            bundle.model_dump(mode="json", exclude_none=True),
            indent=2,
            sort_keys=True,
        )
        resolved_output.write_text(f"{serialized_bundle}\n", encoding="utf-8")
        return resolved_output

    def load_bundle_file(self, bundle_path: Path) -> ReplayBundle:
        resolved_path = bundle_path.resolve()
        try:
            raw_bundle = resolved_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise _ReplayFailure(
                f"missing replay bundle file: {resolved_path}"
            ) from exc

        try:
            bundle = ReplayBundle.model_validate_json(raw_bundle)
        except ValueError as exc:
            raise _ReplayFailure(
                f"invalid replay bundle file {resolved_path}: {exc}"
            ) from exc

        if bundle.bundle_version != REPLAY_BUNDLE_VERSION:
            raise _ReplayUnsupportedSession(
                f"unsupported replay bundle version: {bundle.bundle_version}"
            )
        return bundle

    async def replay_session(self, session_id: SessionId) -> ReplayResult:
        try:
            bundle = self.load_session_bundle(session_id)
            return await self.replay_bundle(bundle)
        except _ReplayManifestDrift as exc:
            return ReplayResult(
                outcome="manifest_drift",
                source_session_id=session_id,
                message=str(exc),
            )
        except _ReplayUnsupportedSession as exc:
            return ReplayResult(
                outcome="unsupported_session",
                source_session_id=session_id,
                message=str(exc),
            )
        except _ReplayFailure as exc:
            return ReplayResult(
                outcome="replay_failure",
                source_session_id=session_id,
                message=str(exc),
            )

    async def replay_bundle_file(
        self,
        bundle_path: Path,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        try:
            bundle = self.load_bundle_file(bundle_path)
        except _ReplayUnsupportedSession as exc:
            return ReplayResult(
                outcome="unsupported_session",
                source_session_id=None,
                message=str(exc),
            )
        except _ReplayFailure as exc:
            return ReplayResult(
                outcome="replay_failure",
                source_session_id=None,
                message=str(exc),
            )

        return await self.replay_bundle(bundle, workspace_root=workspace_root)

    async def replay_bundle(
        self,
        bundle: ReplayBundle,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        bundle = _hydrate_lineage_aware_bundle(bundle)
        try:
            replay_session = await self._run_bundle(
                bundle,
                workspace_root=workspace_root,
            )
        except _ReplayManifestDrift as exc:
            return ReplayResult(
                outcome="manifest_drift",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )
        except _ReplayUnsupportedSession as exc:
            return ReplayResult(
                outcome="unsupported_session",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )
        except _ReplayFailure as exc:
            return ReplayResult(
                outcome="replay_failure",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )

        mismatches = _collect_mismatches(bundle.baseline, replay_session)
        return ReplayResult(
            outcome="exact_match" if not mismatches else "behavioral_drift",
            source_session_id=bundle.source_session_id,
            message=None if not mismatches else "normalized replay drift detected",
            mismatches=mismatches,
            baseline=bundle.baseline,
            replay=replay_session,
        )

    def _load_manifest(self, payload: ReplayArtifactRecorded):
        _, artifact_repository = self._require_recorded_repositories()

        if payload.path is None:
            raise _ReplayFailure("replay artifact event is missing its path")

        try:
            raw_manifest = artifact_repository.read_text_artifact(Path(payload.path))
        except FileNotFoundError as exc:
            raise _ReplayFailure(
                f"missing replay artifact for path: {payload.path}"
            ) from exc

        try:
            manifest = load_replay_manifest(raw_manifest)
        except ValueError as exc:
            raise _ReplayFailure(
                f"invalid replay artifact for path {payload.path}: {exc}"
            ) from exc

        if getattr(manifest, "manifest_version", 1) != 1:
            raise _ReplayUnsupportedSession(
                "unsupported replay manifest version: "
                f"{getattr(manifest, 'manifest_version', None)}"
            )
        return manifest

    def _require_recorded_repositories(
        self,
    ) -> tuple[SessionRepository, ArtifactRepository]:
        if self._session_repository is None or self._artifact_repository is None:
            raise ValueError(
                "session and artifact repositories are required for session-based "
                "replay operations"
            )
        return self._session_repository, self._artifact_repository

    async def _run_bundle(
        self,
        bundle: ReplayBundle,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayNormalizedSession:
        if not bundle.model_calls:
            raise _ReplayFailure("replay bundle does not contain model calls")

        replay_session_config = _build_replay_session_config(
            bundle,
            workspace_root=workspace_root,
        )
        model_executor = _ReplayModelExecutor(
            bundle.model_calls,
            ignored_live_source_names=(
                {"repository_context"} if workspace_root is not None else set()
            ),
        )
        tool_runtime = _build_replay_tool_runtime(
            bundle,
            workspace_root=workspace_root,
        )

        with TemporaryDirectory(prefix="glassbox-replay-") as replay_dir:
            replay_root = Path(replay_dir)
            connection = open_database(replay_root / "glassbox.sqlite3")
            try:
                initialize_database(connection)
                repository = SQLiteSessionRepository(connection)
                artifact_repository = FilesystemArtifactRepository(
                    connection,
                    replay_root,
                )
                bus: EventBus[EventEnvelope] = EventBus()
                turn_engine = TurnEngine(
                    repository,
                    bus,
                    TurnContextBuilder(repository),
                    lambda _session: _build_replay_model_adapter(bundle),
                    lambda _session: model_executor,
                    (
                        (lambda _session: tool_runtime)
                        if tool_runtime is not None
                        else None
                    ),
                    artifact_repository=artifact_repository,
                )
                supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
                replay_state = await supervisor.start_session(replay_session_config)
                restored_import_events = _build_replay_import_events(
                    bundle,
                    repository,
                    replay_state.session_id,
                )
                if restored_import_events:
                    for event in repository.append_events(restored_import_events):
                        bus.publish(event)

                restored_runtime_note_events = _build_replay_runtime_note_import_events(
                    bundle,
                    replay_state.session_id,
                )
                if restored_runtime_note_events:
                    for event in repository.append_events(restored_runtime_note_events):
                        bus.publish(event)

                for action in bundle.actions:
                    if action.action_type == "user_message":
                        assert action.text is not None
                        await supervisor.submit_user_message(
                            replay_state.session_id,
                            action.text,
                        )
                        continue

                    if action.action_type == "runtime_note":
                        assert action.category is not None
                        assert action.message is not None
                        await supervisor.record_runtime_note(
                            replay_state.session_id,
                            category=action.category,
                            message=action.message,
                        )
                        continue

                    session_state = repository.get_session_state(
                        replay_state.session_id
                    )
                    if session_state is None:
                        raise _ReplayFailure("replay session state disappeared")

                    if action.action_type == "approval":
                        if session_state.pending_approval_id is None:
                            raise _ReplayFailure(
                                "replay session is not awaiting approval when one was "
                                "recorded"
                            )
                        assert action.decision is not None
                        await supervisor.resolve_approval(
                            replay_state.session_id,
                            session_state.pending_approval_id,
                            action.decision,
                        )
                        continue

                    if session_state.pending_question_id is None:
                        raise _ReplayFailure(
                            "replay session is not awaiting user input when one was "
                            "recorded"
                        )
                    assert action.answer is not None
                    await supervisor.provide_user_answer(
                        replay_state.session_id,
                        session_state.pending_question_id,
                        action.answer,
                    )

                return _normalize_session(
                    replay_state.session_id,
                    repository,
                    repository.read_session_events(replay_state.session_id),
                )
            finally:
                connection.close()


class _ReplayManifestDrift(RuntimeError):
    pass


class _ReplayUnsupportedSession(RuntimeError):
    pass


class _ReplayFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _ToolResultKey:
    provider_tool_call_id: str
    tool_name: str


class _ReplayModelExecutor(ModelExecutor):
    def __init__(
        self,
        model_calls: Sequence[ReplayRecordedModelCall],
        *,
        ignored_live_source_names: set[str] | None = None,
    ) -> None:
        self._model_calls = list(model_calls)
        self._index = 0
        self._ignored_live_source_names = set(ignored_live_source_names or ())

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        return await self.execute_stream(
            prepared_turn,
            stream_translator=PydanticAIStreamTranslator(),
            on_event=lambda _event: None,
        )

    async def execute_stream(
        self,
        prepared_turn: PreparedModelTurn,
        *,
        stream_translator: PydanticAIStreamTranslator,
        on_event,
    ) -> ModelExecutionResult:
        del stream_translator

        if self._index >= len(self._model_calls):
            raise _ReplayFailure("replay requested more model calls than were recorded")

        recorded_call = self._model_calls[self._index]
        self._index += 1

        current_tool_names = _prepared_turn_tool_names(prepared_turn)
        current_runtime_config = build_replay_runtime_config_snapshot(
            prepared_turn,
            tool_names=current_tool_names,
        )
        current_prepared_turn = build_replay_prepared_turn_snapshot(
            prepared_turn,
            tool_names=current_tool_names,
        )
        drift_reasons: list[str] = []
        if current_runtime_config != recorded_call.manifest.runtime_config:
            drift_reasons.append("runtime config no longer matches recorded manifest")
        if current_prepared_turn != recorded_call.manifest.prepared_turn:
            drift_reasons.append("prepared turn no longer matches recorded manifest")
        if recorded_call.manifest.enriched_context_sources:
            current_turn_context_payload = prepared_turn.turn_context_payload
            if current_turn_context_payload is None:
                drift_reasons.append(
                    "live replay turn did not include enriched context payload"
                )
            recorded_turn_context_sources = build_replay_enriched_context_sources(
                recorded_call.manifest.turn_context
            )
            drift_reasons.extend(
                _diff_enriched_context_sources(
                    expected_sources=recorded_call.manifest.enriched_context_sources,
                    actual_sources=recorded_turn_context_sources,
                    prefix="recorded enriched context",
                )
            )
            if current_turn_context_payload is not None:
                current_enriched_context_sources = (
                    build_replay_enriched_context_sources(current_turn_context_payload)
                )
                drift_reasons.extend(
                    _diff_enriched_context_sources(
                        expected_sources=recorded_call.manifest.enriched_context_sources,
                        actual_sources=current_enriched_context_sources,
                        prefix="enriched context",
                        ignored_source_names=self._ignored_live_source_names,
                    )
                )
        elif (
            recorded_call.manifest.enriched_context_fingerprint is not None
            and fingerprint_replay_enriched_context_payload(
                recorded_call.manifest.turn_context
            )
            != recorded_call.manifest.enriched_context_fingerprint
        ):
            drift_reasons.append(
                "enriched context no longer matches recorded replay manifest"
            )
        if drift_reasons:
            raise _ReplayManifestDrift("; ".join(drift_reasons))

        for text_delta in recorded_call.text_deltas:
            on_event(ModelTextDelta(text=text_delta))

        response_parts = []
        tool_calls = tuple(
            ModelToolCall(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                tool_call_id=tool_call.provider_tool_call_id,
            )
            for tool_call in recorded_call.tool_calls
        )
        for tool_call in recorded_call.tool_calls:
            response_parts.append(
                ToolCallPart(
                    tool_name=tool_call.tool_name,
                    args=tool_call.arguments,
                    tool_call_id=tool_call.provider_tool_call_id,
                )
            )
        if recorded_call.assistant_text is not None:
            response_parts.append(TextPart(content=recorded_call.assistant_text))

        return ModelExecutionResult(
            assistant_text=recorded_call.assistant_text or "",
            tool_calls=tool_calls,
            model_response=ModelResponse(parts=response_parts),
            input_tokens=recorded_call.input_tokens,
            output_tokens=recorded_call.output_tokens,
        )


def _diff_enriched_context_sources(
    *,
    expected_sources,
    actual_sources,
    prefix: str,
    ignored_source_names: set[str] | None = None,
) -> list[str]:
    ignored = set(ignored_source_names or ())
    filtered_expected_sources = [
        source for source in expected_sources if source.source_name not in ignored
    ]
    filtered_actual_sources = [
        source for source in actual_sources if source.source_name not in ignored
    ]
    if fingerprint_replay_enriched_context_sources(
        filtered_actual_sources
    ) == fingerprint_replay_enriched_context_sources(filtered_expected_sources):
        return []

    expected_sources_by_name = {
        source.source_name: source for source in filtered_expected_sources
    }
    actual_sources_by_name = {
        source.source_name: source for source in filtered_actual_sources
    }
    drift_reasons: list[str] = []
    for source_name in sorted(
        set(expected_sources_by_name) | set(actual_sources_by_name)
    ):
        expected_source = expected_sources_by_name.get(source_name)
        actual_source = actual_sources_by_name.get(source_name)
        if expected_source is None:
            drift_reasons.append(f"{prefix} source added: {source_name}")
            continue
        if actual_source is None:
            drift_reasons.append(f"{prefix} source missing: {source_name}")
            continue
        if actual_source.fingerprint != expected_source.fingerprint:
            drift_reasons.append(f"{prefix} source drifted: {source_name}")
            continue
        if actual_source.provenance_class != expected_source.provenance_class:
            drift_reasons.append(f"{prefix} provenance changed: {source_name}")
            continue
        if actual_source.schema_version != expected_source.schema_version:
            drift_reasons.append(f"{prefix} schema version changed: {source_name}")
            continue
        if actual_source.inherited != expected_source.inherited:
            drift_reasons.append(f"{prefix} inheritance changed: {source_name}")
            continue
        if actual_source.item_count != expected_source.item_count:
            drift_reasons.append(f"{prefix} item count changed: {source_name}")
            continue
        if actual_source.additional_item_count != expected_source.additional_item_count:
            drift_reasons.append(f"{prefix} overflow count changed: {source_name}")
    return drift_reasons


class _ReplayToolRuntime(ToolRuntime):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        policy_engine: ToolPolicyEngine,
        policy_context: ToolPolicyContext,
        *,
        tool_requests: Sequence[ReplayToolRequestManifest],
        tool_results: Sequence[ReplayToolResultManifest],
    ) -> None:
        super().__init__(tool_registry, policy_engine, policy_context)
        self._tool_requests = {
            _ToolResultKey(manifest.provider_tool_call_id, manifest.tool_name): manifest
            for manifest in tool_requests
        }
        self._tool_results = {
            _ToolResultKey(manifest.provider_tool_call_id, manifest.tool_name): manifest
            for manifest in tool_results
        }
        self._consumed_results: set[_ToolResultKey] = set()

    def prepare_tool_call(self, tool_call) -> Any:
        prepared_tool_call = super().prepare_tool_call(tool_call)
        manifest = self._tool_requests.get(
            _ToolResultKey(
                prepared_tool_call.provider_tool_call_id,
                prepared_tool_call.tool_name,
            )
        )
        if manifest is None:
            raise _ReplayManifestDrift(
                "tool request no longer matches the recorded replay manifest: "
                f"{prepared_tool_call.tool_name}"
            )

        current_request = build_replay_tool_request_manifest(prepared_tool_call)
        if not _tool_request_matches(current_request, manifest):
            raise _ReplayManifestDrift(
                "tool request no longer matches the recorded replay manifest: "
                f"{prepared_tool_call.tool_name}"
            )
        return prepared_tool_call

    async def execute(
        self,
        prepared,
        on_output_chunk=None,
    ) -> ToolExecutionResult:
        del on_output_chunk
        return self._recorded_execution_result(prepared)

    async def execute_approved(
        self,
        prepared,
        on_output_chunk=None,
    ) -> ToolExecutionResult:
        del on_output_chunk
        return self._recorded_execution_result(prepared)

    def _recorded_execution_result(self, prepared) -> ToolExecutionResult:
        result_key = _ToolResultKey(
            prepared.provider_tool_call_id,
            prepared.tool_name,
        )
        manifest = self._tool_results.get(result_key)
        if manifest is None:
            raise _ReplayFailure(
                "missing recorded tool result for replayed tool call: "
                f"{prepared.tool_name}"
            )
        if result_key in self._consumed_results:
            raise _ReplayFailure(
                f"recorded tool result already consumed for {prepared.tool_name}"
            )
        self._consumed_results.add(result_key)

        if not manifest.success:
            raise RuntimeError(manifest.error_message or manifest.summary)

        return ToolExecutionResult(
            event_tool_call_id=prepared.event_tool_call_id,
            provider_tool_call_id=prepared.provider_tool_call_id,
            tool_name=prepared.tool_name,
            output_payload=manifest.output_payload or {},
            summary=manifest.summary,
        )


def _build_replay_actions(events: Sequence[EventEnvelope]) -> list[ReplayAction]:
    actions: list[ReplayAction] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, UserMessageReceived):
            actions.append(ReplayAction(action_type="user_message", text=payload.text))
        elif isinstance(payload, RuntimeNoteRecorded):
            actions.append(
                ReplayAction(
                    action_type="runtime_note",
                    category=payload.category,
                    message=payload.message,
                )
            )
        elif isinstance(payload, ApprovalResolved):
            actions.append(
                ReplayAction(
                    action_type="approval",
                    decision=payload.decision,
                )
            )
        elif isinstance(payload, UserAnswerProvided):
            actions.append(
                ReplayAction(
                    action_type="user_answer",
                    answer=payload.answer,
                )
            )
    return actions


def _build_replay_bundle_session_config(source_session: SessionRecord) -> SessionConfig:
    return SessionConfig(
        model_name=source_session.model_name,
        cwd=source_session.cwd,
        approval_mode=source_session.approval_mode,
        parent_session_id=source_session.parent_session_id,
        forked_from_turn_id=source_session.forked_from_turn_id,
        forked_from_sequence=source_session.forked_from_sequence,
        branch_label=source_session.branch_label,
    )


def _build_inherited_messages(
    events: Sequence[EventEnvelope],
) -> list[InheritedTranscriptMessage]:
    inherited_messages = [
        InheritedTranscriptMessage(
            source_message_id=payload.source_message_id,
            source_turn_id=payload.source_turn_id,
            role=payload.role,
            parts=payload.parts,
            created_at=payload.source_created_at,
        )
        for event in events
        if isinstance((payload := event.payload), TranscriptMessageImported)
    ]
    inherited_messages.sort(
        key=lambda message: (message.created_at, str(message.source_message_id))
    )
    return inherited_messages


def _build_inherited_runtime_notes(
    session_id: SessionId,
    source_session: SessionRecord,
    events: Sequence[EventEnvelope],
    session_repository: SessionRepository,
) -> list[RuntimeNoteRecord]:
    imported_notes = [
        RuntimeNoteRecord(
            source_session_id=payload.source_session_id,
            source_sequence=payload.source_sequence,
            category=payload.category,
            message=payload.message,
            created_at=payload.source_created_at,
            inherited=True,
        )
        for event in events
        if isinstance((payload := event.payload), RuntimeNoteImported)
    ]
    if imported_notes or source_session.parent_session_id is None:
        return imported_notes

    return [
        note
        for note in session_repository.list_runtime_notes(session_id)
        if note.inherited
    ]


def _build_replay_import_events(
    bundle: ReplayBundle,
    repository: SQLiteSessionRepository,
    session_id: SessionId,
) -> list[EventEnvelope]:
    if not bundle.inherited_messages:
        return []

    parent_session_id = bundle.session_config.parent_session_id
    forked_from_turn_id = bundle.session_config.forked_from_turn_id
    forked_from_sequence = bundle.session_config.forked_from_sequence
    if (
        parent_session_id is None
        or forked_from_turn_id is None
        or forked_from_sequence is None
    ):
        raise _ReplayUnsupportedSession(
            "forked replay bundle is missing lineage metadata for inherited transcript"
        )

    return repository.build_imported_transcript_events(
        session_id,
        ResolvedForkPoint(
            parent_session_id=parent_session_id,
            turn_id=forked_from_turn_id,
            sequence=forked_from_sequence,
            inherited_messages=list(bundle.inherited_messages),
        ),
    )


def _build_replay_runtime_note_import_events(
    bundle: ReplayBundle,
    session_id: SessionId,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=RuntimeNoteImported(
                source_session_id=note.source_session_id,
                source_sequence=note.source_sequence,
                category=note.category,
                message=note.message,
                source_created_at=note.created_at,
            ),
        )
        for note in bundle.inherited_runtime_notes
    ]


def _build_recorded_model_calls(
    events: Sequence[EventEnvelope],
    model_call_manifests: Sequence[ReplayModelCallManifest],
    tool_request_manifests: Sequence[ReplayToolRequestManifest],
) -> list[ReplayRecordedModelCall]:
    model_start_indexes = [
        index
        for index, event in enumerate(events)
        if isinstance(event.payload, ModelCallStarted)
    ]
    if len(model_start_indexes) != len(model_call_manifests):
        raise _ReplayFailure(
            "recorded model call manifests do not match the session event count"
        )

    recorded_calls: list[ReplayRecordedModelCall] = []
    tool_request_index = 0
    for model_index, start_index in enumerate(model_start_indexes):
        completed_index, completed_payload = _find_model_call_completed_event(
            events,
            start_index=start_index,
        )
        text_deltas = [
            event.payload.delta
            for event in events[start_index:completed_index]
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        assistant_text: str | None = None
        tool_calls: list[ReplayRecordedToolCall] = []

        lookahead_index = completed_index + 1
        while lookahead_index < len(events):
            payload = events[lookahead_index].payload
            if isinstance(payload, ModelCallStarted):
                break
            if isinstance(payload, ModelToolCallRequested):
                if tool_request_index >= len(tool_request_manifests):
                    raise _ReplayFailure(
                        "recorded tool request manifests ran out before session "
                        "event reconstruction finished"
                    )
                manifest = tool_request_manifests[tool_request_index]
                tool_request_index += 1
                tool_calls.append(
                    ReplayRecordedToolCall(
                        provider_tool_call_id=manifest.provider_tool_call_id,
                        tool_name=manifest.tool_name,
                        arguments=dict(manifest.validated_arguments),
                    )
                )
            elif isinstance(payload, AssistantMessageCompleted):
                assistant_text = _assistant_message_text(payload)
            elif isinstance(payload, TurnCompleted | TurnFailed):
                break
            lookahead_index += 1

        if assistant_text is None and text_deltas:
            assistant_text = "".join(text_deltas).strip() or None
        if assistant_text is None and not tool_calls:
            raise _ReplayFailure(
                "could not reconstruct a recorded model response from session events"
            )

        recorded_calls.append(
            ReplayRecordedModelCall(
                manifest=model_call_manifests[model_index],
                assistant_text=assistant_text,
                text_deltas=text_deltas,
                tool_calls=tool_calls,
                input_tokens=completed_payload.input_tokens,
                output_tokens=completed_payload.output_tokens,
            )
        )

    if tool_request_index != len(tool_request_manifests):
        raise _ReplayFailure(
            "recorded tool request manifests were not fully consumed by replay "
            "session reconstruction"
        )
    return recorded_calls


def _find_model_call_completed_event(
    events: Sequence[EventEnvelope],
    *,
    start_index: int,
) -> tuple[int, ModelCallCompleted]:
    start_payload = cast(ModelCallStarted, events[start_index].payload)
    for event_index in range(start_index + 1, len(events)):
        payload = events[event_index].payload
        if (
            isinstance(payload, ModelCallCompleted)
            and payload.turn_id == start_payload.turn_id
        ):
            return event_index, payload
    raise _ReplayFailure("session is missing a matching ModelCallCompleted event")


def _build_replay_model_adapter(bundle: ReplayBundle) -> PydanticAIModelAdapter:
    if not bundle.model_calls:
        raise _ReplayFailure("replay bundle does not contain model calls")

    provider, model_name = _split_model_name(bundle.session_config.model_name)
    runtime_config = bundle.model_calls[0].manifest.runtime_config
    return PydanticAIModelAdapter(
        ModelProviderConfig(
            model_name=model_name,
            provider=provider,
            model_settings=dict(runtime_config.model_settings),
            allow_text_output=runtime_config.allow_text_output,
            allow_image_output=runtime_config.allow_image_output,
        )
    )


def _build_replay_session_config(
    bundle: ReplayBundle,
    *,
    workspace_root: Path | None = None,
) -> SessionConfig:
    replay_cwd = bundle.session_config.cwd
    if workspace_root is not None:
        replay_cwd = workspace_root.resolve()
    return bundle.session_config.model_copy(update={"cwd": replay_cwd})


def _build_replay_tool_runtime(
    bundle: ReplayBundle,
    *,
    workspace_root: Path | None = None,
) -> _ReplayToolRuntime | None:
    recorded_tool_names = sorted(
        {
            tool_name
            for model_call in bundle.model_calls
            for tool_name in model_call.manifest.runtime_config.tool_names
        }
        | {manifest.tool_name for manifest in bundle.tool_requests}
    )
    if not recorded_tool_names:
        return None

    replay_session_config = _build_replay_session_config(
        bundle,
        workspace_root=workspace_root,
    )

    try:
        approval_mode = ApprovalMode(replay_session_config.approval_mode)
    except ValueError as exc:
        raise _ReplayFailure(
            "invalid approval mode persisted for replay bundle: "
            f"{replay_session_config.approval_mode}"
        ) from exc

    full_registry = build_ask_user_tool_registry(replay_session_config.cwd)
    registered_tools = {tool.spec.name: tool for tool in full_registry.list_tools()}
    missing_tools = [
        tool_name
        for tool_name in recorded_tool_names
        if tool_name not in registered_tools
    ]
    if missing_tools:
        raise _ReplayManifestDrift(
            "current runtime no longer exposes recorded replay tools: "
            f"{', '.join(missing_tools)}"
        )

    filtered_registry = ToolRegistry(
        [registered_tools[tool_name] for tool_name in recorded_tool_names]
    )
    return _ReplayToolRuntime(
        filtered_registry,
        ToolPolicyEngine(),
        ToolPolicyContext(
            workspace_root=replay_session_config.cwd,
            approval_mode=approval_mode,
        ),
        tool_requests=bundle.tool_requests,
        tool_results=bundle.tool_results,
    )


def _normalize_session(
    session_id: SessionId,
    repository: SessionRepository,
    events: Sequence[EventEnvelope],
) -> ReplayNormalizedSession:
    session_record = repository.get_session(session_id)
    if session_record is None:
        raise _ReplayFailure(f"unknown replay session {session_id}")
    session_state = repository.get_session_state(session_id)
    if session_state is None:
        raise _ReplayFailure(f"unknown session state for replay session {session_id}")
    transcript_messages = repository.list_transcript_messages(session_id)
    imported_message_ids = {
        payload.message_id
        for event in events
        if isinstance((payload := event.payload), TranscriptMessageImported)
    }
    normalized_transcript = [
        _normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
    ]
    inherited_transcript = [
        _normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
        if message.message_id in imported_message_ids
    ]
    post_fork_transcript = [
        _normalize_transcript_message(message.role, message.parts)
        for message in transcript_messages
        if message.message_id not in imported_message_ids
    ]

    return ReplayNormalizedSession(
        transcript=normalized_transcript,
        lineage=_normalize_lineage(session_record),
        inherited_transcript=inherited_transcript,
        post_fork_transcript=post_fork_transcript,
        tool_calls=[
            ReplayToolCallSnapshot(
                tool_name=tool_call.tool_name,
                status=_enum_value(tool_call.status),
                summary=tool_call.summary,
            )
            for tool_call in repository.list_tool_calls(session_id)
        ],
        approvals=[
            ReplayApprovalSnapshot(
                subject=approval.subject,
                reason=approval.reason,
                status=_enum_value(approval.status),
                decided_by=approval.decided_by,
            )
            for approval in repository.list_approvals(session_id)
        ],
        questions=_normalize_questions(events),
        event_families=[
            event.event_type
            for event in events
            if event.event_type != "ReplayArtifactRecorded"
        ],
        final_state=ReplayFinalStateSnapshot(
            status=_enum_value(session_state.status),
            has_active_turn=session_state.current_turn_id is not None,
            has_pending_approval=session_state.pending_approval_id is not None,
            has_pending_question=session_state.pending_question_id is not None,
        ),
    )


def _normalize_questions(
    events: Sequence[EventEnvelope],
) -> list[ReplayQuestionSnapshot]:
    questions: list[ReplayQuestionSnapshot] = []
    question_indexes: dict[str, int] = {}
    for event in events:
        payload = event.payload
        if isinstance(payload, UserQuestionAsked):
            question_indexes[str(payload.question_id)] = len(questions)
            questions.append(ReplayQuestionSnapshot(question=payload.question))
            continue
        if not isinstance(payload, UserAnswerProvided):
            continue
        question_index = question_indexes.get(str(payload.question_id))
        if question_index is None:
            questions.append(ReplayQuestionSnapshot(question="", answer=payload.answer))
            continue
        questions[question_index].answer = payload.answer
    return questions


def _collect_mismatches(
    baseline: ReplayNormalizedSession,
    replay: ReplayNormalizedSession,
) -> list[str]:
    mismatches: list[str] = []
    baseline_dump = baseline.model_dump(mode="json")
    replay_dump = replay.model_dump(mode="json")
    for field_name in (
        "transcript",
        "lineage",
        "inherited_transcript",
        "post_fork_transcript",
        "tool_calls",
        "approvals",
        "questions",
        "event_families",
        "final_state",
    ):
        if baseline_dump[field_name] != replay_dump[field_name]:
            mismatches.append(f"{field_name} drift")
    return mismatches


def _assistant_message_text(payload: AssistantMessageCompleted) -> str:
    return "\n".join(
        part.text for part in payload.parts if part.kind == cast(Any, "text")
    )


def _prepared_turn_tool_names(prepared_turn: PreparedModelTurn) -> list[str]:
    return sorted(tool.name for tool in prepared_turn.request_parameters.function_tools)


def _hydrate_lineage_aware_bundle(bundle: ReplayBundle) -> ReplayBundle:
    baseline_updates: dict[str, object] = {}
    baseline = bundle.baseline

    lineage = baseline.lineage
    if lineage is None:
        lineage = _normalize_lineage_from_session_config(bundle.session_config)
        if lineage is not None:
            baseline_updates["lineage"] = lineage

    inherited_transcript = list(baseline.inherited_transcript)
    if not inherited_transcript and bundle.inherited_messages:
        inherited_transcript = [
            _normalize_transcript_message(message.role, message.parts)
            for message in bundle.inherited_messages
        ]
        baseline_updates["inherited_transcript"] = inherited_transcript

    if not baseline.post_fork_transcript and baseline.transcript:
        inherited_count = len(inherited_transcript)
        baseline_updates["post_fork_transcript"] = list(
            baseline.transcript[inherited_count:]
        )

    if not baseline_updates:
        return bundle

    return bundle.model_copy(
        update={"baseline": baseline.model_copy(update=baseline_updates)}
    )


def _normalize_lineage(session: SessionRecord) -> ReplayLineageSnapshot | None:
    return _normalize_lineage_from_session_config(
        SessionConfig(
            model_name=session.model_name,
            cwd=session.cwd,
            approval_mode=session.approval_mode,
            dashboard_url=None,
            parent_session_id=session.parent_session_id,
            forked_from_turn_id=session.forked_from_turn_id,
            forked_from_sequence=session.forked_from_sequence,
            branch_label=session.branch_label,
        )
    )


def _normalize_lineage_from_session_config(
    session_config: SessionConfig,
) -> ReplayLineageSnapshot | None:
    if (
        session_config.parent_session_id is None
        or session_config.forked_from_turn_id is None
        or session_config.forked_from_sequence is None
    ):
        return None
    return ReplayLineageSnapshot(
        parent_session_id=str(session_config.parent_session_id),
        forked_from_turn_id=str(session_config.forked_from_turn_id),
        forked_from_sequence=session_config.forked_from_sequence,
        branch_label=session_config.branch_label,
    )


def _normalize_transcript_message(
    role: str,
    parts: Sequence[Any],
) -> ReplayTranscriptMessage:
    return ReplayTranscriptMessage(
        role=role,
        parts=[ReplayTranscriptPart(kind=part.kind, text=part.text) for part in parts],
    )


def _tool_request_matches(
    current: ReplayToolRequestManifest,
    expected: ReplayToolRequestManifest,
) -> bool:
    return (
        current.provider_tool_call_id == expected.provider_tool_call_id
        and current.tool_name == expected.tool_name
        and current.validated_arguments == expected.validated_arguments
        and current.policy_decision == expected.policy_decision
    )


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _split_model_name(model_name: str) -> tuple[str | None, str]:
    provider, separator, resolved_model_name = model_name.partition(":")
    if separator == "":
        return None, model_name
    return provider, resolved_model_name
