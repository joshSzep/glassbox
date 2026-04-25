"""Local policy evaluation for tool execution requests."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ApprovalMode
from glassbox.core import PolicyDecision
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.tools.policy_config import ToolPolicyAction
from glassbox.tools.policy_config import ToolPolicyManifest
from glassbox.tools.policy_config import ToolPolicyRule
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


class ToolPolicyContext(BaseModel):
    """Inputs required to evaluate one tool request against local policy."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    approval_mode: ApprovalMode
    policy_manifest: ToolPolicyManifest = Field(default_factory=ToolPolicyManifest)


@dataclass(frozen=True, slots=True)
class _ResolvedPolicyOutcome:
    action: ToolPolicyAction
    source_kind: PolicyDecisionSourceKind
    source_label: str


@dataclass(frozen=True, slots=True)
class _PolicyDecisionMessages:
    allow_reason: str
    deny_reason: str
    approval_reason: str
    blocked_reason: str


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
        command_text = _command_text(tool_spec, normalized_arguments)

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
                outcome="blocked",
                risk_level=tool_spec.risk_level.value,
                source_kind="invariant",
                source_label="workspace_scope",
            )

        if tool_spec.risk_level is ToolRiskLevel.COMMAND:
            if command_text is not None and _is_destructive_command(command_text):
                return PolicyDecision(
                    allowed=False,
                    requires_approval=False,
                    reason="blocked: destructive command pattern is not allowed",
                    outcome="blocked",
                    risk_level=tool_spec.risk_level.value,
                    source_kind="invariant",
                    source_label="destructive_command",
                )

        outcome = _resolve_policy_outcome(
            tool_spec,
            arguments=normalized_arguments,
            workspace_root=workspace_root,
            policy_manifest=context.policy_manifest,
            command_text=command_text,
        )
        return _decision_from_outcome(
            outcome,
            tool_spec=tool_spec,
            approval_mode=context.approval_mode,
        )

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
    risk_level: ToolRiskLevel,
    source_kind: PolicyDecisionSourceKind,
    source_label: str,
) -> PolicyDecision:
    if approval_mode is ApprovalMode.NEVER:
        return PolicyDecision(
            allowed=False,
            requires_approval=False,
            reason=blocked_reason,
            outcome="blocked",
            risk_level=risk_level.value,
            source_kind=source_kind,
            source_label=source_label,
        )

    return PolicyDecision(
        allowed=True,
        requires_approval=True,
        reason=f"{approval_reason} ({approval_mode.value})",
        outcome="approve",
        risk_level=risk_level.value,
        source_kind=source_kind,
        source_label=source_label,
    )


def _resolve_policy_outcome(
    tool_spec: ToolSpec,
    *,
    arguments: Mapping[str, object],
    workspace_root: Path,
    policy_manifest: ToolPolicyManifest,
    command_text: str | None,
) -> _ResolvedPolicyOutcome:
    for index, rule in enumerate(policy_manifest.rules, start=1):
        if _rule_matches(
            rule,
            tool_spec=tool_spec,
            arguments=arguments,
            workspace_root=workspace_root,
            command_text=command_text,
        ):
            return _ResolvedPolicyOutcome(
                action=rule.action,
                source_kind="rule",
                source_label=rule.rule_id or f"rule_{index}",
            )

    return _ResolvedPolicyOutcome(
        action=_default_policy_action(tool_spec.risk_level, policy_manifest),
        source_kind="default",
        source_label=tool_spec.risk_level.value,
    )


def _rule_matches(
    rule: ToolPolicyRule,
    *,
    tool_spec: ToolSpec,
    arguments: Mapping[str, object],
    workspace_root: Path,
    command_text: str | None,
) -> bool:
    if rule.tool_name != tool_spec.name:
        return False

    if rule.command_prefixes:
        if command_text is None:
            return False
        if not any(command_text.startswith(prefix) for prefix in rule.command_prefixes):
            return False

    if rule.cwd_prefixes and not _path_prefixes_match(
        arguments.get("cwd"),
        prefixes=rule.cwd_prefixes,
        workspace_root=workspace_root,
    ):
        return False

    if rule.path_prefixes:
        path_argument_names = tuple(
            argument_name
            for argument_name in tool_spec.path_argument_names
            if argument_name != "cwd"
        )
        if not path_argument_names:
            return False
        if not all(
            _path_prefixes_match(
                arguments.get(argument_name),
                prefixes=rule.path_prefixes,
                workspace_root=workspace_root,
            )
            for argument_name in path_argument_names
        ):
            return False

    return True


def _path_prefixes_match(
    value: object,
    *,
    prefixes: list[str],
    workspace_root: Path,
) -> bool:
    candidate_paths = _iter_path_values(value)
    if not candidate_paths:
        return False
    resolved_prefixes = [
        (workspace_root / prefix).resolve(strict=False) for prefix in prefixes
    ]
    return all(
        any(
            _is_within_workspace_prefix(
                _resolve_scoped_path(candidate, workspace_root),
                prefix,
            )
            for prefix in resolved_prefixes
        )
        for candidate in candidate_paths
    )


