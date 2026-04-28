"""Typed tool contracts and explicit registration for Glassbox tools."""

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import runtime_checkable

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ToolSchema(BaseModel):
    """Stable model-facing schema exported for tool usage."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters_json_schema: dict[str, object] = Field(default_factory=dict)


class ToolRiskLevel(StrEnum):
    """Coarse risk buckets used for future policy evaluation."""

    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    COMMAND = "command"


class ToolStreamingMode(StrEnum):
    """Streaming behavior declared by a tool implementation."""

    NONE = "none"
    TEXT = "text"
    STRUCTURED = "structured"


InputModelT = TypeVar("InputModelT", bound=BaseModel)
OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Typed contract for a tool implementation."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    risk_level: ToolRiskLevel
    streaming_mode: ToolStreamingMode = ToolStreamingMode.NONE
    path_argument_names: tuple[str, ...] = ()
    command_argument_name: str | None = None

    def __post_init__(self) -> None:
        if self.name.strip() == "":
            raise ValueError("tool name must not be blank")
        if self.description.strip() == "":
            raise ValueError("tool description must not be blank")
        if self.command_argument_name is not None:
            if self.command_argument_name.strip() == "":
                raise ValueError("command argument name must not be blank")

    def to_schema(self) -> ToolSchema:
        """Export the model-facing schema for this tool."""

        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.input_model.model_json_schema(),
        )


@runtime_checkable
class Tool(Protocol[InputModelT, OutputModelT]):
    """Base interface for explicitly registered tools."""

    spec: ToolSpec

    async def execute(self, arguments: InputModelT) -> OutputModelT:
        """Execute the tool for one validated argument payload."""


@runtime_checkable
class StreamingTool(Protocol):
    """Optional extension for tools that stream output chunks during execution."""

    spec: ToolSpec

    async def execute_streaming(
        self,
        arguments: BaseModel,
        on_chunk: Callable[[str, str], None],
        *,
        cancellation_controller: object | None = None,
    ) -> BaseModel:
        """Execute the tool and deliver output lines to on_chunk(stream, text)."""


class ToolRegistry:
    """Explicit registry for tool implementations and their typed contracts."""

    def __init__(self, tools: Sequence[Tool[Any, Any]] = ()) -> None:
        self._tools: dict[str, Tool[Any, Any]] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool[Any, Any]) -> None:
        """Register one tool implementation by its declared name."""

        tool_name = tool.spec.name
        if tool_name in self._tools:
            raise ValueError(f"duplicate tool name: {tool_name}")
        self._tools[tool_name] = tool

    def get(self, tool_name: str) -> Tool[Any, Any] | None:
        """Return one registered tool, or None when absent."""

        return self._tools.get(tool_name)

    def require(self, tool_name: str) -> Tool[Any, Any]:
        """Return one registered tool or raise when absent."""

        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(tool_name)
        return tool

    def list_tools(self) -> list[Tool[Any, Any]]:
        """Return registered tools in stable name order."""

        return [self._tools[name] for name in sorted(self._tools)]

    def list_specs(self) -> list[ToolSpec]:
        """Return typed tool contracts in stable name order."""

        return [tool.spec for tool in self.list_tools()]

    def list_schemas(self) -> list[ToolSchema]:
        """Return exported model-facing schemas in stable name order."""

        return [spec.to_schema() for spec in self.list_specs()]
