"""Runtime helpers for executing registered tools inside a turn."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, ToolReturnPart

from glassbox.core import PolicyDecision, ToolCallId, new_tool_call_id
from glassbox.tools.policy import ToolPolicyContext, ToolPolicyEngine
from glassbox.tools.registry import StreamingTool, Tool, ToolRegistry


class ToolCallRequest(Protocol):
    """Minimal model tool-call shape needed by the runtime helper."""

    tool_name: str
    arguments: str | dict[str, object] | None
    tool_call_id: str


@dataclass(frozen=True, slots=True)
class PreparedToolExecution:
    """Validated tool execution request ready for policy handling."""

    event_tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    tool: Tool[Any, Any]
    validated_arguments: BaseModel
    policy_decision: PolicyDecision


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """Result from one successfully executed tool call."""

    event_tool_call_id: ToolCallId
    provider_tool_call_id: str
    tool_name: str
    output_payload: dict[str, object]
    summary: str

    def to_model_request(self) -> ModelRequest:
        """Convert the tool result into a provider-facing tool return request."""

        timestamp = datetime.now(tz=UTC)
        return ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name=self.tool_name,
                    tool_call_id=self.provider_tool_call_id,
                    content=self.output_payload,
                    timestamp=timestamp,
                )
            ],
            timestamp=timestamp,
        )


class ToolRuntime:
    """Execute model-requested tools against a registry and policy context."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        policy_engine: ToolPolicyEngine,
        policy_context: ToolPolicyContext,
    ) -> None:
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self._policy_context = policy_context

    @property
    def tool_registry(self) -> ToolRegistry:
        """Return the tool registry exposed for the current session."""

        return self._tool_registry

    def prepare_tool_call(self, tool_call: ToolCallRequest) -> PreparedToolExecution:
        """Resolve, validate, and authorize one model-emitted tool call."""

        tool = self._tool_registry.require(tool_call.tool_name)
        raw_arguments = _tool_arguments_payload(tool_call.arguments)
        validated_arguments = tool.spec.input_model.model_validate(raw_arguments)
        policy_decision = self._policy_engine.evaluate(
            tool.spec,
            arguments=validated_arguments,
            context=self._policy_context,
        )
        return PreparedToolExecution(
            event_tool_call_id=new_tool_call_id(),
            provider_tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            tool=tool,
            validated_arguments=validated_arguments,
            policy_decision=policy_decision,
        )

    async def execute(
        self,
        prepared: PreparedToolExecution,
        on_output_chunk: Callable[[str, str], None] | None = None,
    ) -> ToolExecutionResult:
        """Execute one prepared tool call after policy approval."""

        if (
            not prepared.policy_decision.allowed
            or prepared.policy_decision.requires_approval
        ):
            raise ValueError(prepared.policy_decision.reason)

        return await self._run_tool(prepared, on_output_chunk=on_output_chunk)

    async def execute_approved(
        self,
        prepared: PreparedToolExecution,
        on_output_chunk: Callable[[str, str], None] | None = None,
    ) -> ToolExecutionResult:
        """Execute a tool whose approval has been explicitly granted by the operator.

        Bypasses the ``requires_approval`` guard so that a previously suspended
        tool call can resume after an ``ApprovalResolved(decision=APPROVED)`` event.
        """

        if not prepared.policy_decision.allowed:
            raise ValueError(prepared.policy_decision.reason)

        return await self._run_tool(prepared, on_output_chunk=on_output_chunk)

    async def _run_tool(
        self,
        prepared: PreparedToolExecution,
        on_output_chunk: Callable[[str, str], None] | None = None,
    ) -> ToolExecutionResult:
        """Execute the tool, handling both streaming and non-streaming tools."""

        if isinstance(prepared.tool, StreamingTool):
            chunk_callback = (
                on_output_chunk if on_output_chunk is not None else _noop_chunk
            )
            raw_output = await prepared.tool.execute_streaming(
                prepared.validated_arguments, chunk_callback
            )
        else:
            raw_output = await prepared.tool.execute(prepared.validated_arguments)
        validated_output = prepared.tool.spec.output_model.model_validate(
            raw_output.model_dump(mode="python")
            if isinstance(raw_output, BaseModel)
            else raw_output
        )
        output_payload = validated_output.model_dump(mode="json")
        return ToolExecutionResult(
            event_tool_call_id=prepared.event_tool_call_id,
            provider_tool_call_id=prepared.provider_tool_call_id,
            tool_name=prepared.tool_name,
            output_payload=output_payload,
            summary=f"{prepared.tool_name} completed",
        )


def _tool_arguments_payload(
    arguments: str | dict[str, object] | None,
) -> dict[str, object]:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return dict(arguments)

    decoded = json.loads(arguments)
    if not isinstance(decoded, dict):
        raise ValueError("tool call arguments must decode to a JSON object")
    return {str(key): value for key, value in decoded.items()}


def _noop_chunk(stream: str, chunk: str) -> None:
    pass
