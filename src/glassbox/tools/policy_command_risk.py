"""Command text extraction and command-risk heuristics for tool policy."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from glassbox.tools.policy_command_patterns import DEPLOY_COMMAND_PATTERNS
from glassbox.tools.policy_command_patterns import DESTRUCTIVE_COMMAND_PATTERNS
from glassbox.tools.policy_command_patterns import DRY_RUN_FLAGS
from glassbox.tools.policy_command_patterns import PUBLISH_COMMAND_PATTERNS
from glassbox.tools.policy_command_patterns import REMOTE_GIT_MUTATION_PATTERNS
from glassbox.tools.registry import ToolSpec


@dataclass(frozen=True, slots=True)
class CommandRiskAssessment:
    """Hard command-risk assessment used by policy invariants."""

    source_label: str
    reason: str


def command_text(tool_spec: ToolSpec, arguments: Mapping[str, object]) -> str | None:
    """Return normalized command text for command tools."""

    if tool_spec.command_argument_name is None:
        return None
    value = arguments.get(tool_spec.command_argument_name)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def is_destructive_command(command_text: str) -> bool:
    """Return whether command text matches blocked destructive patterns."""

    normalized_command = command_text.strip().lower()
    return any(
        pattern.search(normalized_command) is not None
        for pattern in DESTRUCTIVE_COMMAND_PATTERNS
    )


def blocked_command_risk(command_text: str) -> CommandRiskAssessment | None:
    """Return a hard-blocking command risk, if one is present."""

    normalized_command = command_text.strip().lower()
    if is_destructive_command(normalized_command):
        return CommandRiskAssessment(
            source_label="destructive_command",
            reason="blocked: destructive command pattern is not allowed",
        )
    if _contains_dry_run_flag(normalized_command):
        return None
    if _matches_any(normalized_command, PUBLISH_COMMAND_PATTERNS):
        return CommandRiskAssessment(
            source_label="publish_command",
            reason="blocked: publish command pattern is not allowed",
        )
    if _matches_any(normalized_command, DEPLOY_COMMAND_PATTERNS):
        return CommandRiskAssessment(
            source_label="deploy_command",
            reason="blocked: deploy command pattern is not allowed",
        )
    if _matches_any(normalized_command, REMOTE_GIT_MUTATION_PATTERNS):
        return CommandRiskAssessment(
            source_label="remote_or_history_mutation",
            reason=(
                "blocked: remote git or history mutation command pattern is not allowed"
            ),
        )
    return None


def _matches_any(command: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(command) is not None for pattern in patterns)


def _contains_dry_run_flag(command: str) -> bool:
    return any(flag in f" {command} " for flag in DRY_RUN_FLAGS)
