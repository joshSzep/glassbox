"""Hydrate terminal conversation state from initial snapshots."""

from uuid import UUID

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation_models import PendingQuestionState
from glassbox.cli.tui.conversation_models import TerminalConversationState
from glassbox.cli.tui.conversation_models import TerminalHeaderState
from glassbox.cli.tui.conversation_models import TerminalMode
from glassbox.cli.tui.conversation_selectors import mode_from_session_status
from glassbox.cli.tui.conversation_selectors import stream_status_from_session_status
from glassbox.core.types import SessionStatus


def conversation_state_from_snapshot(
    snapshot: InteractiveSessionSnapshot,
) -> TerminalConversationState:
    status = snapshot.state.status
    stream_status = stream_status_from_session_status(status)
    mode = mode_from_session_status(status)
    if status == SessionStatus.RUNNING and snapshot.state.current_turn_id is not None:
        mode = TerminalMode.THINKING
    return TerminalConversationState(
        header=TerminalHeaderState(
            session_id=snapshot.session_id,
            status=status,
            mode=mode,
            stream_status=stream_status,
            model_name=snapshot.model_name,
            cwd=snapshot.cwd,
            approval_mode=snapshot.approval_mode,
            dashboard_url=snapshot.dashboard_url,
            current_turn_id=snapshot.state.current_turn_id,
            last_sequence=snapshot.last_sequence,
        ),
        pending_question=(
            PendingQuestionState(
                question_id=snapshot.state.pending_question_id,
                turn_id=snapshot.state.current_turn_id or UUID(int=0),
                tool_call_id=UUID(int=0),
                question=snapshot.pending_question_text or "",
                sequence=snapshot.last_sequence,
            )
            if snapshot.state.pending_question_id is not None
            else None
        ),
    )
