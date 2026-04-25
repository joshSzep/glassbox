"""Shared subprocess execution helpers for command-style tools."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

DEFAULT_MAX_OUTPUT_BYTES = 100 * 1024  # 100 KB cap before truncation

type CommandFailureCategory = Literal[
    "execution_error",
    "timed_out",
    "interrupted",
]
type CommandDirectoryPolicy = Literal[
    "workspace_root",
    "workspace_subdirectory",
]


class CommandExecutionEnvelope(BaseModel):
    """Reviewable execution constraints applied to one command-style tool run."""

    model_config = ConfigDict(extra="forbid")

    requested_cwd: str
    resolved_cwd: str
    directory_policy: CommandDirectoryPolicy
    timeout_seconds: int = Field(ge=1)
    output_limit_bytes: int = Field(ge=1)


@dataclass(frozen=True, slots=True)
class CapturedSubprocessOutput:
    """Captured subprocess output plus classified termination metadata."""

    exit_code: int
    stdout: str
    stderr: str
    truncated: bool
    timed_out: bool
    failure_category: CommandFailureCategory | None
    termination_signal: int | None


async def capture_streaming_subprocess(
    process: asyncio.subprocess.Process,
    *,
    timeout_seconds: int,
    on_chunk: Callable[[str, str], None],
    output_limit_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> CapturedSubprocessOutput:
    """Capture and classify subprocess output with bounded buffering."""

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    total_bytes = 0
    truncated = False
    timed_out = False

    def record_line(stream: str, raw_line: bytes, parts: list[str]) -> None:
        nonlocal total_bytes, truncated
        total_bytes += len(raw_line)
        if total_bytes <= output_limit_bytes:
            text = raw_line.decode("utf-8", errors="replace")
            parts.append(text)
            on_chunk(stream, text)
        else:
            truncated = True

    assert process.stdout is not None
    assert process.stderr is not None
    stdout_stream = process.stdout
    stderr_stream = process.stderr

    async def read_stdout() -> None:
        async for raw_line in stdout_stream:
            record_line("stdout", raw_line, stdout_parts)

    async def read_stderr() -> None:
        async for raw_line in stderr_stream:
            record_line("stderr", raw_line, stderr_parts)

    exit_code = -1
    try:
        async with asyncio.timeout(float(timeout_seconds)):
            await asyncio.gather(read_stdout(), read_stderr())
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

    failure_category, termination_signal = classify_subprocess_failure(
        exit_code=exit_code,
        timed_out=timed_out,
    )
    return CapturedSubprocessOutput(
        exit_code=exit_code,
        stdout="".join(stdout_parts),
        stderr="".join(stderr_parts),
        truncated=truncated,
        timed_out=timed_out,
        failure_category=failure_category,
        termination_signal=termination_signal,
    )


def classify_subprocess_failure(
    *,
    exit_code: int,
    timed_out: bool,
) -> tuple[CommandFailureCategory | None, int | None]:
    """Classify subprocess termination for operator-facing summaries."""

    if timed_out:
        return "timed_out", _termination_signal_from_exit_code(exit_code)
    termination_signal = _termination_signal_from_exit_code(exit_code)
    if termination_signal is not None:
        return "interrupted", termination_signal
    if exit_code != 0:
        return "execution_error", None
    return None, None


def build_command_execution_envelope(
    *,
    workspace_root: Path,
    requested_cwd: str,
    resolved_cwd: Path,
    timeout_seconds: int,
    output_limit_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> CommandExecutionEnvelope:
    """Build a stable execution envelope for a workspace-scoped subprocess."""

    workspace_root = workspace_root.resolve(strict=False)
    resolved_cwd = resolved_cwd.resolve(strict=False)
    directory_policy: CommandDirectoryPolicy = "workspace_root"
    relative_resolved = "."
    if resolved_cwd != workspace_root:
        directory_policy = "workspace_subdirectory"
        relative_resolved = resolved_cwd.relative_to(workspace_root).as_posix()

    return CommandExecutionEnvelope(
        requested_cwd=requested_cwd,
        resolved_cwd=relative_resolved,
        directory_policy=directory_policy,
        timeout_seconds=timeout_seconds,
        output_limit_bytes=output_limit_bytes,
    )


def resolve_workspace_cwd(workspace_root: Path, relative_path: str) -> Path:
    """Resolve one workspace-relative directory and reject escapes."""

    if relative_path == ".":
        return workspace_root
    resolved = (workspace_root / relative_path).resolve(strict=False)
    if not resolved.is_relative_to(workspace_root):
        raise ValueError(
            f"working directory '{relative_path}' is outside workspace "
            f"'{workspace_root}'"
        )
    return resolved


def _termination_signal_from_exit_code(exit_code: int) -> int | None:
    if exit_code >= 0:
        return None
    return abs(exit_code)
