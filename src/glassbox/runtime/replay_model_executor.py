"""Recorded model executor used by deterministic replay."""

from collections.abc import Sequence

from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart

from glassbox.llm import ModelExecutionResult
from glassbox.llm import ModelExecutor
from glassbox.llm import ModelTextDelta
from glassbox.llm import ModelToolCall
from glassbox.llm import PreparedModelTurn
from glassbox.llm import PydanticAIStreamTranslator
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_failures import ReplayManifestDrift
from glassbox.runtime.replay_fingerprints import build_replay_enriched_context_sources
from glassbox.runtime.replay_fingerprints import (
    fingerprint_replay_enriched_context_payload,
)
from glassbox.runtime.replay_fingerprints import (
    fingerprint_replay_enriched_context_sources,
)
from glassbox.runtime.replay_manifests import build_replay_prepared_turn_snapshot
from glassbox.runtime.replay_manifests import build_replay_runtime_config_snapshot


class ReplayModelExecutor(ModelExecutor):
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


def prepared_turn_tool_names(prepared_turn: PreparedModelTurn) -> list[str]:
    return sorted(tool.name for tool in prepared_turn.request_parameters.function_tools)
