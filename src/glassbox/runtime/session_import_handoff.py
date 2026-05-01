"""Handoff-note helpers for imported session packages."""

from glassbox.runtime.session_export import SessionExportPayload


def import_note(package: SessionExportPayload) -> str:
    fragments = [
        f"Imported for inspection from session {package.metadata.session_id}",
        f"original status {package.metadata.status}",
        f"next action: {package.handoff.next_action_summary}",
    ]
    if package.task_summaries:
        fragments.append(f"imported task plans: {len(package.task_summaries)}")
    if package.checkpoint_history:
        fragments.append(f"imported checkpoints: {len(package.checkpoint_history)}")
    if package.handoff.expected_custodian is not None:
        fragments.append(f"expected custodian: {package.handoff.expected_custodian}")
    if package.handoff.note is not None:
        fragments.append(f"handoff note: {package.handoff.note}")
    if package.handoff.summary is not None:
        fragments.append(
            f"latest objective: {package.handoff.summary.latest_objective}"
        )
        fragments.append(
            f"knowledge posture: {package.handoff.summary.knowledge_posture}"
        )
    return "; ".join(fragments)
