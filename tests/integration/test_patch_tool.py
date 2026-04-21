"""Integration tests for the apply_patch tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    build_patch_tool_registry,
)
from glassbox.tools.patch import ApplyPatchArgs, ApplyPatchTool

# ---------------------------------------------------------------------------
# Targeted replacement (old_text non-empty)
# ---------------------------------------------------------------------------


def test_apply_patch_replaces_exact_match(tmp_path: Path) -> None:
    target = tmp_path / "hello.py"
    target.write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="hello.py", old_text="y = 2\n", new_text="y = 42\n")
        )
        assert result.success is True
        assert result.error is None
        assert target.read_text(encoding="utf-8") == "x = 1\ny = 42\nz = 3\n"

    asyncio.run(scenario())


def test_apply_patch_returns_unified_diff(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_text("hello world\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="f.txt", old_text="hello", new_text="goodbye")
        )
        assert result.success is True
        assert result.diff is not None
        assert "--- a/f.txt" in result.diff
        assert "+++ b/f.txt" in result.diff
        assert "-hello world" in result.diff
        assert "+goodbye world" in result.diff

    asyncio.run(scenario())


def test_apply_patch_errors_when_old_text_not_found(tmp_path: Path) -> None:
    target = tmp_path / "src.py"
    target.write_text("a = 1\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="src.py", old_text="missing text", new_text="x")
        )
        assert result.success is False
        assert "not found" in (result.error or "")
        # File must not have been modified
        assert target.read_text(encoding="utf-8") == "a = 1\n"

    asyncio.run(scenario())


def test_apply_patch_errors_on_ambiguous_match(tmp_path: Path) -> None:
    target = tmp_path / "dup.txt"
    target.write_text("foo\nfoo\nbar\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="dup.txt", old_text="foo", new_text="baz")
        )
        assert result.success is False
        assert result.error is not None
        assert "2" in result.error
        # File must not have been modified
        assert target.read_text(encoding="utf-8") == "foo\nfoo\nbar\n"

    asyncio.run(scenario())


def test_apply_patch_errors_when_file_missing_and_old_text_set(tmp_path: Path) -> None:
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="ghost.py", old_text="something", new_text="x")
        )
        assert result.success is False
        assert "not found" in (result.error or "")

    asyncio.run(scenario())


def test_apply_patch_only_replaces_first_occurrence(tmp_path: Path) -> None:
    """With exactly one occurrence the targeted path must work correctly."""

    target = tmp_path / "once.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="once.txt", old_text="beta\n", new_text="BETA\n")
        )
        assert result.success is True
        assert target.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Full-overwrite mode (old_text == "")
# ---------------------------------------------------------------------------


def test_apply_patch_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("old content\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="data.txt", old_text="", new_text="new content\n")
        )
        assert result.success is True
        assert target.read_text(encoding="utf-8") == "new content\n"

    asyncio.run(scenario())


def test_apply_patch_creates_new_file(tmp_path: Path) -> None:
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="new_dir/new_file.py", old_text="", new_text="x = 1\n")
        )
        assert result.success is True
        created = tmp_path / "new_dir" / "new_file.py"
        assert created.exists()
        assert created.read_text(encoding="utf-8") == "x = 1\n"

    asyncio.run(scenario())


def test_apply_patch_overwrite_diff_is_empty_when_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "same.txt"
    target.write_text("content\n", encoding="utf-8")
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        result = await tool.execute(
            ApplyPatchArgs(path="same.txt", old_text="", new_text="content\n")
        )
        assert result.success is True
        assert result.diff == ""

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Workspace scope enforcement
# ---------------------------------------------------------------------------


def test_apply_patch_rejects_path_outside_workspace(tmp_path: Path) -> None:
    tool = ApplyPatchTool(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await tool.execute(
                ApplyPatchArgs(
                    path="../../../etc/passwd", old_text="", new_text="hacked"
                )
            )

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Registry contents
# ---------------------------------------------------------------------------


def test_build_patch_tool_registry_includes_all_tools(tmp_path: Path) -> None:
    registry = build_patch_tool_registry(tmp_path)
    tool_names = {tool.spec.name for tool in registry.list_tools()}
    assert tool_names == {
        "list_dir",
        "read_file",
        "search_files",
        "run_command",
        "git_status",
        "run_tests",
        "apply_patch",
    }


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------


def test_apply_patch_requires_approval_in_confirm_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.CONFIRM
    )
    registry = build_patch_tool_registry(tmp_path)
    tool = registry.require("apply_patch")
    decision = engine.evaluate(
        tool.spec,
        arguments=ApplyPatchArgs(path="f.py", old_text="x", new_text="y"),
        context=context,
    )

    assert decision.requires_approval is True
    assert decision.allowed is True


def test_apply_patch_blocked_in_never_mode(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.NEVER
    )
    registry = build_patch_tool_registry(tmp_path)
    tool = registry.require("apply_patch")
    decision = engine.evaluate(
        tool.spec,
        arguments=ApplyPatchArgs(path="f.py", old_text="x", new_text="y"),
        context=context,
    )

    assert decision.allowed is False


def test_apply_patch_blocked_for_out_of_scope_path(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    context = ToolPolicyContext(
        workspace_root=tmp_path, approval_mode=ApprovalMode.CONFIRM
    )
    registry = build_patch_tool_registry(tmp_path)
    tool = registry.require("apply_patch")
    decision = engine.evaluate(
        tool.spec,
        arguments=ApplyPatchArgs(
            path="../../../etc/passwd", old_text="", new_text="hacked"
        ),
        context=context,
    )

    assert decision.allowed is False
    assert "outside workspace" in (decision.reason or "")
