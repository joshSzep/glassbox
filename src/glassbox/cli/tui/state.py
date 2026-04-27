"""State containers owned by the Textual app shell."""

from dataclasses import dataclass

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchOptions


@dataclass(frozen=True, slots=True)
class TerminalAppState:
    session_id: str
    status: str
    last_sequence: int
    model_name: str | None
    cwd: str | None
    approval_mode: str | None
    dashboard_url: str | None
    pending_question_text: str | None
    launch_options: InteractiveLaunchOptions

    @classmethod
    def from_snapshot(
        cls,
        snapshot: InteractiveSessionSnapshot,
        *,
        launch_options: InteractiveLaunchOptions,
        dashboard_url: str | None = None,
    ) -> TerminalAppState:
        return cls(
            session_id=str(snapshot.session_id),
            status=snapshot.state.status.value,
            last_sequence=snapshot.last_sequence,
            model_name=snapshot.model_name,
            cwd=snapshot.cwd,
            approval_mode=snapshot.approval_mode,
            dashboard_url=dashboard_url or snapshot.dashboard_url,
            pending_question_text=snapshot.pending_question_text,
            launch_options=launch_options,
        )
