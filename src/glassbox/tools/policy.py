"""Local policy evaluation for tool execution requests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core import ApprovalMode
from glassbox.core import PolicyDecision
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


class ToolPolicyContext(BaseModel):
    """Inputs required to evaluate one tool request against local policy."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    approval_mode: ApprovalMode


class ToolPolicyEngine:
    """Evaluate tool requests against local risk and workspace rules."""

    def evaluate(
        self,
        tool_spec: ToolSpec,
        *,
        arguments: BaseModel | Mapping[str, object],
        context: ToolPolicyContext,
    ) -> PolicyDecision:
        normalized_arguments = _normalize_arguments(arguments)
        workspace_root = context.workspace_root.resolve(strict=False)

        blocked_path = _first_out_of_scope_path(
            tool_spec,
            arguments=normalized_arguments,
            workspace_root=workspace_root,
        )
        if blocked_path is not None:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                reason=(
                    f"blocked: path '{blocked_path}' is outside workspace "
                    f"'{workspace_root}'"
                ),
            )

        if tool_spec.risk_level is ToolRiskLevel.READ_ONLY:
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                reason="allowed: read-only tool within workspace scope",
            )

        if tool_spec.risk_level is ToolRiskLevel.WORKSPACE_WRITE:
            return _approval_gate(
                approval_mode=context.approval_mode,
                blocked_reason=(
                    "blocked: workspace write requires approval but approval "
                    "mode is never"
                ),
                approval_reason=(
                    "approval required: workspace write inside workspace scope"
                ),
            )

        if tool_spec.risk_level is ToolRiskLevel.COMMAND:
            command_text = _command_text(tool_spec, normalized_arguments)
            if command_text is not None and _is_destructive_command(command_text):
                return PolicyDecision(
                    allowed=False,
                    requires_approval=False,
                    reason="blocked: destructive command pattern is not allowed",
                )

            return _approval_gate(
                approval_mode=context.approval_mode,
                blocked_reason=(
                    "blocked: command execution requires approval but approval "
                    "mode is never"
                ),
                approval_reason=(
                    "approval required: command execution is gated by local policy"
                ),
            )

        raise ValueError(f"unsupported tool risk level: {tool_spec.risk_level}")

    def evaluate_registered(
        self,
        tool_registry: ToolRegistry,
        tool_name: str,
        *,
        arguments: BaseModel | Mapping[str, object],
        context: ToolPolicyContext,
    ) -> PolicyDecision:
        """Resolve one registered tool and evaluate it against policy."""

        return self.evaluate(
            tool_registry.require(tool_name).spec,
            arguments=arguments,
            context=context,
        )


def _normalize_arguments(
    arguments: BaseModel | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(arguments, BaseModel):
        return dict(arguments.model_dump(mode="python"))
    return dict(arguments)


def _first_out_of_scope_path(
    tool_spec: ToolSpec,
    *,
    arguments: Mapping[str, object],
    workspace_root: Path,
) -> str | None:
    for argument_name in tool_spec.path_argument_names:
        value = arguments.get(argument_name)
        for candidate in _iter_path_values(value):
            resolved_candidate = _resolve_scoped_path(candidate, workspace_root)
            if not _is_within_workspace(resolved_candidate, workspace_root):
                return str(candidate)
    return None


def _iter_path_values(value: object) -> tuple[Path, ...]:
    if value is None:
        return ()
    if isinstance(value, Path):
        return (value,)
    if isinstance(value, str):
        return (Path(value),)
    if isinstance(value, tuple | list):
        paths: list[Path] = []
        for item in value:
            if isinstance(item, Path):
                paths.append(item)
            elif isinstance(item, str):
                paths.append(Path(item))
        return tuple(paths)
    return ()


def _resolve_scoped_path(candidate: Path, workspace_root: Path) -> Path:
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (workspace_root / candidate).resolve(strict=False)


def _is_within_workspace(candidate: Path, workspace_root: Path) -> bool:
    try:
        candidate.relative_to(workspace_root)
    except ValueError:
        return False
    return True


def _command_text(tool_spec: ToolSpec, arguments: Mapping[str, object]) -> str | None:
    if tool_spec.command_argument_name is None:
        return None
    value = arguments.get(tool_spec.command_argument_name)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _approval_gate(
    *,
    approval_mode: ApprovalMode,
    blocked_reason: str,
    approval_reason: str,
) -> PolicyDecision:
    if approval_mode is ApprovalMode.NEVER:
        return PolicyDecision(
            allowed=False,
            requires_approval=False,
            reason=blocked_reason,
        )

    return PolicyDecision(
        allowed=True,
        requires_approval=True,
        reason=f"{approval_reason} ({approval_mode.value})",
    )


_DESTRUCTIVE_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)rm\s+-[A-Za-z-]*[rf][A-Za-z-]*\b"),
    re.compile(r"(^|\s)git\s+clean\b[^\n]*\s-f\b"),
    re.compile(r"(^|\s)git\s+reset\s+--hard\b"),
    re.compile(r"(^|\s)(mkfs|shutdown|reboot|poweroff)\b"),
)


def _is_destructive_command(command_text: str) -> bool:
    normalized_command = command_text.strip().lower()
    return any(
        pattern.search(normalized_command) is not None
        for pattern in _DESTRUCTIVE_COMMAND_PATTERNS
    )
