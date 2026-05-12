"""Recovery playbook formatting for observability status output."""

from glassbox.runtime.observability import WorkspaceObservabilityReport


def print_recovery_playbooks(report: WorkspaceObservabilityReport) -> None:
    """Print compact recovery playbook guidance."""

    if not report.recovery_playbooks:
        return
    print("Recovery playbooks:")
    for playbook in report.recovery_playbooks[:6]:
        print(f"  - {playbook.title}: {playbook.summary}")
        first_command = next(
            (step.command for step in playbook.steps if step.command is not None),
            None,
        )
        if first_command is not None:
            print(f"    command: {first_command}")


__all__ = ["print_recovery_playbooks"]
