"""Approval gates and policy decision message construction."""

from glassbox.core import ApprovalMode
from glassbox.core import PolicyDecision
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.tools.policy_autonomy import budget_field_for_risk
from glassbox.tools.policy_autonomy import budgeted_approval_allow_reason
from glassbox.tools.policy_config import ToolPolicyAction
from glassbox.tools.policy_models import PolicyDecisionMessages
from glassbox.tools.policy_models import ResolvedPolicyOutcome
from glassbox.tools.policy_models import ToolPolicyContext
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


def decision_from_outcome(
    outcome: ResolvedPolicyOutcome,
    *,
    tool_spec: ToolSpec,
    context: ToolPolicyContext,
) -> PolicyDecision:
    """Build a stable public policy decision from a resolved outcome."""

    if outcome.autonomy_action is not None:
        return decision_from_action(
            outcome.action,
            context=context,
            risk_level=tool_spec.risk_level,
            source_kind=outcome.source_kind,
            source_label=outcome.source_label,
            messages=autonomy_policy_messages(outcome, tool_spec),
        )

    if outcome.source_kind == "default":
        return decision_from_action(
            outcome.action,
            context=context,
            risk_level=tool_spec.risk_level,
            source_kind=outcome.source_kind,
            source_label=outcome.source_label,
            messages=default_policy_messages(tool_spec.risk_level),
        )

    return decision_from_action(
        outcome.action,
        context=context,
        risk_level=tool_spec.risk_level,
        source_kind=outcome.source_kind,
        source_label=outcome.source_label,
        messages=PolicyDecisionMessages(
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


def approval_gate(
    *,
    context: ToolPolicyContext,
    blocked_reason: str,
    approval_reason: str,
    risk_level: ToolRiskLevel,
    source_kind: PolicyDecisionSourceKind,
    source_label: str,
) -> PolicyDecision:
    """Apply approval-mode and autonomy-budget behavior to approval actions."""

    approval_mode = context.approval_mode
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

    budget_allow_reason = budgeted_approval_allow_reason(
        context,
        risk_level=risk_level,
        source_kind=source_kind,
        approval_reason=approval_reason,
    )
    if budget_allow_reason is not None:
        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            reason=budget_allow_reason,
            outcome="allow",
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


def autonomy_policy_messages(
    outcome: ResolvedPolicyOutcome,
    tool_spec: ToolSpec,
) -> PolicyDecisionMessages:
    """Build reason strings for autonomy-rule decisions."""

    rule = outcome.source_label
    budget_field = outcome.budget_field or budget_field_for_risk(tool_spec.risk_level)
    if outcome.autonomy_action == "require-verification":
        approval_reason = (
            f"approval required: autonomy rule '{rule}' requires verification "
            f"before tool '{tool_spec.name}'"
        )
    elif outcome.autonomy_action == "allow-with-budget":
        approval_reason = (
            f"approval required: autonomy rule '{rule}' needs budget field "
            f"{budget_field} for tool '{tool_spec.name}'"
        )
    else:
        approval_reason = (
            f"approval required: autonomy rule '{rule}' matched tool '{tool_spec.name}'"
        )
    return PolicyDecisionMessages(
        allow_reason=(
            f"allowed: autonomy rule '{rule}' matched tool '{tool_spec.name}' "
            f"with budget field {budget_field}"
        ),
        deny_reason=(f"blocked: autonomy rule '{rule}' denied tool '{tool_spec.name}'"),
        approval_reason=approval_reason,
        blocked_reason=(
            f"blocked: autonomy rule '{rule}' requires approval but approval mode "
            "is never"
        ),
    )


def decision_from_action(
    action: ToolPolicyAction,
    *,
    context: ToolPolicyContext,
    risk_level: ToolRiskLevel,
    source_kind: PolicyDecisionSourceKind,
    source_label: str,
    messages: PolicyDecisionMessages,
) -> PolicyDecision:
    """Build a public policy decision for an action and message family."""

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

    return approval_gate(
        context=context,
        blocked_reason=messages.blocked_reason,
        approval_reason=messages.approval_reason,
        risk_level=risk_level,
        source_kind=source_kind,
        source_label=source_label,
    )


def default_policy_messages(
    risk_level: ToolRiskLevel,
) -> PolicyDecisionMessages:
    """Build reason strings for default risk-bucket decisions."""

    if risk_level is ToolRiskLevel.READ_ONLY:
        return PolicyDecisionMessages(
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
        return PolicyDecisionMessages(
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
        return PolicyDecisionMessages(
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
