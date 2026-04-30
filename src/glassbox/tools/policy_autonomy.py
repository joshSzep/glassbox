"""Autonomy-budget and autonomy-rule helpers for tool policy."""

from collections.abc import Mapping
from pathlib import Path

from glassbox.core import ApprovalMode
from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyMode
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.tools.policy_config import ToolAutonomyRule
from glassbox.tools.policy_config import ToolPolicyAction
from glassbox.tools.policy_models import ResolvedPolicyOutcome
from glassbox.tools.policy_models import ToolPolicyContext
from glassbox.tools.policy_paths import path_argument_prefixes_match
from glassbox.tools.policy_paths import path_argument_values
from glassbox.tools.policy_paths import path_extensions_match
from glassbox.tools.policy_paths import path_prefixes_match
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


def budgeted_approval_allow_reason(
    context: ToolPolicyContext,
    *,
    risk_level: ToolRiskLevel,
    source_kind: PolicyDecisionSourceKind,
    approval_reason: str,
) -> str | None:
    """Return an autonomy-budget allow reason for approval-gated actions."""

    if not budget_permits_risk(context.autonomy_budget, risk_level):
        return None
    if context.autonomy_mode in {AutonomyMode.MANUAL, AutonomyMode.GUIDED}:
        return None

    if context.approval_mode is ApprovalMode.REVIEW:
        if risk_level is not ToolRiskLevel.WORKSPACE_WRITE:
            return None
    elif context.approval_mode is ApprovalMode.ON_REQUEST:
        if source_kind == "rule":
            return None
    else:
        return None

    reason = approval_reason.removeprefix("approval required: ")
    return (
        f"allowed: {reason} under {context.approval_mode.value} approval mode "
        f"with {context.autonomy_mode.value} autonomy budget"
    )


def budget_permits_risk(
    budget: AutonomyBudget | None,
    risk_level: ToolRiskLevel,
) -> bool:
    """Return whether the autonomy budget permits a risk bucket."""

    if budget is None or risk_level.value not in budget.allowed_risk_buckets:
        return False
    if risk_level is ToolRiskLevel.WORKSPACE_WRITE:
        return budget.max_write_operations > 0
    if risk_level is ToolRiskLevel.COMMAND:
        return budget.max_command_operations > 0
    return True


def describe_effective_approval_behavior(
    approval_mode: ApprovalMode | str,
    *,
    autonomy_mode: AutonomyMode | str | None = None,
    budget: AutonomyBudget | None = None,
) -> str:
    """Describe the effective approval behavior for status surfaces."""

    mode = ApprovalMode(approval_mode)
    resolved_autonomy_mode = (
        AutonomyMode(autonomy_mode)
        if autonomy_mode is not None
        else AutonomyMode.MANUAL
    )
    has_budget = budget is not None and resolved_autonomy_mode not in {
        AutonomyMode.MANUAL,
        AutonomyMode.GUIDED,
    }

    if mode is ApprovalMode.NEVER:
        return "never: approve-gated write and command actions are blocked"
    if mode is ApprovalMode.CONFIRM:
        return "confirm: approve-gated write and command actions request approval"
    if mode is ApprovalMode.REVIEW:
        if has_budget and budget_permits_risk(budget, ToolRiskLevel.WORKSPACE_WRITE):
            return (
                "review: budgeted workspace writes may run; commands request approval"
            )
        return "review: write and command actions request approval until budgeted"
    if has_budget:
        return (
            "on-request: budgeted default-gated actions may run; approval rules pause"
        )
    return "on-request: approve-gated actions request approval until budgeted"


def autonomy_rule_matches(
    rule: ToolAutonomyRule,
    *,
    tool_spec: ToolSpec,
    arguments: Mapping[str, object],
    workspace_root: Path,
    command_text: str | None,
) -> bool:
    """Return whether an autonomy policy rule matches the tool request."""

    if rule.tool_name is not None and rule.tool_name != tool_spec.name:
        return False
    if rule.risk_buckets and tool_spec.risk_level.value not in rule.risk_buckets:
        return False
    if rule.read_only_operation is not None:
        is_read_only = tool_spec.risk_level is ToolRiskLevel.READ_ONLY
        if rule.read_only_operation != is_read_only:
            return False
    if rule.command_prefixes:
        if command_text is None:
            return False
        if not any(command_text.startswith(prefix) for prefix in rule.command_prefixes):
            return False
    if rule.cwd_prefixes and not path_prefixes_match(
        arguments.get("cwd"),
        prefixes=rule.cwd_prefixes,
        workspace_root=workspace_root,
    ):
        return False
    if rule.path_prefixes and not path_argument_prefixes_match(
        tool_spec,
        arguments=arguments,
        prefixes=rule.path_prefixes,
        workspace_root=workspace_root,
    ):
        return False
    if rule.file_extensions and not path_extensions_match(
        path_argument_values(tool_spec, arguments),
        extensions=rule.file_extensions,
    ):
        return False
    if rule.test_path_prefixes and not path_prefixes_match(
        path_argument_values(tool_spec, arguments),
        prefixes=rule.test_path_prefixes,
        workspace_root=workspace_root,
    ):
        return False
    if rule.generated_path_prefixes and not path_prefixes_match(
        path_argument_values(tool_spec, arguments),
        prefixes=rule.generated_path_prefixes,
        workspace_root=workspace_root,
    ):
        return False
    if rule.max_timeout_seconds is not None:
        timeout = timeout_argument(arguments)
        if timeout is None or timeout > rule.max_timeout_seconds:
            return False
    return True


def autonomy_rule_outcome(
    rule: ToolAutonomyRule,
    *,
    context: ToolPolicyContext,
    risk_level: ToolRiskLevel,
) -> ResolvedPolicyOutcome:
    """Resolve a matched autonomy rule into a policy action."""

    budget_field = budget_field_for_risk(risk_level)
    if rule.action == "deny":
        action: ToolPolicyAction = "deny"
    elif rule.action in {"require-approval", "require-verification"}:
        action = "approve"
    elif budget_permits_risk(context.autonomy_budget, risk_level):
        action = "allow"
    else:
        action = "approve"
    return ResolvedPolicyOutcome(
        action=action,
        source_kind="rule",
        source_label=rule.rule_id,
        autonomy_action=rule.action,
        budget_field=budget_field,
    )


def budget_field_for_risk(risk_level: ToolRiskLevel) -> str:
    """Return the autonomy budget field that controls a tool risk bucket."""

    if risk_level is ToolRiskLevel.WORKSPACE_WRITE:
        return "max_write_operations"
    if risk_level is ToolRiskLevel.COMMAND:
        return "max_command_operations"
    return "max_tool_calls"


def timeout_argument(arguments: Mapping[str, object]) -> int | None:
    """Return the first supported timeout argument."""

    for name in ("timeout", "timeout_seconds"):
        value = arguments.get(name)
        if isinstance(value, int):
            return value
    return None
