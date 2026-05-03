"""Stable tool-policy engine facade."""

from collections.abc import Mapping

from pydantic import BaseModel

from glassbox.core import ApprovalMode
from glassbox.core import PolicyDecision
from glassbox.tools.policy_autonomy import describe_effective_approval_behavior
from glassbox.tools.policy_command_risk import blocked_command_risk
from glassbox.tools.policy_command_risk import command_text
from glassbox.tools.policy_messages import decision_from_outcome
from glassbox.tools.policy_models import ToolPolicyContext
from glassbox.tools.policy_paths import first_out_of_scope_path
from glassbox.tools.policy_paths import normalize_tool_arguments
from glassbox.tools.policy_rules import resolve_policy_outcome
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec

__all__ = [
    "ApprovalMode",
    "ToolPolicyContext",
    "ToolPolicyEngine",
    "describe_effective_approval_behavior",
]


class ToolPolicyEngine:
    """Evaluate tool requests against local risk and workspace rules."""

    def evaluate(
        self,
        tool_spec: ToolSpec,
        *,
        arguments: BaseModel | Mapping[str, object],
        context: ToolPolicyContext,
    ) -> PolicyDecision:
        normalized_arguments = normalize_tool_arguments(arguments)
        workspace_root = context.workspace_root.resolve(strict=False)
        resolved_command_text = command_text(tool_spec, normalized_arguments)

        blocked_path = first_out_of_scope_path(
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

        command_risk = (
            blocked_command_risk(resolved_command_text)
            if tool_spec.risk_level is ToolRiskLevel.COMMAND
            and resolved_command_text is not None
            else None
        )
        if command_risk is not None:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                reason=command_risk.reason,
                outcome="blocked",
                risk_level=tool_spec.risk_level.value,
                source_kind="invariant",
                source_label=command_risk.source_label,
            )

        outcome = resolve_policy_outcome(
            tool_spec,
            arguments=normalized_arguments,
            context=context,
            workspace_root=workspace_root,
            policy_manifest=context.policy_manifest,
            command_text=resolved_command_text,
        )
        return decision_from_outcome(
            outcome,
            tool_spec=tool_spec,
            context=context,
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
