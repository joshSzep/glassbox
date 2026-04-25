"""Runtime helpers for executing registered tools inside a turn."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Protocol
from typing import cast

from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ToolReturnPart

from glassbox.core import PolicyDecision
from glassbox.core import ToolCallId
from glassbox.core import new_tool_call_id
from glassbox.tools.policy import ToolPolicyContext
from glassbox.tools.policy import ToolPolicyEngine
from glassbox.tools.registry import StreamingTool
from glassbox.tools.registry import Tool
from glassbox.tools.registry import ToolRegistry


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
    success: bool
    output_payload: dict[str, object]
    summary: str
    exit_code: int | None = None
    error_message: str | None = None

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
        success, summary, exit_code, error_message = _classify_tool_result(
            prepared.tool_name,
            output_payload,
        )
        return ToolExecutionResult(
            event_tool_call_id=prepared.event_tool_call_id,
            provider_tool_call_id=prepared.provider_tool_call_id,
            tool_name=prepared.tool_name,
            success=success,
            output_payload=output_payload,
            summary=summary,
            exit_code=exit_code,
            error_message=error_message,
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


def _classify_tool_result(
    tool_name: str,
    output_payload: dict[str, object],
) -> tuple[bool, str, int | None, str | None]:
    exit_code = output_payload.get("exit_code")
    if not isinstance(exit_code, int):
        return True, f"{tool_name} completed", None, None

    failure_category = output_payload.get("failure_category")
    timeout_seconds = _execution_envelope_value(output_payload, "timeout_seconds")
    resolved_cwd = _execution_envelope_value(output_payload, "resolved_cwd")
    location_suffix = f" in {resolved_cwd}" if resolved_cwd else ""

    if failure_category == "timed_out":
        timeout_suffix = f" after {timeout_seconds}s" if timeout_seconds else ""
        summary = f"timed out{timeout_suffix}{location_suffix}"
        return False, summary, exit_code, summary

    if failure_category == "interrupted":
        termination_signal = output_payload.get("termination_signal")
        signal_suffix = (
            f" by signal {termination_signal}"
            if isinstance(termination_signal, int)
            else ""
        )
        summary = f"interrupted{signal_suffix}{location_suffix}"
        return False, summary, exit_code, summary

    if failure_category == "execution_error":
        summary = f"failed{location_suffix}"
        return False, summary, exit_code, f"{summary} (exit code {exit_code})"

    return True, f"completed{location_suffix}", exit_code, None


def _execution_envelope_value(
    output_payload: dict[str, object],
    key: str,
) -> str | int | None:
    envelope = output_payload.get("execution_envelope")
    if not isinstance(envelope, dict):
        return None
    value = cast(dict[str, object], envelope).get(key)
    if isinstance(value, (str, int)):
        return value
    return None
