"""Typed next-action records for observability status output."""

from glassbox.cli.next_action_output import next_action_records_for_cli
from glassbox.core import NextActionPriority
from glassbox.core import NextActionTargetKind
from glassbox.runtime.observability import WorkspaceObservabilityReport


def observability_next_action_records(report: WorkspaceObservabilityReport):
    return next_action_records_for_cli(
        report.next_actions,
        target_kind=NextActionTargetKind.WORKSPACE,
        target_id=str(report.workspace_root),
        purpose=(
            "Inspect workspace health before running maintenance or recovery commands."
        ),
        evidence_summary=(
            "Observability status aggregates local runtime, projection, job, and "
            "knowledge posture."
        ),
        priority=NextActionPriority.ACTION_NEEDED
        if report.next_actions
        else NextActionPriority.RECOMMENDED,
        limitations=["Status rendering does not run maintenance actions."],
    )


__all__ = ["observability_next_action_records"]
