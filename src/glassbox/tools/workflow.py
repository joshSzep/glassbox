"""Workflow tools: git status, diff review, and test runner for sessions."""

import asyncio
import json
import re
import sys
from collections.abc import Awaitable
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools._subprocess import DEFAULT_MAX_OUTPUT_BYTES
from glassbox.tools._subprocess import CapturedSubprocessOutput
from glassbox.tools._subprocess import CommandExecutionResult
from glassbox.tools._subprocess import SubprocessCancellationController
from glassbox.tools._subprocess import build_command_execution_envelope
from glassbox.tools._subprocess import capture_streaming_subprocess
from glassbox.tools._subprocess import resolve_workspace_cwd
from glassbox.tools.command import build_command_tool_registry
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec
from glassbox.tools.registry import ToolStreamingMode
from glassbox.tools.test_discovery import TestDiscoveryTool
from glassbox.tools.test_discovery import TestTargetSelectionTool

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

        cwd = resolve_workspace_cwd(self._workspace_root, arguments.cwd)
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
# Diff summary tool
# ---------------------------------------------------------------------------

DIFF_SUMMARY_ARTIFACT_KIND = "workspace_diff_summary"

_POLICY_SENSITIVE_PATH_PREFIXES = (
    ".github/",
    "docs/tool-policy",
    "docs/tasks-v",
    "scripts/validate_",
    "src/glassbox/tools/policy",
    "src/glassbox/tools/policy_config",
)
_POLICY_SENSITIVE_PATH_NAMES = {
    ".env",
    ".env.local",
    ".envrc",
    "glassbox-policy.json",
    "glassbox.tool-policy.json",
}
_GENERATED_PATH_MARKERS = (
    "/__pycache__/",
    "/generated/",
    "/static_next/",
    "/node_modules/",
)
_GENERATED_PATH_PREFIXES = (
    "frontend/generated/",
    "src/glassbox/web/static_next/",
)


class DiffSummaryScope(StrEnum):
    """Supported git diff scopes for structured review."""

    WORKSPACE = "workspace"
    STAGED = "staged"
    UNSTAGED = "unstaged"


class DiffSummaryArgs(BaseModel):
    """Arguments for summarizing local git diffs without mutating state."""

    model_config = ConfigDict(extra="forbid")

    scope: DiffSummaryScope = Field(
        default=DiffSummaryScope.WORKSPACE,
        description=(
            "Diff scope: workspace compares HEAD to the working tree and includes "
            "untracked files, staged inspects the index, and unstaged inspects "
            "working-tree changes not yet staged."
        ),
    )
    paths: list[str] = Field(
        default_factory=list,
        description="Optional workspace-relative path filters.",
        max_length=100,
    )
    max_files: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum changed files to include in the structured summary.",
    )
    inline_file_limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description=(
            "Maximum file summaries to return inline before also preparing an "
            "artifact-sized JSON summary for event recording."
        ),
    )


class DiffFileSummary(BaseModel):
    """One file touched by a local diff."""

    model_config = ConfigDict(extra="forbid")

    path: str
    change_kind: str = "modified"
    insertions: int | None = None
    deletions: int | None = None
    binary: bool = False
    generated: bool = False
    test_file: bool = False
    docs_file: bool = False
    policy_sensitive: bool = False


class PatchRiskSummary(BaseModel):
    """Aggregated change-risk cues for operators and verification loops."""

    model_config = ConfigDict(extra="forbid")

    touched_files: int = 0
    insertions: int = 0
    deletions: int = 0
    binary_files: int = 0
    generated_files: list[str] = Field(default_factory=list)
    tests_touched: list[str] = Field(default_factory=list)
    docs_touched: list[str] = Field(default_factory=list)
    policy_sensitive_paths: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)


