"""Unit tests for local tool policy evaluation."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from glassbox.cli.policy_formatters import format_policy_summary
from glassbox.core import AutonomyMode
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import PolicyActivitySummary
from glassbox.tools import DEFAULT_TOOL_POLICY_PATH
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolAutonomyRule
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolPolicyManifest
from glassbox.tools import ToolPolicyRule
from glassbox.tools import ToolRegistry
from glassbox.tools import ToolRiskLevel
from glassbox.tools import ToolSpec
from glassbox.tools import describe_effective_approval_behavior
from glassbox.tools import load_tool_policy_manifest

EXAMPLE_POLICY_DIR = (
    Path(__file__).resolve().parents[2] / "docs" / "examples" / "tool-policy"
)


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
    timeout: int = 30


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


class ApplyPatchTool:
    spec = ToolSpec(
        name="apply_patch",
        description="Patch one file inside the workspace.",
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


def _workspace_write_budget() -> AutonomyBudget:
    return AutonomyBudget(
        max_steps=3,
        max_tool_calls=5,
        max_write_operations=2,
        max_command_operations=0,
        max_wall_clock_seconds=60,
        max_verification_attempts=2,
        max_branch_attempts=0,
        max_artifact_bytes=1024,
        allowed_risk_buckets=["read_only", "workspace_write"],
    )


def _command_budget() -> AutonomyBudget:
    return AutonomyBudget(
        max_steps=3,
        max_tool_calls=5,
        max_write_operations=2,
        max_command_operations=2,
        max_wall_clock_seconds=60,
        max_verification_attempts=2,
        max_branch_attempts=0,
        max_artifact_bytes=1024,
        allowed_risk_buckets=["read_only", "workspace_write", "command"],
    )


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


def test_confirm_mode_still_requires_approval_with_autonomy_budget() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
            autonomy_mode=AutonomyMode.EDIT_SAFE,
            autonomy_budget=_workspace_write_budget(),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.outcome == "approve"


def test_review_mode_allows_budgeted_workspace_write() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        WriteFileTool.spec,
        arguments=WriteFileArgs(path="notes.txt", content="hello"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
            autonomy_mode=AutonomyMode.EDIT_SAFE,
            autonomy_budget=_workspace_write_budget(),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.outcome == "allow"
    assert "review approval mode" in decision.reason
    assert "edit-safe autonomy budget" in decision.reason


def test_review_mode_keeps_commands_approval_gated_with_budget() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv run pytest", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_command_budget(),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.outcome == "approve"


def test_on_request_mode_allows_budgeted_default_command() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv run pytest", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_command_budget(),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.outcome == "allow"
    assert "on-request approval mode" in decision.reason


def test_on_request_mode_honors_explicit_approval_rules() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv run pytest", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_command_budget(),
            policy_manifest=ToolPolicyManifest(
                rules=[
                    ToolPolicyRule(
                        rule_id="request-tests",
                        tool_name="run_command",
                        action="approve",
                        command_prefixes=["uv run pytest"],
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.outcome == "approve"
    assert decision.source_label == "request-tests"


def test_autonomy_rule_allows_budgeted_targeted_test_command() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv run pytest tests/unit", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_command_budget(),
            policy_manifest=ToolPolicyManifest(
                autonomy_rules=[
                    ToolAutonomyRule(
                        rule_id="targeted-tests",
                        action="allow-with-budget",
                        tool_name="run_command",
                        command_prefixes=["uv run pytest tests/"],
                        max_timeout_seconds=60,
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.outcome == "allow"
    assert decision.source_label == "targeted-tests"
    assert "max_command_operations" in decision.reason


def test_autonomy_rule_pauses_when_budget_field_is_missing() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv run pytest tests/unit", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_workspace_write_budget(),
            policy_manifest=ToolPolicyManifest(
                autonomy_rules=[
                    ToolAutonomyRule(
                        rule_id="targeted-tests",
                        action="allow-with-budget",
                        tool_name="run_command",
                        command_prefixes=["uv run pytest tests/"],
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.outcome == "approve"
    assert "needs budget field max_command_operations" in decision.reason


def test_autonomy_rule_does_not_override_standard_deny_rule() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="pnpm publish --dry-run", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
            autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
            autonomy_budget=_command_budget(),
            policy_manifest=ToolPolicyManifest(
                rules=[
                    ToolPolicyRule(
                        rule_id="deny-publish",
                        tool_name="run_command",
                        action="deny",
                        command_prefixes=["pnpm publish"],
                    )
                ],
                autonomy_rules=[
                    ToolAutonomyRule(
                        rule_id="local-commands",
                        action="allow-with-budget",
                        tool_name="run_command",
                        command_prefixes=["pnpm"],
                    )
                ],
            ),
        ),
    )

    assert decision.allowed is False
    assert decision.outcome == "deny"
    assert decision.source_label == "deny-publish"


def test_autonomy_rule_selectors_cover_paths_extensions_and_timeout() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        ApplyPatchTool.spec,
        arguments=WriteFileArgs(path="generated/snapshots/state.json", content="{}"),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.REVIEW,
            autonomy_mode=AutonomyMode.EDIT_SAFE,
            autonomy_budget=_workspace_write_budget(),
            policy_manifest=ToolPolicyManifest(
                autonomy_rules=[
                    ToolAutonomyRule(
                        rule_id="generated-json",
                        action="allow-with-budget",
                        tool_name="apply_patch",
                        generated_path_prefixes=["generated"],
                        file_extensions=["json"],
                    )
                ]
            ),
        ),
    )

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.source_label == "generated-json"


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


def test_approval_behavior_label_describes_budgeted_review_mode() -> None:
    label = describe_effective_approval_behavior(
        ApprovalMode.REVIEW,
        autonomy_mode=AutonomyMode.EDIT_SAFE,
        budget=_workspace_write_budget(),
    )

    assert label == (
        "review: budgeted workspace writes may run; commands request approval"
    )


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


@pytest.mark.parametrize(
    ("command", "source_label", "reason_fragment"),
    [
        ("npm publish", "publish_command", "publish command"),
        ("twine upload dist/*", "publish_command", "publish command"),
        ("vercel deploy --prod", "deploy_command", "deploy command"),
        ("kubectl apply -f deploy.yaml", "deploy_command", "deploy command"),
        ("git push origin main", "remote_or_history_mutation", "remote git"),
        ("git rebase main", "remote_or_history_mutation", "history mutation"),
    ],
)
def test_policy_blocks_publish_deploy_and_history_mutation_commands(
    command: str,
    source_label: str,
    reason_fragment: str,
) -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command=command, cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.ON_REQUEST,
        ),
    )

    assert decision.allowed is False
    assert decision.requires_approval is False
    assert reason_fragment in decision.reason
    assert decision.outcome == "blocked"
    assert decision.source_kind == "invariant"
    assert decision.source_label == source_label


def test_policy_allows_local_package_build_without_publish_block() -> None:
    engine = ToolPolicyEngine()

    decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="uv build", cwd="."),
        context=ToolPolicyContext(
            workspace_root=Path("/tmp/workspace"),
            approval_mode=ApprovalMode.CONFIRM,
        ),
    )

    assert decision.allowed is True
    assert decision.outcome == "approve"
    assert decision.source_kind == "default"


def test_policy_summary_points_to_source_and_reason_details() -> None:
    summary = PolicyActivitySummary(
        total_decisions=2,
        allow_count=1,
        approve_count=1,
        workspace_write_count=1,
        command_count=1,
        highest_risk_level="command",
    )

    rendered = format_policy_summary(summary)

    assert "2 decision(s)" in rendered
    assert "highest command" in rendered
    assert "source/reason detail in approvals and recent tool activity" in rendered


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


def test_load_tool_policy_manifest_parses_autonomy_rules(tmp_path: Path) -> None:
    (tmp_path / DEFAULT_TOOL_POLICY_PATH).write_text(
        """
                {
                    "manifest_version": 1,
                    "autonomy_rules": [
                        {
                            "rule_id": "generated-json",
                            "action": "allow-with-budget",
                            "tool_name": "apply_patch",
                            "generated_path_prefixes": ["generated"],
                            "file_extensions": ["json"],
                            "max_timeout_seconds": 30
                        }
                    ]
                }
                """,
        encoding="utf-8",
    )

    manifest = load_tool_policy_manifest(tmp_path)

    assert len(manifest.autonomy_rules) == 1
    assert manifest.autonomy_rules[0].rule_id == "generated-json"
    assert manifest.autonomy_rules[0].file_extensions == [".json"]


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


def _load_example_manifest(name: str) -> ToolPolicyManifest:
    return ToolPolicyManifest.model_validate_json(
        (EXAMPLE_POLICY_DIR / name).read_text(encoding="utf-8")
    )


def test_example_policy_manifests_are_loadable_and_review_safe(
    tmp_path: Path,
) -> None:
    fixture_names = [
        "default-review.json",
        "docs-write-allowlist.json",
        "local-command-governance.json",
        "deny-publish-commands.json",
        "autonomy-safe-local.json",
    ]

    for fixture_name in fixture_names:
        raw_manifest = (EXAMPLE_POLICY_DIR / fixture_name).read_text(encoding="utf-8")
        assert "sk-" not in raw_manifest.lower()
        assert "/users/" not in raw_manifest.lower()
        assert "api_key" not in raw_manifest.lower()

        workspace_root = tmp_path / fixture_name.removesuffix(".json")
        workspace_root.mkdir()
        (workspace_root / DEFAULT_TOOL_POLICY_PATH).write_text(
            raw_manifest,
            encoding="utf-8",
        )

        loaded = load_tool_policy_manifest(workspace_root)
        assert loaded.manifest_version == 1


def test_default_review_fixture_keeps_default_allow_and_approve_posture(
    tmp_path: Path,
) -> None:
    engine = ToolPolicyEngine()
    manifest = _load_example_manifest("default-review.json")

    read_decision = engine.evaluate(
        ReadFileTool.spec,
        arguments=ReadFileArgs(path="README.md"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )
    write_decision = engine.evaluate(
        ApplyPatchTool.spec,
        arguments=WriteFileArgs(path="src/glassbox/__init__.py", content=""),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )
    command_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(
            command="uv run pytest tests/unit/test_tools_policy.py"
        ),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )

    assert read_decision.outcome == "allow"
    assert write_decision.outcome == "approve"
    assert command_decision.outcome == "approve"
    assert [
        read_decision.source_kind,
        write_decision.source_kind,
        command_decision.source_kind,
    ] == ["default", "default", "default"]


def test_docs_write_fixture_covers_path_prefix_and_workspace_scope_block(
    tmp_path: Path,
) -> None:
    engine = ToolPolicyEngine()
    manifest = _load_example_manifest("docs-write-allowlist.json")

    docs_decision = engine.evaluate(
        ApplyPatchTool.spec,
        arguments=WriteFileArgs(path="docs/tool-policy.md", content="update"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.NEVER,
            policy_manifest=manifest,
        ),
    )
    source_decision = engine.evaluate(
        ApplyPatchTool.spec,
        arguments=WriteFileArgs(path="src/glassbox/tools/policy.py", content="update"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )
    blocked_decision = engine.evaluate(
        ApplyPatchTool.spec,
        arguments=WriteFileArgs(path="../outside.md", content="update"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )

    assert docs_decision.outcome == "allow"
    assert docs_decision.source_kind == "rule"
    assert docs_decision.source_label == "allow-docs-patches"
    assert source_decision.outcome == "approve"
    assert source_decision.source_kind == "default"
    assert blocked_decision.outcome == "blocked"
    assert blocked_decision.source_kind == "invariant"
    assert blocked_decision.source_label == "workspace_scope"


def test_command_fixture_covers_command_and_cwd_prefixes(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    manifest = _load_example_manifest("local-command-governance.json")

    git_status_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="git status --short", cwd="."),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.NEVER,
            policy_manifest=manifest,
        ),
    )
    script_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="python validate_release.py", cwd="scripts"),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.NEVER,
            policy_manifest=manifest,
        ),
    )
    wrong_cwd_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="python validate_release.py", cwd="."),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )

    assert git_status_decision.outcome == "allow"
    assert git_status_decision.source_label == "allow-git-status"
    assert script_decision.outcome == "allow"
    assert script_decision.source_label == "allow-script-validation"
    assert wrong_cwd_decision.outcome == "approve"
    assert wrong_cwd_decision.source_kind == "default"


def test_deny_fixture_and_destructive_invariant_stay_distinct(tmp_path: Path) -> None:
    engine = ToolPolicyEngine()
    manifest = _load_example_manifest("deny-publish-commands.json")

    deny_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="pnpm publish --dry-run", cwd="."),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )
    destructive_decision = engine.evaluate(
        RunCommandTool.spec,
        arguments=RunCommandArgs(command="rm -rf build", cwd="."),
        context=ToolPolicyContext(
            workspace_root=tmp_path,
            approval_mode=ApprovalMode.CONFIRM,
            policy_manifest=manifest,
        ),
    )

    assert deny_decision.allowed is False
    assert deny_decision.outcome == "deny"
    assert deny_decision.source_kind == "rule"
    assert deny_decision.source_label == "deny-package-publish"
    assert destructive_decision.allowed is False
    assert destructive_decision.outcome == "blocked"
    assert destructive_decision.source_kind == "invariant"
    assert destructive_decision.source_label == "destructive_command"
