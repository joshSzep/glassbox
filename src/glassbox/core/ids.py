"""Identifier aliases and factories for Glassbox domain objects."""

from uuid import UUID
from uuid import uuid4

type SessionId = UUID
type TurnId = UUID
type MessageId = UUID
type ToolCallId = UUID
type ApprovalId = UUID
type QuestionId = UUID
type EventId = UUID
type ArtifactId = UUID
type TaskId = UUID
type TaskStepId = UUID
type TaskVerificationId = UUID
type BudgetOverrideId = UUID


def new_session_id() -> SessionId:
    """Create a new session identifier."""
    return uuid4()


def new_turn_id() -> TurnId:
    """Create a new turn identifier."""
    return uuid4()


def new_message_id() -> MessageId:
    """Create a new message identifier."""
    return uuid4()


def new_tool_call_id() -> ToolCallId:
    """Create a new tool call identifier."""
    return uuid4()


def new_approval_id() -> ApprovalId:
    """Create a new approval identifier."""
    return uuid4()


def new_question_id() -> QuestionId:
    """Create a new user question identifier."""
    return uuid4()


def new_event_id() -> EventId:
    """Create a new event identifier."""
    return uuid4()


def new_artifact_id() -> ArtifactId:
    """Create a new artifact identifier."""
    return uuid4()


def new_task_id() -> TaskId:
    """Create a new task identifier."""
    return uuid4()


def new_task_step_id() -> TaskStepId:
    """Create a new task step identifier."""
    return uuid4()


def new_task_verification_id() -> TaskVerificationId:
    """Create a new task verification identifier."""
    return uuid4()


def new_budget_override_id() -> BudgetOverrideId:
    """Create a new budget override identifier."""
    return uuid4()
