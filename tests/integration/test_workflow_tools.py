"""Integration tests for the git status and run tests workflow tools."""

import asyncio
import subprocess
from pathlib import Path

import pytest

from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import build_workflow_tool_registry
from glassbox.tools.workflow import DIFF_SUMMARY_ARTIFACT_KIND
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool
from glassbox.tools.workflow import GitStatusArgs
from glassbox.tools.workflow import GitStatusTool
from glassbox.tools.workflow import RunTestsArgs
from glassbox.tools.workflow import RunTestsTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialise a minimal git repo with a first commit at path."""

    subprocess.run(
        ["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    # Initial commit so HEAD exists
    (path / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# GitStatusTool tests
# ---------------------------------------------------------------------------


def test_git_status_returns_branch_name(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is None
        assert result.branch == "main"

    asyncio.run(scenario())


def test_git_status_clean_after_initial_commit(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is None
        assert result.clean is True
        assert result.staged == []
        assert result.modified == []
        assert result.untracked == []

    asyncio.run(scenario())


def test_git_status_detects_untracked_files(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "new_file.py").write_text("# new\n", encoding="utf-8")
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is None
        assert "new_file.py" in result.untracked
        assert result.clean is False

    asyncio.run(scenario())


def test_git_status_detects_modified_files(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("changed\n", encoding="utf-8")
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is None
        assert "README.md" in result.modified
        assert result.clean is False

    asyncio.run(scenario())


def test_git_status_detects_staged_files(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "staged.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "staged.py"], cwd=tmp_path, check=True, capture_output=True
    )
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is None
        assert "staged.py" in result.staged
        assert result.clean is False

    asyncio.run(scenario())


def test_git_status_handles_non_git_directory(tmp_path: Path) -> None:
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(GitStatusArgs())
        assert result.error is not None

    asyncio.run(scenario())


def test_git_status_rejects_out_of_scope_cwd(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tool = GitStatusTool(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await tool.execute(GitStatusArgs(cwd="../"))

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# DiffSummaryTool tests
# ---------------------------------------------------------------------------


def test_diff_summary_reports_workspace_patch_risk(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\nchanged\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_new.py").write_text(
        "def test_new():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(DiffSummaryArgs())
        assert result.error is None
        assert result.clean is False
        assert result.scope == DiffSummaryScope.WORKSPACE
        assert result.risk_summary.touched_files == 3
        assert "tests/test_new.py" in result.risk_summary.tests_touched
        assert "docs/guide.md" in result.risk_summary.docs_touched
        assert "tests/test_new.py" in result.risk_summary.untracked_files

    asyncio.run(scenario())


def test_diff_summary_reports_staged_changes_only(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("staged\n", encoding="utf-8")
    (tmp_path / "later.md").write_text("unstaged\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(DiffSummaryArgs(scope=DiffSummaryScope.STAGED))
        assert result.error is None
        assert [file.path for file in result.files] == ["README.md"]
        assert result.risk_summary.docs_touched == ["README.md"]

    asyncio.run(scenario())


def test_diff_summary_applies_path_filters(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("changed\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("print('new')\n", encoding="utf-8")
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(DiffSummaryArgs(paths=["README.md"]))
        assert result.error is None
        assert [file.path for file in result.files] == ["README.md"]

    asyncio.run(scenario())


def test_diff_summary_rejects_out_of_scope_path_filter(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await tool.execute(DiffSummaryArgs(paths=["../outside"]))

    asyncio.run(scenario())


def test_diff_summary_reports_binary_and_policy_sensitive_paths(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "asset.bin").write_bytes(b"\x00\x01changed")
    (tmp_path / "glassbox-policy.json").write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "binary"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "asset.bin").write_bytes(b"\x00\x02changed")
    (tmp_path / "glassbox-policy.json").write_text('{"rules":[]}\n', encoding="utf-8")
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(DiffSummaryArgs())
        assert result.error is None
        assert result.risk_summary.binary_files == 1
        assert "glassbox-policy.json" in result.risk_summary.policy_sensitive_paths

    asyncio.run(scenario())


def test_diff_summary_prepares_artifact_payload_for_large_summary(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    for index in range(4):
        (tmp_path / f"file_{index}.py").write_text(
            f"value = {index}\n", encoding="utf-8"
        )
    tool = DiffSummaryTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(DiffSummaryArgs(inline_file_limit=2))
        assert result.error is None
        assert result.artifact_required is True
        assert result.artifact_kind == DIFF_SUMMARY_ARTIFACT_KIND
        assert result.artifact_payload is not None
        assert len(result.files) == 2
        assert len(result.artifact_payload.files) == 4
        assert result.artifact_payload.redaction == "summary-only-no-raw-diff"

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# RunTestsTool tests
# ---------------------------------------------------------------------------


def _write_passing_test(path: Path, name: str = "test_pass.py") -> Path:
    test_file = path / name
    test_file.write_text("def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    return test_file


def _write_failing_test(path: Path, name: str = "test_fail.py") -> Path:
    test_file = path / name
    test_file.write_text("def test_bad():\n    assert False\n", encoding="utf-8")
    return test_file


def test_run_tests_passes_on_simple_test(tmp_path: Path) -> None:
    test_file = _write_passing_test(tmp_path)
    tool = RunTestsTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunTestsArgs(paths=[test_file.name]))
        assert result.passed == 1
        assert result.failed == 0
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.failure_category is None
        assert result.execution_envelope.resolved_cwd == "."

    asyncio.run(scenario())


def test_run_tests_captures_failure(tmp_path: Path) -> None:
    test_file = _write_failing_test(tmp_path)
    tool = RunTestsTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunTestsArgs(paths=[test_file.name]))
        assert result.failed == 1
        assert result.exit_code != 0
        assert result.failure_category == "execution_error"

    asyncio.run(scenario())


def test_run_tests_streams_output_chunks(tmp_path: Path) -> None:
    test_file = _write_passing_test(tmp_path)
    tool = RunTestsTool(tmp_path)
    collected: list[tuple[str, str]] = []

    async def scenario() -> None:
        result = await tool.execute_streaming(
            RunTestsArgs(paths=[test_file.name]),
            on_chunk=lambda stream, chunk: collected.append((stream, chunk)),
        )
        assert result.exit_code == 0

    asyncio.run(scenario())
    assert len(collected) > 0
    assert all(stream in ("stdout", "stderr") for stream, _ in collected)


def test_run_tests_keyword_filter(tmp_path: Path) -> None:
    (tmp_path / "test_kw.py").write_text(
        "def test_alpha():\n    assert True\n\ndef test_beta():\n    assert True\n",
        encoding="utf-8",
    )
    tool = RunTestsTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            RunTestsArgs(paths=["test_kw.py"], keywords="alpha")
        )
        assert result.passed == 1
        assert result.exit_code == 0

    asyncio.run(scenario())


def test_run_tests_times_out(tmp_path: Path) -> None:
    (tmp_path / "test_slow.py").write_text(
        "import time\ndef test_slow():\n    time.sleep(60)\n",
        encoding="utf-8",
    )
    tool = RunTestsTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(RunTestsArgs(paths=["test_slow.py"], timeout=2))
        assert result.timed_out is True
        assert result.failure_category == "timed_out"

    asyncio.run(scenario())


def test_run_tests_rejects_out_of_scope_path(tmp_path: Path) -> None:
    tool = RunTestsTool(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await tool.execute(RunTestsArgs(paths=["../other"]))

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Registry contents
# ---------------------------------------------------------------------------


def test_build_workflow_tool_registry_includes_all_tools(tmp_path: Path) -> None:
    registry = build_workflow_tool_registry(tmp_path)
    tool_names = {tool.spec.name for tool in registry.list_tools()}
    assert tool_names == {
        "list_dir",
        "read_file",
        "search_files",
        "run_command",
        "git_status",
        "workspace_diff_summary",
        "run_tests",
    }


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------


def test_git_status_allowed_without_approval(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.NEVER
    )
    registry = build_workflow_tool_registry(tmp_path)
    tool = registry.require("git_status")
    decision = engine.evaluate(tool.spec, arguments=GitStatusArgs(), context=context)

    assert decision.allowed is True
    assert decision.requires_approval is False


def test_diff_summary_allowed_without_approval(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.NEVER
    )
    registry = build_workflow_tool_registry(tmp_path)
    tool = registry.require("workspace_diff_summary")
    decision = engine.evaluate(tool.spec, arguments=DiffSummaryArgs(), context=context)

    assert decision.allowed is True
    assert decision.requires_approval is False


def test_run_tests_requires_approval_in_confirm_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.CONFIRM
    )
    registry = build_workflow_tool_registry(tmp_path)
    tool = registry.require("run_tests")
    decision = engine.evaluate(tool.spec, arguments=RunTestsArgs(), context=context)

    assert decision.requires_approval is True
    assert decision.allowed is True


def test_run_tests_blocked_in_never_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.NEVER
    )
    registry = build_workflow_tool_registry(tmp_path)
    tool = registry.require("run_tests")
    decision = engine.evaluate(tool.spec, arguments=RunTestsArgs(), context=context)

    assert decision.allowed is False
