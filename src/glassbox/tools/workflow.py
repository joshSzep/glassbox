"""Workflow tools: git status and test runner for Glassbox sessions."""

from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.command import build_command_tool_registry
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec
from glassbox.tools.registry import ToolStreamingMode

_MAX_OUTPUT_BYTES = 100 * 1024  # 100 KB cap before truncation

# ---------------------------------------------------------------------------
# Git status tool
# ---------------------------------------------------------------------------

_NO_COMMITS_RE = re.compile(r"^## No commits yet on (.+)$")
_BRANCH_REMOTE_RE = re.compile(r"^## (.+?)\.{3}(.+?)(?:\s+\[(.+)\])?$")
_BRANCH_LOCAL_RE = re.compile(r"^## (.+)$")
_AHEAD_BEHIND_RE = re.compile(r"ahead (\d+)|behind (\d+)")


class GitStatusArgs(BaseModel):
    """Arguments for inspecting git status of the workspace."""

    model_config = ConfigDict(extra="forbid")

    cwd: str = Field(
        default=".",
        description="Working directory relative to the workspace root.",
    )


class GitStatusResult(BaseModel):
    """Structured result from one git status invocation."""

    model_config = ConfigDict(extra="forbid")

    branch: str | None = None
    ahead: int = 0
    behind: int = 0
    staged: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    untracked: list[str] = Field(default_factory=list)
    clean: bool = False
    error: str | None = None


class GitStatusTool:
    """Inspect git status and return structured repo state."""

    spec = ToolSpec(
        name="git_status",
        description=(
            "Get the current git status of the workspace: branch name, "
            "staged files, modified files, and untracked files."
        ),
        input_model=GitStatusArgs,
        output_model=GitStatusResult,
        risk_level=ToolRiskLevel.READ_ONLY,
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: GitStatusArgs) -> GitStatusResult:
        """Run git status and return structured output."""

        cwd = _resolve_workspace_cwd(self._workspace_root, arguments.cwd)
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "status",
                "--porcelain=v1",
                "-b",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=10.0
            )
        except FileNotFoundError:
            return GitStatusResult(error="git executable not found")
        except TimeoutError:
            return GitStatusResult(error="git status timed out")

        if process.returncode != 0:
            error_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
            return GitStatusResult(
                error=error_msg or f"git exited with code {process.returncode}"
            )

        return _parse_porcelain_output(stdout_bytes.decode("utf-8", errors="replace"))


def _parse_porcelain_output(output: str) -> GitStatusResult:
    """Parse `git status --porcelain=v1 -b` output into a GitStatusResult."""

    lines = output.splitlines()
    branch: str | None = None
    ahead = 0
    behind = 0
    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []

    for line in lines:
        if line.startswith("## "):
            m = _NO_COMMITS_RE.match(line)
            if m:
                branch = m.group(1).strip()
                continue
            m = _BRANCH_REMOTE_RE.match(line)
            if m:
                branch = m.group(1).strip()
                ab_text = m.group(3) or ""
                for ab_m in _AHEAD_BEHIND_RE.finditer(ab_text):
                    if ab_m.group(1):
                        ahead = int(ab_m.group(1))
                    if ab_m.group(2):
                        behind = int(ab_m.group(2))
                continue
            m = _BRANCH_LOCAL_RE.match(line)
            if m:
                branch = m.group(1).strip()
            continue

        if len(line) < 4:
            continue

        xy = line[:2]
        path = line[3:]

        if xy == "??":
            untracked.append(path)
        else:
            x = xy[0]  # index (staged) status
            y = xy[1]  # worktree (unstaged) status
            if x not in (" ", "?"):
                staged.append(path)
            if y not in (" ", "?"):
                modified.append(path)

    clean = not staged and not modified and not untracked
    return GitStatusResult(
        branch=branch,
        ahead=ahead,
        behind=behind,
        staged=staged,
        modified=modified,
        untracked=untracked,
        clean=clean,
    )


# ---------------------------------------------------------------------------
# Run tests tool
# ---------------------------------------------------------------------------

_PYTEST_SUMMARY_RE = re.compile(r"(\d+)\s+(passed|failed|error|warning)")


class RunTestsArgs(BaseModel):
    """Arguments for running pytest in the workspace."""

    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(
        default_factory=list,
        description=(
            "Test paths or files to run relative to the workspace root. "
            "Empty list runs the full test suite."
        ),
    )
    keywords: str | None = Field(
        default=None,
        description="Pytest -k expression to filter tests by keyword.",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Maximum seconds to wait before killing the test run.",
    )


class RunTestsResult(BaseModel):
    """Structured result from one pytest invocation."""

    model_config = ConfigDict(extra="forbid")

    passed: int = 0
    failed: int = 0
    errors: int = 0
    warnings: int = 0
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    timed_out: bool = False


class RunTestsTool:
    """Run pytest in the workspace with constrained arguments."""

    spec = ToolSpec(
        name="run_tests",
        description=(
            "Run pytest in the workspace. Paths can target specific test files "
            "or directories; an empty list runs the full test suite."
        ),
        input_model=RunTestsArgs,
        output_model=RunTestsResult,
        risk_level=ToolRiskLevel.COMMAND,
        streaming_mode=ToolStreamingMode.TEXT,
        path_argument_names=("paths",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: RunTestsArgs) -> RunTestsResult:
        """Run tests; streaming output is discarded."""

        return await self.execute_streaming(arguments, lambda _stream, _chunk: None)

    async def execute_streaming(
        self,
        arguments: RunTestsArgs,
        on_chunk: Callable[[str, str], None],
    ) -> RunTestsResult:
        """Run tests and deliver each output line to on_chunk."""

        for p in arguments.paths:
            resolved = (self._workspace_root / p).resolve(strict=False)
            if not resolved.is_relative_to(self._workspace_root):
                raise ValueError(
                    f"test path '{p}' is outside workspace '{self._workspace_root}'"
                )

        cmd = [sys.executable, "-m", "pytest", "--tb=short", "-q"]
        if arguments.keywords:
            cmd.extend(["-k", arguments.keywords])
        cmd.extend(arguments.paths)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._workspace_root,
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

        stdout_text = "".join(stdout_parts)
        stderr_text = "".join(stderr_parts)
        counts = _parse_pytest_summary(stdout_text + stderr_text)

        return RunTestsResult(
            passed=counts.get("passed", 0),
            failed=counts.get("failed", 0),
            errors=counts.get("error", 0),
            warnings=counts.get("warning", 0),
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            truncated=truncated,
            timed_out=timed_out,
        )


def _parse_pytest_summary(output: str) -> dict[str, int]:
    """Extract pass/fail/error/warning counts from pytest summary line."""

    counts: dict[str, int] = {}
    for m in _PYTEST_SUMMARY_RE.finditer(output):
        counts[m.group(2)] = int(m.group(1))
    return counts


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_workflow_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build a tool registry with all tools including git status and test runner."""

    registry = build_command_tool_registry(workspace_root)
    registry.register(GitStatusTool(workspace_root))
    registry.register(RunTestsTool(workspace_root))
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
