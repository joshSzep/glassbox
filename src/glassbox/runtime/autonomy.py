"""Autonomy mode and budget preset helpers."""

from glassbox.core.models import AutonomyBudget
from glassbox.core.types import AutonomyMode

DEFAULT_AUTONOMY_MODE = AutonomyMode.MANUAL

BUILTIN_AUTONOMY_BUDGET_PRESETS: dict[str, AutonomyBudget] = {
    "manual": AutonomyBudget(
        max_steps=0,
        max_tool_calls=0,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=1,
        max_verification_attempts=0,
        max_branch_attempts=0,
        max_artifact_bytes=0,
        allowed_risk_buckets=["read_only"],
    ),
    "guided": AutonomyBudget(
        max_steps=3,
        max_tool_calls=12,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=600,
        max_verification_attempts=1,
        max_branch_attempts=0,
        max_artifact_bytes=1_000_000,
        allowed_risk_buckets=["read_only"],
    ),
    "inspect": AutonomyBudget(
        max_steps=6,
        max_tool_calls=40,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=900,
        max_verification_attempts=2,
        max_branch_attempts=0,
        max_artifact_bytes=4_000_000,
        allowed_risk_buckets=["read_only"],
    ),
    "edit-safe": AutonomyBudget(
        max_steps=6,
        max_tool_calls=40,
        max_write_operations=6,
        max_command_operations=0,
        max_wall_clock_seconds=1_200,
        max_verification_attempts=2,
        max_branch_attempts=0,
        max_artifact_bytes=4_000_000,
        allowed_risk_buckets=["read_only", "workspace_write"],
    ),
    "test-driven": AutonomyBudget(
        max_steps=8,
        max_tool_calls=60,
        max_write_operations=8,
        max_command_operations=6,
        max_wall_clock_seconds=1_800,
        max_verification_attempts=4,
        max_branch_attempts=1,
        max_artifact_bytes=8_000_000,
        allowed_risk_buckets=["read_only", "workspace_write", "command"],
    ),
    "autonomous-local": AutonomyBudget(
        max_steps=12,
        max_tool_calls=100,
        max_write_operations=16,
        max_command_operations=12,
        max_wall_clock_seconds=3_600,
        max_verification_attempts=6,
        max_branch_attempts=2,
        max_artifact_bytes=16_000_000,
        allowed_risk_buckets=["read_only", "workspace_write", "command"],
    ),
    "release-candidate": AutonomyBudget(
        max_steps=6,
        max_tool_calls=40,
        max_write_operations=2,
        max_command_operations=8,
        max_wall_clock_seconds=2_400,
        max_verification_attempts=6,
        max_branch_attempts=0,
        max_artifact_bytes=12_000_000,
        allowed_risk_buckets=["read_only", "workspace_write", "command"],
    ),
}


def default_budget_for_autonomy_mode(mode: AutonomyMode) -> AutonomyBudget:
    """Return a copy of the built-in budget preset for one mode."""

    return BUILTIN_AUTONOMY_BUDGET_PRESETS[mode.value].model_copy(deep=True)


__all__ = [
    "BUILTIN_AUTONOMY_BUDGET_PRESETS",
    "DEFAULT_AUTONOMY_MODE",
    "default_budget_for_autonomy_mode",
]
