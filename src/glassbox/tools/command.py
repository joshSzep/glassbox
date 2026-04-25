"""Command execution tool with subprocess streaming for Glassbox sessions."""

import asyncio
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools._subprocess import DEFAULT_MAX_OUTPUT_BYTES
from glassbox.tools._subprocess import CommandExecutionEnvelope
from glassbox.tools._subprocess import CommandFailureCategory
from glassbox.tools._subprocess import build_command_execution_envelope
from glassbox.tools._subprocess import capture_streaming_subprocess
from glassbox.tools._subprocess import resolve_workspace_cwd
from glassbox.tools.read_only import build_read_only_tool_registry
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec
from glassbox.tools.registry import ToolStreamingMode


class RunCommandArgs(BaseModel):
    """Arguments for running one shell command inside the workspace."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, description="Shell command to execute.")
    cwd: str = Field(
        default=".",
        description="Working directory relative to the workspace root.",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum seconds to wait before killing the process.",
    )


class RunCommandResult(BaseModel):
    """Structured result from one completed or timed-out command invocation."""

    model_config = ConfigDict(extra="forbid")

    command: str
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool = False
    timed_out: bool = False
    execution_envelope: CommandExecutionEnvelope
    failure_category: CommandFailureCategory | None = None
    termination_signal: int | None = None


class RunCommandTool:
    """Run a shell command inside the workspace and stream its output."""

    spec = ToolSpec(
        name="run_command",
        description=(
            "Run a shell command inside the workspace directory. "
            "stdout and stderr are captured and streamed as output chunks."
        ),
        input_model=RunCommandArgs,
        output_model=RunCommandResult,
        risk_level=ToolRiskLevel.COMMAND,
        streaming_mode=ToolStreamingMode.TEXT,
        command_argument_name="command",
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: RunCommandArgs) -> RunCommandResult:
        """Execute the command; streaming output is discarded."""

        return await self.execute_streaming(arguments, lambda _stream, _chunk: None)

    async def execute_streaming(
        self,
        arguments: RunCommandArgs,
        on_chunk: Callable[[str, str], None],
    ) -> RunCommandResult:
        """Execute the command and deliver each output line to on_chunk."""

        cwd = resolve_workspace_cwd(self._workspace_root, arguments.cwd)
        envelope = build_command_execution_envelope(
            workspace_root=self._workspace_root,
            requested_cwd=arguments.cwd,
            resolved_cwd=cwd,
            timeout_seconds=arguments.timeout,
            output_limit_bytes=DEFAULT_MAX_OUTPUT_BYTES,
        )

        # The command string originates from the model, not direct user input.
        # Policy evaluation (destructive-pattern blocking and approval gating)
        # must happen before this method is called via ToolRuntime.
        process = await asyncio.create_subprocess_shell(
            arguments.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        captured = await capture_streaming_subprocess(
            process,
            timeout_seconds=arguments.timeout,
            on_chunk=on_chunk,
            output_limit_bytes=DEFAULT_MAX_OUTPUT_BYTES,
        )

        return RunCommandResult(
            command=arguments.command,
            exit_code=captured.exit_code,
            stdout=captured.stdout,
            stderr=captured.stderr,
            truncated=captured.truncated,
            timed_out=captured.timed_out,
            execution_envelope=envelope,
            failure_category=captured.failure_category,
            termination_signal=captured.termination_signal,
        )


def build_command_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build a tool registry with read-only tools and the command runner."""

    registry = build_read_only_tool_registry(workspace_root)
    registry.register(RunCommandTool(workspace_root))
    return registry
