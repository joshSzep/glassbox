"""Deterministic replay execution against an isolated runtime."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart

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
from glassbox.runtime.model_loop import ModelLoopRunner
from glassbox.runtime.replay_bundle_io import (
    build_replay_import_events,
    build_replay_runtime_note_import_events,
)
from glassbox.runtime.replay_compare import normalize_session
from glassbox.runtime.replay_failures import (
    ReplayFailure,
    ReplayManifestDrift,
)
from glassbox.runtime.replay_fingerprints import (
    build_replay_enriched_context_sources,
    fingerprint_replay_enriched_context_payload,
    fingerprint_replay_enriched_context_sources,
)
from glassbox.runtime.replay_manifests import (
    ReplayToolRequestManifest,
    ReplayToolResultManifest,
    build_replay_prepared_turn_snapshot,
    build_replay_runtime_config_snapshot,
    build_replay_tool_request_manifest,
)
from glassbox.runtime.replay_models import ReplayBundle, ReplayNormalizedSession
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
)
from glassbox.store.sqlite import initialize_database, open_database
from glassbox.tools import (
    ApprovalMode,
    ToolExecutionResult,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRegistry,
    ToolRuntime,
    build_ask_user_tool_registry,
)


async def execute_replay_bundle(
    bundle: ReplayBundle,
    *,
    workspace_root: Path | None = None,
) -> ReplayNormalizedSession:
    if not bundle.model_calls:
        raise ReplayFailure("replay bundle does not contain model calls")

    replay_session_config = build_replay_session_config(
        bundle,
        workspace_root=workspace_root,
    )
    model_executor = _ReplayModelExecutor(
        bundle.model_calls,
        ignored_live_source_names=(
            {"repository_context"} if workspace_root is not None else set()
        ),
    )
    tool_runtime = build_replay_tool_runtime(
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
            bus: EventBus = EventBus()
            turn_engine = TurnEngine(
                repository,
                bus,
                TurnContextBuilder(repository),
                lambda _session: build_replay_model_adapter(bundle),
                lambda _session: model_executor,
                ((lambda _session: tool_runtime) if tool_runtime is not None else None),
                artifact_repository=artifact_repository,
                model_loop_runner=ModelLoopRunner(),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            replay_state = await supervisor.start_session(replay_session_config)
            restored_import_events = build_replay_import_events(
                bundle,
                repository,
                replay_state.session_id,
            )
            if restored_import_events:
                for event in repository.append_events(restored_import_events):
                    bus.publish(event)

            restored_runtime_note_events = build_replay_runtime_note_import_events(
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

                session_state = repository.get_session_state(replay_state.session_id)
                if session_state is None:
                    raise ReplayFailure("replay session state disappeared")

                if action.action_type == "approval":
                    if session_state.pending_approval_id is None:
                        raise ReplayFailure(
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
                    raise ReplayFailure(
                        "replay session is not awaiting user input when one was "
                        "recorded"
                    )
                assert action.answer is not None
                await supervisor.provide_user_answer(
                    replay_state.session_id,
                    session_state.pending_question_id,
                    action.answer,
                )

            return normalize_session(
                replay_state.session_id,
                repository,
                repository.read_session_events(replay_state.session_id),
            )
        finally:
            connection.close()


@dataclass(frozen=True, slots=True)
class _ToolResultKey:
    provider_tool_call_id: str
    tool_name: str


class _ReplayModelExecutor(ModelExecutor):
    def __init__(
        self,
        model_calls: Sequence,
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
            raise ReplayFailure("replay requested more model calls than were recorded")

        recorded_call = self._model_calls[self._index]
        self._index += 1

        current_tool_names = prepared_turn_tool_names(prepared_turn)
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
                diff_enriched_context_sources(
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
                    diff_enriched_context_sources(
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
            raise ReplayManifestDrift("; ".join(drift_reasons))

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


def diff_enriched_context_sources(
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
            raise ReplayManifestDrift(
                "tool request no longer matches the recorded replay manifest: "
                f"{prepared_tool_call.tool_name}"
            )

        current_request = build_replay_tool_request_manifest(prepared_tool_call)
        if not tool_request_matches(current_request, manifest):
            raise ReplayManifestDrift(
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
            raise ReplayFailure(
                "missing recorded tool result for replayed tool call: "
                f"{prepared.tool_name}"
            )
        if result_key in self._consumed_results:
            raise ReplayFailure(
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


def build_replay_model_adapter(bundle: ReplayBundle) -> PydanticAIModelAdapter:
    if not bundle.model_calls:
        raise ReplayFailure("replay bundle does not contain model calls")

    provider, model_name = split_model_name(bundle.session_config.model_name)
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


def build_replay_session_config(
    bundle: ReplayBundle,
    *,
    workspace_root: Path | None = None,
):
    replay_cwd = bundle.session_config.cwd
    if workspace_root is not None:
        replay_cwd = workspace_root.resolve()
    return bundle.session_config.model_copy(update={"cwd": replay_cwd})


def build_replay_tool_runtime(
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

    replay_session_config = build_replay_session_config(
        bundle,
        workspace_root=workspace_root,
    )

    try:
        approval_mode = ApprovalMode(replay_session_config.approval_mode)
    except ValueError as exc:
        raise ReplayFailure(
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
        raise ReplayManifestDrift(
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


def prepared_turn_tool_names(prepared_turn: PreparedModelTurn) -> list[str]:
    return sorted(tool.name for tool in prepared_turn.request_parameters.function_tools)


def tool_request_matches(
    current: ReplayToolRequestManifest,
    expected: ReplayToolRequestManifest,
) -> bool:
    return (
        current.provider_tool_call_id == expected.provider_tool_call_id
        and current.tool_name == expected.tool_name
        and current.validated_arguments == expected.validated_arguments
        and current.policy_decision == expected.policy_decision
    )


def split_model_name(model_name: str) -> tuple[str | None, str]:
    provider, separator, resolved_model_name = model_name.partition(":")
    if separator == "":
        return None, model_name
    return provider, resolved_model_name
