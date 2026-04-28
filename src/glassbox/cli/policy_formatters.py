"""Shared CLI formatting helpers for policy metadata."""

from glassbox.core.models import PolicyActivitySummary


def format_policy_suffix(
    *,
    outcome: str | None,
    risk_level: str | None,
    source_kind: str | None,
    source_label: str | None,
) -> str:
    """Render one inline policy classification suffix for CLI output."""

    if outcome is None or risk_level is None:
        return ""

    source_suffix = ""
    if source_kind is not None and source_label is not None:
        source_suffix = f" via {source_kind}:{source_label}"
    return f" [{outcome} {risk_level}{source_suffix}]"


def format_policy_summary(summary: PolicyActivitySummary) -> str:
    """Render a compact CLI summary of policy activity counts."""

    if summary.total_decisions == 0:
        return "none"

    highest_risk = summary.highest_risk_level or "n/a"
    return (
        f"{summary.total_decisions} decision(s); "
        f"allow {summary.allow_count}, approve {summary.approve_count}, "
        f"deny {summary.deny_count}, blocked {summary.blocked_count}; "
        f"risk read_only {summary.read_only_count}, "
        f"workspace_write {summary.workspace_write_count}, "
        f"command {summary.command_count}; highest {highest_risk}; "
        "source/reason detail in approvals and recent tool activity"
    )
