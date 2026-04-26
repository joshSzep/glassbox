"""Deterministic replay execution against an isolated runtime."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.model_loop import ModelLoopRunner
from glassbox.runtime.replay_bundle_io import build_replay_import_events
from glassbox.runtime.replay_bundle_io import build_replay_runtime_note_import_events
from glassbox.runtime.replay_compare import normalize_session
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_failures import ReplayManifestDrift
from glassbox.runtime.replay_manifests import ReplayToolRequestManifest
from glassbox.runtime.replay_manifests import ReplayToolResultManifest
from glassbox.runtime.replay_manifests import build_replay_tool_request_manifest
from glassbox.runtime.replay_model_executor import ReplayModelExecutor
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.transport import InProcessEventTransport
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolExecutionResult
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRegistry
from glassbox.tools import ToolRuntime
from glassbox.tools import build_ask_user_tool_registry
from glassbox.tools import load_tool_policy_manifest


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
    model_executor = ReplayModelExecutor(
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
            event_transport = InProcessEventTransport()
            turn_engine = TurnEngine(
                repository,
                event_transport,
                TurnContextBuilder(repository),
                lambda _session: build_replay_model_adapter(bundle),
                lambda _session: model_executor,
                ((lambda _session: tool_runtime) if tool_runtime is not None else None),
                artifact_repository=artifact_repository,
                model_loop_runner=ModelLoopRunner(),
            )
            supervisor = SessionSupervisor(
                repository,
                event_transport,
                turn_engine=turn_engine,
            )
            replay_state = await supervisor.start_session(replay_session_config)
            restored_import_events = build_replay_import_events(
                bundle,
                repository,
                replay_state.session_id,
            )
            if restored_import_events:
                for event in repository.append_events(restored_import_events):
                    event_transport.publish(event)

            restored_runtime_note_events = build_replay_runtime_note_import_events(
                bundle,
                replay_state.session_id,
            )
            if restored_runtime_note_events:
                for event in repository.append_events(restored_runtime_note_events):
                    event_transport.publish(event)

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

        if not manifest.success and manifest.output_payload is None:
            raise RuntimeError(manifest.error_message or manifest.summary)

        output_payload = manifest.output_payload or {}
        exit_code = output_payload.get("exit_code")

        return ToolExecutionResult(
            event_tool_call_id=prepared.event_tool_call_id,
            provider_tool_call_id=prepared.provider_tool_call_id,
            tool_name=prepared.tool_name,
            success=manifest.success,
            output_payload=output_payload,
            summary=manifest.summary,
            exit_code=exit_code if isinstance(exit_code, int) else None,
            error_message=manifest.error_message,
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
    policy_manifest = load_tool_policy_manifest(replay_session_config.cwd)
    return _ReplayToolRuntime(
        filtered_registry,
        ToolPolicyEngine(),
        ToolPolicyContext(
            workspace_root=replay_session_config.cwd,
            approval_mode=approval_mode,
            policy_manifest=policy_manifest,
        ),
        tool_requests=bundle.tool_requests,
        tool_results=bundle.tool_results,
    )


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