class DiffSummaryArtifact(BaseModel):
    """Artifact-ready payload for large structured diff summaries."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: str = DIFF_SUMMARY_ARTIFACT_KIND
    scope: DiffSummaryScope
    path_filters: list[str]
    risk_summary: PatchRiskSummary
    files: list[DiffFileSummary]
    redaction: str = "summary-only-no-raw-diff"


class DiffSummaryResult(BaseModel):
    """Structured read-only summary of local git changes."""

    model_config = ConfigDict(extra="forbid")

    scope: DiffSummaryScope
    path_filters: list[str] = Field(default_factory=list)
    clean: bool = False
    files: list[DiffFileSummary] = Field(default_factory=list)
    truncated: bool = False
    risk_summary: PatchRiskSummary = Field(default_factory=PatchRiskSummary)
    artifact_required: bool = False
    artifact_kind: str | None = None
    artifact_payload: DiffSummaryArtifact | None = None
    error: str | None = None


class DiffSummaryTool:
    """Summarize local git diffs without mutating git or workspace files."""

    spec = ToolSpec(
        name="workspace_diff_summary",
        description=(
            "Summarize local git changes as structured patch-risk evidence. "
            "The tool is read-only and never mutates git state."
        ),
        input_model=DiffSummaryArgs,
        output_model=DiffSummaryResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("paths",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: DiffSummaryArgs) -> DiffSummaryResult:
        """Return a structured summary for the requested local diff scope."""

        path_filters = _normalize_path_filters(self._workspace_root, arguments.paths)
        numstat_result = await _run_git_capture(
            self._workspace_root,
            _diff_numstat_command(arguments.scope, path_filters),
        )
        if numstat_result[0] != 0:
            return DiffSummaryResult(
                scope=arguments.scope,
                path_filters=path_filters,
                error=numstat_result[2] or f"git diff exited with {numstat_result[0]}",
            )

        files = _parse_diff_numstat(numstat_result[1])
        if arguments.scope == DiffSummaryScope.WORKSPACE:
            untracked = await _list_untracked_files(self._workspace_root, path_filters)
            files.extend(_summarize_untracked_files(self._workspace_root, untracked))

        files = sorted(_dedupe_file_summaries(files), key=lambda item: item.path)
        truncated = len(files) > arguments.max_files
        bounded_files = files[: arguments.max_files]
        risk_summary = _build_patch_risk_summary(bounded_files)
        inline_files = bounded_files[: arguments.inline_file_limit]
        artifact_required = truncated or len(bounded_files) > len(inline_files)
        artifact_payload = (
            DiffSummaryArtifact(
                scope=arguments.scope,
                path_filters=path_filters,
                risk_summary=risk_summary,
                files=bounded_files,
            )
            if artifact_required
            else None
        )

        return DiffSummaryResult(
            scope=arguments.scope,
            path_filters=path_filters,
            clean=not bounded_files,
            files=inline_files,
            truncated=truncated,
            risk_summary=risk_summary,
            artifact_required=artifact_required,
            artifact_kind=DIFF_SUMMARY_ARTIFACT_KIND if artifact_required else None,
            artifact_payload=artifact_payload,
        )


async def _run_git_capture(
    cwd: Path,
    command: list[str],
    *,
    timeout: float = 10.0,
) -> tuple[int, str, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except FileNotFoundError:
        return 127, "", "git executable not found"
    except TimeoutError:
        return 124, "", "git command timed out"
    return (
        process.returncode or 0,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace").strip(),
    )


def _diff_numstat_command(
    scope: DiffSummaryScope,
    path_filters: list[str],
) -> list[str]:
    command = ["git", "diff", "--numstat"]
    if scope == DiffSummaryScope.WORKSPACE:
        command.append("HEAD")
    elif scope == DiffSummaryScope.STAGED:
        command.append("--cached")
    command.append("--")
    command.extend(path_filters)
    return command


def _parse_diff_numstat(output: str) -> list[DiffFileSummary]:
    files: list[DiffFileSummary] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        insertions_raw, deletions_raw, raw_path = parts[0], parts[1], parts[-1]
        binary = insertions_raw == "-" or deletions_raw == "-"
        path = _normalize_git_path(raw_path)
        files.append(
            _annotate_diff_file(
                path,
                change_kind="modified",
                insertions=None if binary else int(insertions_raw),
                deletions=None if binary else int(deletions_raw),
                binary=binary,
            )
        )
    return files


async def _list_untracked_files(
    workspace_root: Path,
    path_filters: list[str],
) -> list[str]:
    command = ["git", "ls-files", "--others", "--exclude-standard", "--"]
    command.extend(path_filters)
    exit_code, stdout, _stderr = await _run_git_capture(workspace_root, command)
    if exit_code != 0:
        return []
    return [_normalize_git_path(line) for line in stdout.splitlines() if line.strip()]


def _summarize_untracked_files(
    workspace_root: Path,
    paths: list[str],
) -> list[DiffFileSummary]:
    summaries: list[DiffFileSummary] = []
    for path in paths:
        file_path = workspace_root / path
        insertions, binary = _untracked_file_insertions(file_path)
        summaries.append(
            _annotate_diff_file(
                path,
                change_kind="untracked",
                insertions=insertions,
                deletions=0 if not binary else None,
                binary=binary,
            )
        )
    return summaries


def _untracked_file_insertions(path: Path) -> tuple[int | None, bool]:
    try:
        content = path.read_bytes()
    except OSError:
        return None, True
    if b"\x00" in content:
        return None, True
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None, True
    return len(text.splitlines()), False


def _normalize_path_filters(workspace_root: Path, raw_paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        resolved = (
            candidate.resolve(strict=False)
            if candidate.is_absolute()
            else (workspace_root / candidate).resolve(strict=False)
        )
        try:
            relative = resolved.relative_to(workspace_root)
        except ValueError as exc:
            raise ValueError(f"path filter is outside workspace: {raw_path}") from exc
        normalized.append("." if relative == Path() else relative.as_posix())
    return normalized


def _normalize_git_path(raw_path: str) -> str:
    if " => " in raw_path:
        return raw_path.split(" => ", maxsplit=1)[1].replace("{", "").replace("}", "")
    return raw_path


def _dedupe_file_summaries(files: list[DiffFileSummary]) -> list[DiffFileSummary]:
    deduped: dict[str, DiffFileSummary] = {}
    for file_summary in files:
        deduped[file_summary.path] = file_summary
    return list(deduped.values())


def _annotate_diff_file(
    path: str,
    *,
    change_kind: str,
    insertions: int | None,
    deletions: int | None,
    binary: bool,
) -> DiffFileSummary:
    return DiffFileSummary(
        path=path,
        change_kind=change_kind,
        insertions=insertions,
        deletions=deletions,
        binary=binary,
        generated=_is_generated_path(path),
        test_file=_is_test_path(path),
        docs_file=_is_docs_path(path),
        policy_sensitive=_is_policy_sensitive_path(path),
    )


def _build_patch_risk_summary(files: list[DiffFileSummary]) -> PatchRiskSummary:
    return PatchRiskSummary(
        touched_files=len(files),
        insertions=sum(file.insertions or 0 for file in files),
        deletions=sum(file.deletions or 0 for file in files),
        binary_files=sum(1 for file in files if file.binary),
        generated_files=[file.path for file in files if file.generated],
        tests_touched=[file.path for file in files if file.test_file],
        docs_touched=[file.path for file in files if file.docs_file],
        policy_sensitive_paths=[file.path for file in files if file.policy_sensitive],
        untracked_files=[
            file.path for file in files if file.change_kind == "untracked"
        ],
    )


def _is_generated_path(path: str) -> bool:
    normalized = f"/{path}"
    return path.startswith(_GENERATED_PATH_PREFIXES) or any(
        marker in normalized for marker in _GENERATED_PATH_MARKERS
    )


def _is_test_path(path: str) -> bool:
    name = Path(path).name
    return (
        path.startswith("tests/")
        or "/tests/" in path
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
    )


def _is_docs_path(path: str) -> bool:
    return path.startswith("docs/") or Path(path).suffix.lower() in {".md", ".rst"}


def _is_policy_sensitive_path(path: str) -> bool:
    name = Path(path).name
    return name in _POLICY_SENSITIVE_PATH_NAMES or path.startswith(
        _POLICY_SENSITIVE_PATH_PREFIXES
    )


def diff_summary_artifact_content(output_payload: dict[str, object]) -> str | None:
    """Return artifact JSON content for a large diff summary tool result."""

    artifact_payload = output_payload.get("artifact_payload")
    if not isinstance(artifact_payload, dict):
        return None
    artifact_payload = cast(dict[str, object], artifact_payload)
    if artifact_payload.get("artifact_kind") != DIFF_SUMMARY_ARTIFACT_KIND:
        return None
    return json.dumps(artifact_payload, indent=2, sort_keys=True) + "\n"


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


class RunTestsResult(CommandExecutionResult):
    """Structured result from one pytest invocation."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    warnings: int = 0


