"""Typed next-action records for session status output."""

from glassbox.cli.next_action_output import next_action_records_for_cli
from glassbox.core.types import NextActionPriority
from glassbox.core.types import NextActionTargetKind
from glassbox.runtime.session_queries import SessionStatusView


def session_next_action_records(status_view: SessionStatusView):
    snapshot = status_view.snapshot
    commands = ["glassbox queue list --view action-needed --cwd ."]
    if snapshot.pending_question_id is not None:
        commands.append(
            "glassbox session answer "
            f"{snapshot.session_id} {snapshot.pending_question_id} ANSWER --cwd ."
        )
    elif snapshot.pending_approval_id is not None:
        commands.append(
            "glassbox session approve "
            f"{snapshot.session_id} {snapshot.pending_approval_id} --cwd ."
        )
    else:
        commands.append(f"glassbox session status {snapshot.session_id} --cwd .")
    return next_action_records_for_cli(
        commands,
        target_kind=NextActionTargetKind.SESSION,
        target_id=str(snapshot.session_id),
        purpose="Inspect the session posture before taking the next local action.",
        evidence_summary="Session status is derived from the local event log.",
        priority=NextActionPriority.ACTION_NEEDED
        if snapshot.pending_question_id is not None
        or snapshot.pending_approval_id is not None
        else NextActionPriority.RECOMMENDED,
        limitations=[
            "Commands are advisory; mutating commands still require their normal "
            "operator and policy gates."
        ],
    )


__all__ = ["session_next_action_records"]
