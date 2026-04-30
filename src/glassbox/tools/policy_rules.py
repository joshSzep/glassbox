"""Policy manifest rule matching and outcome resolution."""

from collections.abc import Mapping
from pathlib import Path

from glassbox.tools.policy_autonomy import autonomy_rule_matches
from glassbox.tools.policy_autonomy import autonomy_rule_outcome
from glassbox.tools.policy_config import ToolPolicyAction
from glassbox.tools.policy_config import ToolPolicyManifest
from glassbox.tools.policy_config import ToolPolicyRule
from glassbox.tools.policy_models import ResolvedPolicyOutcome
from glassbox.tools.policy_models import ToolPolicyContext
from glassbox.tools.policy_paths import path_argument_prefixes_match
from glassbox.tools.policy_paths import path_prefixes_match
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


def resolve_policy_outcome(
    tool_spec: ToolSpec,
    *,
    arguments: Mapping[str, object],
    context: ToolPolicyContext,
    workspace_root: Path,
    policy_manifest: ToolPolicyManifest,
    command_text: str | None,
) -> ResolvedPolicyOutcome:
    """Resolve manifest rules, autonomy rules, and defaults for a request."""

    for index, rule in enumerate(policy_manifest.rules, start=1):
        if rule_matches(
            rule,
            tool_spec=tool_spec,
            arguments=arguments,
            workspace_root=workspace_root,
            command_text=command_text,
        ):
            return ResolvedPolicyOutcome(
                action=rule.action,
                source_kind="rule",
                source_label=rule.rule_id or f"rule_{index}",
            )

    for rule in policy_manifest.autonomy_rules:
        if not autonomy_rule_matches(
            rule,
            tool_spec=tool_spec,
            arguments=arguments,
            workspace_root=workspace_root,
            command_text=command_text,
        ):
            continue
        return autonomy_rule_outcome(
            rule,
            context=context,
            risk_level=tool_spec.risk_level,
        )

    return ResolvedPolicyOutcome(
        action=default_policy_action(tool_spec.risk_level, policy_manifest),
        source_kind="default",
        source_label=tool_spec.risk_level.value,
    )


def rule_matches(
    rule: ToolPolicyRule,
    *,
    tool_spec: ToolSpec,
    arguments: Mapping[str, object],
    workspace_root: Path,
    command_text: str | None,
) -> bool:
    """Return whether a workspace policy rule matches the tool request."""

    if rule.tool_name != tool_spec.name:
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

    return True


def default_policy_action(
    risk_level: ToolRiskLevel,
    policy_manifest: ToolPolicyManifest,
) -> ToolPolicyAction:
    """Return the manifest default action for a tool risk level."""

    if risk_level is ToolRiskLevel.READ_ONLY:
        return policy_manifest.defaults.read_only
    if risk_level is ToolRiskLevel.WORKSPACE_WRITE:
        return policy_manifest.defaults.workspace_write
    if risk_level is ToolRiskLevel.COMMAND:
        return policy_manifest.defaults.command
    raise ValueError(f"unsupported tool risk level: {risk_level}")
