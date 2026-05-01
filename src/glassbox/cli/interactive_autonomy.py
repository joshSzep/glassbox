"""Autonomy option resolution for interactive session commands."""

import argparse
from pathlib import Path

from glassbox.core import SessionConfig
from glassbox.runtime.workspace_profile import resolve_session_start_defaults


def build_start_session_config(
    args: argparse.Namespace,
    cwd: Path,
) -> SessionConfig:
    defaults = resolve_session_start_defaults(
        cwd,
        explicit_model_name=args.model_name,
        explicit_approval_mode=args.approval_mode,
        explicit_autonomy_mode=getattr(args, "autonomy_mode", None),
        explicit_autonomy_budget_preset=getattr(args, "autonomy_budget_preset", None),
    )
    return SessionConfig(
        model_name=defaults.model_name,
        cwd=cwd,
        approval_mode=defaults.approval_mode,
        autonomy_mode=defaults.autonomy_mode,
        autonomy_budget=defaults.autonomy_budget,
        autonomy_budget_preset=defaults.autonomy_budget_preset,
    )


def build_ad_hoc_autonomy_config(
    args: argparse.Namespace,
    cwd: Path,
) -> SessionConfig | None:
    autonomy_mode = getattr(args, "autonomy_mode", None)
    autonomy_budget_preset = getattr(args, "autonomy_budget_preset", None)
    if not (autonomy_mode or autonomy_budget_preset):
        return None
    defaults = resolve_session_start_defaults(
        cwd,
        explicit_model_name=None,
        explicit_approval_mode=None,
        explicit_autonomy_mode=autonomy_mode,
        explicit_autonomy_budget_preset=autonomy_budget_preset,
    )
    return SessionConfig(
        model_name=defaults.model_name,
        cwd=cwd,
        approval_mode=defaults.approval_mode,
        autonomy_mode=defaults.autonomy_mode,
        autonomy_budget=defaults.autonomy_budget,
        autonomy_budget_preset=defaults.autonomy_budget_preset,
    )


def print_autonomy_config_summary(config: SessionConfig) -> None:
    budget = config.autonomy_budget
    if budget is None:
        print(f"Autonomy: {config.autonomy_mode.value}; budget unavailable")
        return
    print(
        "Autonomy: "
        f"{config.autonomy_mode.value}; "
        f"budget {config.autonomy_budget_preset or config.autonomy_mode.value}; "
        f"steps {budget.max_steps}, tools {budget.max_tool_calls}, "
        f"writes {budget.max_write_operations}, "
        f"commands {budget.max_command_operations}"
    )


__all__ = [
    "build_ad_hoc_autonomy_config",
    "build_start_session_config",
    "print_autonomy_config_summary",
]
