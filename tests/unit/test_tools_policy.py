"""Unit tests for local tool policy evaluation."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from glassbox.tools import DEFAULT_TOOL_POLICY_PATH
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolPolicyManifest
from glassbox.tools import ToolPolicyRule
from glassbox.tools import ToolRegistry
from glassbox.tools import ToolRiskLevel
from glassbox.tools import ToolSpec
from glassbox.tools import load_tool_policy_manifest


class ReadFileArgs(BaseModel):
    path: str


class ReadFileResult(BaseModel):
    content: str


class WriteFileArgs(BaseModel):
    path: str
    content: str


class WriteFileResult(BaseModel):
    bytes_written: int


class RunCommandArgs(BaseModel):
    command: str
    cwd: str | None = None


class RunCommandResult(BaseModel):
    summary: str


class ReadFileTool:
    spec = ToolSpec(
        name="read_file",
        description="Read a file from the workspace.",
        input_model=ReadFileArgs,
        output_model=ReadFileResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("path",),
    )

    async def execute(self, arguments: ReadFileArgs) -> ReadFileResult:
        return ReadFileResult(content=arguments.path)


class WriteFileTool:
    spec = ToolSpec(
        name="write_file",
        description="Write a file inside the workspace.",
        input_model=WriteFileArgs,
        output_model=WriteFileResult,
        risk_level=ToolRiskLevel.WORKSPACE_WRITE,
        path_argument_names=("path",),
    )

    async def execute(self, arguments: WriteFileArgs) -> WriteFileResult:
        return WriteFileResult(bytes_written=len(arguments.content))


class RunCommandTool:
    spec = ToolSpec(
        name="run_command",
        description="Run a shell command.",
        input_model=RunCommandArgs,
        output_model=RunCommandResult,
        risk_level=ToolRiskLevel.COMMAND,
        path_argument_names=("cwd",),
        command_argument_name="command",
    )

    async def execute(self, arguments: RunCommandArgs) -> RunCommandResult:
        return RunCommandResult(summary=arguments.command)


def test_policy_allows_read_only_tool_inside_workspace_without_approval() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        ReadFileTool.spec,
        arguments=ReadFileArgs(path="src/glassbox/__init__.py"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.reason == "allowed: read-only tool within workspace scope"
    assert decision.outcome == "allow"
    assert decision.risk_level == "read_only"
    assert decision.source_kind == "default"
    assert decision.source_label == "read_only"


def test_policy_requires_approval_for_workspace_write_in_confirm_mode() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "workspace write inside workspace scope" in decision.reason
    assert decision.outcome == "approve"
    assert decision.risk_level == "workspace_write"
    assert decision.source_kind == "default"


def test_policy_blocks_workspace_write_when_approval_mode_is_never() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.NEVER,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "approval mode is never" in decision.reason
    assert decision.outcome == "blocked"
    assert decision.risk_level == "workspace_write"


def test_policy_blocks_out_of_scope_path_requests() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        ReadFileTool.spec,
        arguments=ReadFileArgs(path="../secrets.txt"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert "outside workspace" in decision.reason
    assert decision.outcome == "blocked"
    assert decision.source_kind == "invariant"
    assert decision.source_label == "workspace_scope"


def test_policy_blocks_destructive_commands() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="rm -rf build", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert decision.reason == "blocked: destructive command pattern is not allowed"
    assert decision.outcome == "blocked"
    assert decision.risk_level == "command"
    assert decision.source_kind == "invariant"
    assert decision.source_label == "destructive_command"


def test_policy_evaluates_registered_tools_consistently() -> None:
    engine = ToolPolicyEngine()
    registry = ToolRegistry([RunCommandTool()])

    decision = engine.evaluate_registered(
        registry,
        "run_command",
        arguments=RunCommandArgs(command="git status", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "command execution is gated by local policy" in decision.reason
    assert decision.outcome == "approve"
    assert decision.risk_level == "command"
    assert decision.source_kind == "default"


def test_load_tool_policy_manifest_returns_defaults_when_missing(
    tmp_path: Path,
) -> None:
    manifest = load_tool_policy_manifest(tmp_path)

    assert manifest == ToolPolicyManifest()


def test_load_tool_policy_manifest_rejects_invalid_config(tmp_path: Path) -> None:
    (tmp_path / DEFAULT_TOOL_POLICY_PATH).write_text(
        (
            '{"manifest_version": 1, "rules": '
            '[{"tool_name": "run_command", "action": "ask"}]}'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid tool policy manifest"):
        load_tool_policy_manifest(tmp_path)


def test_policy_rule_can_allow_workspace_write_without_approval(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="docs/notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.NEVER,
            policy_manifest=ToolPolicyManifest(
                rules=[
                    ToolPolicyRule(
                        rule_id="allow-docs-write",
                        tool_name="write_file",
                        action="allow",
                        path_prefixes=["docs"],
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert "allow-docs-write" in decision.reason
    assert decision.outcome == "allow"
    assert decision.source_kind == "rule"
    assert decision.source_label == "allow-docs-write"


def test_policy_rule_can_allow_command_prefix_without_approval(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="git status --short", cwd="."),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.NEVER,
            policy_manifest=ToolPolicyManifest(
                rules=[
                    ToolPolicyRule(
                        rule_id="allow-git-status",
                        tool_name="run_command",
                        action="allow",
                        command_prefixes=["git status"],
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert "allow-git-status" in decision.reason
    assert decision.outcome == "allow"
    assert decision.source_kind == "rule"
    assert decision.source_label == "allow-git-status"
