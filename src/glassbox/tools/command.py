"""Command execution tool with subprocess streaming for Glassbox sessions."""

import asyncio
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.read_only import build_read_only_tool_registry
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec
from glassbox.tools.registry import ToolStreamingMode

_MAX_OUTPUT_BYTES = 100 * 1024  # 100 KB cap before truncation


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

        cwd = _resolve_workspace_cwd(self._workspace_root, arguments.cwd)

        # The command string originates from the model, not direct user input.
        # Policy evaluation (destructive-pattern blocking and approval gating)
        # must happen before this method is called via ToolRuntime.
        process = await asyncio.create_subprocess_shell(
            arguments.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        total_bytes = 0
        truncated = False
        timed_out = False

        def _record_line(stream: str, raw_line: bytes, parts: list[str]) -> None:
            nonlocal total_bytes, truncated
            total_bytes += len(raw_line)
            if total_bytes <= _MAX_OUTPUT_BYTES:
                text = raw_line.decode("utf-8", errors="replace")
                parts.append(text)
                on_chunk(stream, text)
            else:
                truncated = True

        assert process.stdout is not None
        assert process.stderr is not None
        stdout_stream = process.stdout
        stderr_stream = process.stderr

        async def _read_stdout() -> None:
            async for raw_line in stdout_stream:
                _record_line("stdout", raw_line, stdout_parts)

        async def _read_stderr() -> None:
            async for raw_line in stderr_stream:
                _record_line("stderr", raw_line, stderr_parts)

        exit_code = -1
        try:
            async with asyncio.timeout(float(arguments.timeout)):
                await asyncio.gather(_read_stdout(), _read_stderr())
                exit_code = await process.wait()
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                async with asyncio.timeout(5.0):
                    await process.wait()
            except TimeoutError:
                pass
            if process.returncode is not None:
                exit_code = process.returncode
            timed_out = True

        return RunCommandResult(
            command=arguments.command,
            exit_code=exit_code,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            truncated=truncated,
            timed_out=timed_out,
        )


def build_command_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build a tool registry with read-only tools and the command runner."""

    registry = build_read_only_tool_registry(workspace_root)
    registry.register(RunCommandTool(workspace_root))
    return registry


def _resolve_workspace_cwd(workspace_root: Path, relative_path: str) -> Path:
    if relative_path == ".":
        return workspace_root
    resolved = (workspace_root / relative_path).resolve(strict=False)
    if not resolved.is_relative_to(workspace_root):
        raise ValueError(
            f"working directory '{relative_path}' is outside workspace "
            f"'{workspace_root}'"
        )
    return resolved
