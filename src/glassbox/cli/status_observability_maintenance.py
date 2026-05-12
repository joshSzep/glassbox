"""Maintenance cue formatting for observability status output."""

from glassbox.runtime.observability import WorkspaceObservabilityReport


def print_maintenance_cues(report: WorkspaceObservabilityReport) -> None:
    """Print compact observability maintenance cues."""

    if not report.maintenance_cues:
        return
    print("Maintenance cues:")
    for cue in report.maintenance_cues[:6]:
        print(
            f"  - {cue.title}: {cue.priority.value}, "
            f"{cue.severity.value}; {cue.summary}"
        )
        if cue.safe_next_actions and cue.safe_next_actions[0].command is not None:
            print(f"    next: {cue.safe_next_actions[0].command.display}")


__all__ = ["print_maintenance_cues"]