class RunTestsSubprocessRunner(Protocol):
    """Subprocess execution seam for pytest-runner tests."""

    def __call__(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
        on_chunk: Callable[[str, str], None],
        output_limit_bytes: int,
        cancellation_controller: SubprocessCancellationController | None,
    ) -> Awaitable[CapturedSubprocessOutput]: ...


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

    def __init__(
        self,
        workspace_root: Path,
        *,
        subprocess_runner: RunTestsSubprocessRunner | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)
        self._subprocess_runner = subprocess_runner or _run_exec_subprocess

    async def execute(self, arguments: RunTestsArgs) -> RunTestsResult:
        """Run tests; streaming output is discarded."""

        return await self.execute_streaming(arguments, lambda _stream, _chunk: None)

    async def execute_streaming(
        self,
        arguments: RunTestsArgs,
        on_chunk: Callable[[str, str], None],
        *,
        cancellation_controller: SubprocessCancellationController | None = None,
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
        envelope = build_command_execution_envelope(
            workspace_root=self._workspace_root,
            requested_cwd=".",
            resolved_cwd=self._workspace_root,
            timeout_seconds=arguments.timeout,
            output_limit_bytes=DEFAULT_MAX_OUTPUT_BYTES,
        )

        captured = await self._subprocess_runner(
            cmd,
            cwd=self._workspace_root,
            timeout_seconds=arguments.timeout,
            on_chunk=on_chunk,
            output_limit_bytes=DEFAULT_MAX_OUTPUT_BYTES,
            cancellation_controller=cancellation_controller,
        )

        stdout_text = captured.stdout
        stderr_text = captured.stderr
        counts = _parse_pytest_summary(stdout_text + stderr_text)

        return RunTestsResult(
            passed=counts.get("passed", 0),
            failed=counts.get("failed", 0),
            errors=counts.get("error", 0),
            warnings=counts.get("warning", 0),
            exit_code=captured.exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            truncated=captured.truncated,
            timed_out=captured.timed_out,
            cancelled=captured.cancelled,
            execution_envelope=envelope,
            failure_category=captured.failure_category,
            termination_signal=captured.termination_signal,
        )


async def _run_exec_subprocess(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    on_chunk: Callable[[str, str], None],
    output_limit_bytes: int,
    cancellation_controller: SubprocessCancellationController | None,
) -> CapturedSubprocessOutput:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        start_new_session=True,
    )
    return await capture_streaming_subprocess(
        process,
        timeout_seconds=timeout_seconds,
        on_chunk=on_chunk,
        output_limit_bytes=output_limit_bytes,
        cancellation_controller=cancellation_controller,
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
    registry.register(DiffSummaryTool(workspace_root))
    registry.register(TestDiscoveryTool(workspace_root))
    registry.register(TestTargetSelectionTool(workspace_root))
    registry.register(RunTestsTool(workspace_root))
    return registry
