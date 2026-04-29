"""Feedback mapping helpers for the terminal app."""

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import InteractiveClientErrorKind
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus
from glassbox.cli.tui.widgets import ComposerAvailability
from glassbox.cli.tui.widgets import ComposerSubmissionFeedback
from glassbox.cli.tui.widgets import ComposerSubmissionStatus


def feedback_for_blocked_submit(
    availability: ComposerAvailability,
) -> ComposerSubmissionFeedback:
    if availability.disabled_reason in {
        "runtime reconnecting",
        "runtime stream unavailable",
    }:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.UNAVAILABLE_RUNTIME,
            availability.placeholder,
            retryable=True,
        )
    return ComposerSubmissionFeedback(
        ComposerSubmissionStatus.CONFLICT,
        availability.placeholder,
    )


def feedback_for_client_error(
    error: InteractiveClientError,
) -> ComposerSubmissionFeedback:
    if error.kind == InteractiveClientErrorKind.CONFLICT:
        return ComposerSubmissionFeedback(ComposerSubmissionStatus.CONFLICT, str(error))
    if error.kind == InteractiveClientErrorKind.VALIDATION_ERROR:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.VALIDATION_ERROR,
            str(error),
        )
    if error.kind in {
        InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
        InteractiveClientErrorKind.STREAM_UNAVAILABLE,
    }:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.NETWORK_ERROR,
            str(error),
            retryable=True,
        )
    if error.kind in {
        InteractiveClientErrorKind.UNKNOWN_SESSION,
        InteractiveClientErrorKind.HISTORICAL_ONLY,
    }:
        return ComposerSubmissionFeedback(ComposerSubmissionStatus.CONFLICT, str(error))
    return ComposerSubmissionFeedback(
        ComposerSubmissionStatus.RETRYABLE_FAILURE,
        str(error),
        retryable=True,
    )


def action_feedback_for_client_error(
    error: InteractiveClientError,
) -> ActionFeedback:
    if error.kind == InteractiveClientErrorKind.CONFLICT:
        return ActionFeedback(ActionFeedbackStatus.CONFLICT, str(error))
    if error.kind == InteractiveClientErrorKind.VALIDATION_ERROR:
        return ActionFeedback(ActionFeedbackStatus.VALIDATION_ERROR, str(error))
    if error.kind in {
        InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
        InteractiveClientErrorKind.STREAM_UNAVAILABLE,
    }:
        return ActionFeedback(
            ActionFeedbackStatus.NETWORK_ERROR,
            str(error),
            retryable=True,
        )
    if error.kind in {
        InteractiveClientErrorKind.UNKNOWN_SESSION,
        InteractiveClientErrorKind.HISTORICAL_ONLY,
    }:
        return ActionFeedback(ActionFeedbackStatus.CONFLICT, str(error))
    return ActionFeedback(
        ActionFeedbackStatus.RETRYABLE_FAILURE,
        str(error),
        retryable=True,
    )
