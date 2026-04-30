"""Startup summary formatting for interactive chat sessions."""

from pathlib import Path
from uuid import UUID

from glassbox.core import SessionConfig
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.tools import describe_effective_approval_behavior


def chat_startup_summary_lines(
    *,
    session_id: UUID,
    config: SessionConfig,
    database_path: Path,
    dashboard_url: str | None,
    dashboard_disabled: bool,
    dashboard_asset_problems: list[str],
    provider_report: ProviderDiagnosticsReport,
    include_prompt_suggestions: bool,
) -> list[str]:
    """Return a compact operator-facing chat startup summary."""

    lines = [
        "Glassbox chat ready",
        f"Session: {session_id}",
        f"Model: {config.model_name}",
        "Approval: "
        + describe_effective_approval_behavior(
            config.approval_mode,
            autonomy_mode=config.autonomy_mode,
            budget=config.autonomy_budget,
        ),
        _autonomy_summary_line(config),
        f"Workspace: {config.cwd}",
        f"Database: {database_path}",
        _dashboard_summary_line(
            session_id=session_id,
            dashboard_url=dashboard_url,
            dashboard_disabled=dashboard_disabled,
            dashboard_asset_problems=dashboard_asset_problems,
        ),
        _provider_summary_line(provider_report),
    ]
    if include_prompt_suggestions:
        lines.extend(
            [
                "Prompt ideas:",
                "  - Inspect this repository and summarize safe next steps.",
                "  - Run the smallest useful verification for my current changes.",
            ]
        )
    return lines


def print_chat_startup_summary(
    *,
    session_id: UUID,
    config: SessionConfig,
    database_path: Path,
    dashboard_url: str | None,
    dashboard_disabled: bool,
    dashboard_asset_problems: list[str],
    provider_report: ProviderDiagnosticsReport,
    include_prompt_suggestions: bool,
) -> None:
    """Print the startup summary for an interactive chat session."""

    for line in chat_startup_summary_lines(
        session_id=session_id,
        config=config,
        database_path=database_path,
        dashboard_url=dashboard_url,
        dashboard_disabled=dashboard_disabled,
        dashboard_asset_problems=dashboard_asset_problems,
        provider_report=provider_report,
        include_prompt_suggestions=include_prompt_suggestions,
    ):
        print(line)


def _autonomy_summary_line(config: SessionConfig) -> str:
    budget = config.autonomy_budget
    if budget is None:
        return f"Autonomy: {config.autonomy_mode.value}; budget unavailable"
    return (
        "Autonomy: "
        f"{config.autonomy_mode.value}; "
        f"budget {config.autonomy_budget_preset or config.autonomy_mode.value}; "
        f"steps {budget.max_steps}, tools {budget.max_tool_calls}, "
        f"writes {budget.max_write_operations}, "
        f"commands {budget.max_command_operations}"
    )


def _dashboard_summary_line(
    *,
    session_id: UUID,
    dashboard_url: str | None,
    dashboard_disabled: bool,
    dashboard_asset_problems: list[str],
) -> str:
    if dashboard_disabled:
        return "Dashboard: disabled by --no-dashboard; omit it to launch the cockpit"
    if dashboard_url is None:
        return "Dashboard: unavailable; inspect the warning above or rerun readiness"

    line = f"Dashboard: {dashboard_url}?session={session_id}"
    if dashboard_asset_problems:
        line += f" (asset warning: {dashboard_asset_problems[0]})"
    return line


def _provider_summary_line(report: ProviderDiagnosticsReport) -> str:
    if report.state == "ready":
        return f"Provider: {report.runtime_mode} ready ({report.selected_model_name})"
    if report.state == "local_fallback":
        return f"Provider: local fallback for {report.selected_model_name}; " + (
            report.next_actions[0] if report.next_actions else "run readiness"
        )
    if report.next_actions:
        return f"Provider: {report.state}; next: {report.next_actions[0]}"
    return f"Provider: {report.state}"


__all__ = ["chat_startup_summary_lines", "print_chat_startup_summary"]