def _is_within_workspace_prefix(candidate: Path, prefix: Path) -> bool:
    try:
        candidate.relative_to(prefix)
    except ValueError:
        return False
    return True


def _default_policy_action(
    risk_level: ToolRiskLevel,
    policy_manifest: ToolPolicyManifest,
) -> ToolPolicyAction:
    if risk_level is ToolRiskLevel.READ_ONLY:
        return policy_manifest.defaults.read_only
    if risk_level is ToolRiskLevel.WORKSPACE_WRITE:
        return policy_manifest.defaults.workspace_write
    if risk_level is ToolRiskLevel.COMMAND:
        return policy_manifest.defaults.command
    raise ValueError(f"unsupported tool risk level: {risk_level}")


def _decision_from_outcome(
    outcome: _ResolvedPolicyOutcome,
    *,
    tool_spec: ToolSpec,
    approval_mode: ApprovalMode,
) -> PolicyDecision:
    if outcome.source_kind == "default":
        return _decision_from_action(
            outcome.action,
            approval_mode=approval_mode,
            risk_level=tool_spec.risk_level,
            source_kind=outcome.source_kind,
            source_label=outcome.source_label,
            messages=_default_policy_messages(tool_spec.risk_level),
        )

    return _decision_from_action(
        outcome.action,
        approval_mode=approval_mode,
        risk_level=tool_spec.risk_level,
        source_kind=outcome.source_kind,
        source_label=outcome.source_label,
        messages=_PolicyDecisionMessages(
            allow_reason=(
                f"allowed: workspace policy rule '{outcome.source_label}' "
                f"matched tool '{tool_spec.name}'"
            ),
            deny_reason=(
                f"blocked: workspace policy rule '{outcome.source_label}' "
                f"denied tool '{tool_spec.name}'"
            ),
            approval_reason=(
                f"approval required: workspace policy rule '{outcome.source_label}' "
                f"matched tool '{tool_spec.name}'"
            ),
            blocked_reason=(
                f"blocked: workspace policy rule '{outcome.source_label}' "
                f"requires approval but approval mode is never"
            ),
        ),
    )


def _decision_from_action(
    action: ToolPolicyAction,
    *,
    approval_mode: ApprovalMode,
    risk_level: ToolRiskLevel,
    source_kind: PolicyDecisionSourceKind,
    source_label: str,
    messages: _PolicyDecisionMessages,
) -> PolicyDecision:
    if action == "allow":
        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            reason=messages.allow_reason,
            outcome="allow",
            risk_level=risk_level.value,
            source_kind=source_kind,
            source_label=source_label,
        )
    if action == "deny":
        return PolicyDecision(
            allowed=False,
            requires_approval=False,
            reason=messages.deny_reason,
            outcome="deny",
            risk_level=risk_level.value,
            source_kind=source_kind,
            source_label=source_label,
        )

    return _approval_gate(
        approval_mode=approval_mode,
        blocked_reason=messages.blocked_reason,
        approval_reason=messages.approval_reason,
        risk_level=risk_level,
        source_kind=source_kind,
        source_label=source_label,
    )


def _default_policy_messages(
    risk_level: ToolRiskLevel,
) -> _PolicyDecisionMessages:
    if risk_level is ToolRiskLevel.READ_ONLY:
        return _PolicyDecisionMessages(
            allow_reason="allowed: read-only tool within workspace scope",
            deny_reason="blocked: read-only tool denied by workspace policy default",
            approval_reason=(
                "approval required: read-only tool is gated by workspace policy default"
            ),
            blocked_reason=(
                "blocked: read-only tool requires approval but approval mode is never"
            ),
        )

    if risk_level is ToolRiskLevel.WORKSPACE_WRITE:
        return _PolicyDecisionMessages(
            allow_reason=(
                "allowed: workspace write permitted by workspace policy default"
            ),
            deny_reason=("blocked: workspace write denied by workspace policy default"),
            approval_reason="approval required: workspace write inside workspace scope",
            blocked_reason=(
                "blocked: workspace write requires approval but approval mode is never"
            ),
        )

    if risk_level is ToolRiskLevel.COMMAND:
        return _PolicyDecisionMessages(
            allow_reason=(
                "allowed: command execution permitted by workspace policy default"
            ),
            deny_reason=(
                "blocked: command execution denied by workspace policy default"
            ),
            approval_reason=(
                "approval required: command execution is gated by local policy"
            ),
            blocked_reason=(
                "blocked: command execution requires approval but approval mode is "
                "never"
            ),
        )

    raise ValueError(f"unsupported tool risk level: {risk_level}")


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
