"""Helpers for preparing live turn execution state."""

from dataclasses import dataclass

from pydantic_ai.messages import ModelMessage

from glassbox.core.models import SessionRecord
from glassbox.llm import ModelAdapter
from glassbox.llm import ModelExecutor
from glassbox.llm import PreparedModelTurn
from glassbox.llm import build_system_prompt
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.context_models import TurnContext
from glassbox.runtime.model_loop import initial_model_messages
from glassbox.runtime.runtime_context_derivation import derive_runtime_context_snapshot
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import ToolRuntime


@dataclass(slots=True)
class PreparedTurnRun:
    """Prepared dependencies and conversation state for one live turn."""

    tool_runtime: ToolRuntime | None
    turn_context: TurnContext
    model_adapter: ModelAdapter
    model_executor: ModelExecutor
    prepared_turn: PreparedModelTurn
    conversation: list[ModelMessage]


class LiveTurnPreparation:
    """Build session-scoped turn context and model execution dependencies."""

    def __init__(
        self,
        session_repository: SessionRepository,
        context_builder: TurnContextBuilder,
        model_adapter_factory,
        model_executor_factory,
        tool_runtime_factory=None,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._context_builder = context_builder
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory
        self._tool_runtime_factory = tool_runtime_factory
        self._artifact_repository = artifact_repository

    def prepare(self, session_id, session: SessionRecord) -> PreparedTurnRun:
        tool_runtime = (
            self._tool_runtime_factory(session)
            if self._tool_runtime_factory is not None
            else None
        )
        turn_context = self._build_turn_context(
            session_id,
            session,
            tool_runtime=tool_runtime,
        )
        model_adapter = self._model_adapter_factory(session)
        model_executor = self._model_executor_factory(session)
        prepared_turn = model_adapter.build_turn_request(
            turn_context,
            system_prompt=build_system_prompt(turn_context),
        )
        return PreparedTurnRun(
            tool_runtime=tool_runtime,
            turn_context=turn_context,
            model_adapter=model_adapter,
            model_executor=model_executor,
            prepared_turn=prepared_turn,
            conversation=initial_model_messages(prepared_turn),
        )

    def _build_turn_context(
        self,
        session_id,
        session: SessionRecord,
        *,
        tool_runtime: ToolRuntime | None,
    ) -> TurnContext:
        runtime_context = derive_runtime_context_snapshot(
            self._session_repository,
            session_id,
            session.cwd,
            artifact_repository=self._artifact_repository,
            include_stale_artifacts=False,
        )
        return self._context_builder.build_from_runtime_context(
            session_id,
            runtime_context,
            tool_registry=(
                tool_runtime.tool_registry if tool_runtime is not None else None
            ),
        )
