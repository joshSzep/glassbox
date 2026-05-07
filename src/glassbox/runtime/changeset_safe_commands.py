"""Review-loop safe command templates."""

from glassbox.core import ChangesetId
from glassbox.core import ReviewFeedbackId


def show_changeset_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset show {changeset_id} --cwd ."


def changeset_verification_plan_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset verification-plan {changeset_id} --cwd ."


def changeset_brief_command(changeset_id: ChangesetId | str, json: bool = False) -> str:
    if json:
        return f"glassbox changeset brief {changeset_id} --cwd . --json"
    return f"glassbox changeset brief {changeset_id} --cwd ."


def changeset_refresh_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset refresh {changeset_id} --cwd ."


def changeset_feedback_status_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset feedback status {changeset_id} --cwd ."


def changeset_handoff_readiness_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset handoff-readiness {changeset_id} --cwd ."


def changeset_evidence_list_command(changeset_id: ChangesetId | str) -> str:
    return f"glassbox changeset evidence list --changeset {changeset_id} --cwd ."


def changeset_feedback_show_command(feedback_id: ReviewFeedbackId | str) -> str:
    return f"glassbox changeset feedback show {feedback_id} --cwd ."


def tool_attempt_inspect_command(tool_attempt_id: str, session_id: str) -> str:
    return (
        f"glassbox session tool-attempt inspect {tool_attempt_id} "
        f"--session {session_id} --cwd ."
    )
