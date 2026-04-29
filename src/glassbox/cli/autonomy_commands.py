"""Autonomy profile inspection commands."""

import json
from argparse import Namespace

from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.autonomy import BUILTIN_AUTONOMY_BUDGET_PRESETS
from glassbox.runtime.workspace_profile import load_workspace_profile
from glassbox.runtime.workspace_profile import resolve_session_start_defaults


def _autonomy_command(args: Namespace) -> int:
    autonomy_command = getattr(args, "autonomy_command", None)
    if autonomy_command != "profile":
        raise ValueError(f"unsupported autonomy subcommand: {autonomy_command}")
    profile_command = getattr(args, "autonomy_profile_command", None)
    if profile_command == "list":
        return _profile_list_command(args)
    if profile_command == "show":
        return _profile_show_command(args)
    raise ValueError(f"unsupported autonomy profile subcommand: {profile_command}")


def _profile_list_command(args: Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    profile = load_workspace_profile(cwd)
    workspace_presets = profile.autonomy.budget_presets if profile is not None else {}
    payload = {
        "built_in_modes": [
            _budget_payload(name, budget)
            for name, budget in BUILTIN_AUTONOMY_BUDGET_PRESETS.items()
        ],
        "workspace_presets": [
            _budget_payload(name, budget) for name, budget in workspace_presets.items()
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print("Built-in autonomy modes:")
    for item in payload["built_in_modes"]:
        print("  - " + _budget_line(item))
    if payload["workspace_presets"]:
        print("Workspace budget presets:")
        for item in payload["workspace_presets"]:
            print("  - " + _budget_line(item))
    else:
        print("Workspace budget presets: none")
    return 0


def _profile_show_command(args: Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    explicit_mode = (
        args.preset if args.preset in BUILTIN_AUTONOMY_BUDGET_PRESETS else None
    )
    defaults = resolve_session_start_defaults(
        cwd,
        explicit_model_name=None,
        explicit_approval_mode=None,
        explicit_autonomy_mode=explicit_mode,
        explicit_autonomy_budget_preset=args.preset,
    )
    payload = {
        "mode": defaults.autonomy_mode.value,
        "mode_source": defaults.autonomy_mode_source,
        "budget_preset": defaults.autonomy_budget_preset,
        "budget_source": defaults.autonomy_budget_source,
        "budget": defaults.autonomy_budget.model_dump(mode="json"),
        "model_name": defaults.model_name,
        "approval_mode": defaults.approval_mode,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"Autonomy mode: {payload['mode']} ({payload['mode_source']})")
    print(f"Budget preset: {payload['budget_preset']} ({payload['budget_source']})")
    print(
        "Budget: "
        + _budget_line(
            _budget_payload(payload["budget_preset"], defaults.autonomy_budget)
        )
    )
    print(f"Model default: {payload['model_name']}")
    print(f"Approval mode default: {payload['approval_mode']}")
    return 0


def _budget_payload(name, budget) -> dict[str, object]:
    return {
        "name": name,
        "max_steps": budget.max_steps,
        "max_tool_calls": budget.max_tool_calls,
        "max_write_operations": budget.max_write_operations,
        "max_command_operations": budget.max_command_operations,
        "max_wall_clock_seconds": budget.max_wall_clock_seconds,
        "max_verification_attempts": budget.max_verification_attempts,
        "max_branch_attempts": budget.max_branch_attempts,
        "max_artifact_bytes": budget.max_artifact_bytes,
        "allowed_risk_buckets": list(budget.allowed_risk_buckets),
    }


def _budget_line(item: dict[str, object]) -> str:
    risk_buckets = item["allowed_risk_buckets"]
    if not isinstance(risk_buckets, list):
        raise TypeError("allowed_risk_buckets must be a list")
    return (
        f"{item['name']}: steps {item['max_steps']}, "
        f"tools {item['max_tool_calls']}, "
        f"writes {item['max_write_operations']}, "
        f"commands {item['max_command_operations']}, "
        f"risks {', '.join(str(bucket) for bucket in risk_buckets)}"
    )


__all__ = ["_autonomy_command"]
