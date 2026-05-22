"""Dashboard helpers for terminal handoff actions."""

from typing import Any
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus


def open_handoff_dashboard(app: Any) -> None:
    url = dashboard_handoff_url(app.state.header.dashboard_url)
    if url is None:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.CONFLICT,
                "Dashboard URL is unavailable.",
            )
        )
        return
    try:
        app.open_url(url)
    except Exception as exc:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.RETRYABLE_FAILURE,
                str(exc) or "Handoff dashboard did not open.",
                retryable=True,
            )
        )
        return
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Handoff dashboard opened.")
    )


def dashboard_handoff_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    parts = urlsplit(dashboard_url)
    return urlunsplit((parts.scheme, parts.netloc, "/app/handoffs", "", ""))


__all__ = ["dashboard_handoff_url", "open_handoff_dashboard"]
