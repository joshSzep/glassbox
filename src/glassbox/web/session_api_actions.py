"""Action request and response models for the session API."""

from uuid import UUID

from pydantic import BaseModel

from glassbox.web.session_api_common import ContextCompactionResponse
from glassbox.web.session_api_common import ToolAttemptArtifactReferenceResponse
from glassbox.web.session_api_common import ToolAttemptResponse


class ToolAttemptInspectionResponse(BaseModel):
    attempt: ToolAttemptResponse
    source_tool_call_id: str | None = None
    source_arguments: dict[str, object] | None = None
    output_artifact: ToolAttemptArtifactReferenceResponse | None = None
    correlated_event_count: int
    recovery_actions: list[str]


class ToolAttemptRecoveryRequest(BaseModel):
    reason: str | None = None
    actor: str = "operator"
    confirmed: bool = False


class ToolAttemptAbandonRequest(BaseModel):
    reason: str
    actor: str = "operator"
    confirmed: bool = False


class ToolAttemptRecoveryResponse(BaseModel):
    message: str
    original_attempt: ToolAttemptResponse
    retry_attempt: ToolAttemptResponse | None = None


class ForkSessionRequest(BaseModel):
    turn_id: UUID | None = None
    branch_label: str | None = None


class ForkSessionResponse(BaseModel):
    child_session_id: str
    parent_session_id: str
    forked_from_turn_id: str
    forked_from_sequence: int
    branch_label: str | None
    inherited_message_count: int
    last_sequence: int


class SubmitSessionMessageRequest(BaseModel):
    text: str


class SubmitSessionAnswerRequest(BaseModel):
    answer: str


class CancelSessionTurnRequest(BaseModel):
    turn_id: UUID | None = None
    reason: str | None = None


class ActionAcceptedResponse(BaseModel):
    status: str


class ErrorDetailResponse(BaseModel):
    detail: str | dict[str, object]


class RefreshContextCompactionRequest(BaseModel):
    reason: str | None = None
    confirmed: bool = False


class RefreshContextCompactionResponse(BaseModel):
    refreshed_compaction: ContextCompactionResponse
    previous_compaction_id: str
    previous_freshness: str
    previous_freshness_reason: str
    superseded_by_compaction_id: str


class InvalidateContextCompactionRequest(BaseModel):
    reason: str
    confirmed: bool = False


class InvalidateContextCompactionResponse(BaseModel):
    compaction_id: str
    freshness: str
    freshness_reason: str
