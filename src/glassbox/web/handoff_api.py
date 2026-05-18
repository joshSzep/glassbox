"""API models for local handoff workflows."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffReadiness
from glassbox.runtime.handoff_guidance import HandoffGuidance
from glassbox.runtime.handoff_import_triage import HandoffImportTriage
from glassbox.runtime.handoff_redaction_preview import HandoffRedactionPreview
from glassbox.runtime.session_import import SessionImportResult


class HandoffRecordResponse(BaseModel):
    """Projected handoff record plus dashboard action state."""

    model_config = ConfigDict(extra="forbid")

    record: HandoffProjectionRecord
    action_state: str = Field(min_length=1, max_length=120)


class HandoffListResponse(BaseModel):
    """Bounded list of projected handoff records."""

    model_config = ConfigDict(extra="forbid")

    items: list[HandoffRecordResponse] = Field(default_factory=list, max_length=500)


class HandoffAcceptRequest(BaseModel):
    """Request to accept local custody or imported follow-up."""

    model_config = ConfigDict(extra="forbid")

    accepted_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    follow_up_intent: HandoffIntent | None = None


class HandoffRejectRequest(BaseModel):
    """Request to reject local custody with a retained reason."""

    model_config = ConfigDict(extra="forbid")

    rejected_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class HandoffArchiveRequest(BaseModel):
    """Request to archive a handoff as historical workflow evidence."""

    model_config = ConfigDict(extra="forbid")

    archived_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class HandoffDecisionResponse(BaseModel):
    """Response for a recorded handoff custody decision."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=120)
    handoff: HandoffRecordResponse
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class HandoffGuidanceResponse(BaseModel):
    """Dashboard/API fork-or-continue guidance."""

    model_config = ConfigDict(extra="forbid")

    guidance: HandoffGuidance


class HandoffProfileRequest(BaseModel):
    """Shared recipient profile metadata for handoff prepare routes."""

    model_config = ConfigDict(extra="forbid")

    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY
    recipient: str | None = Field(default=None, min_length=1, max_length=200)
    exported_by: str | None = Field(default=None, min_length=1, max_length=200)
    expected_custodian: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    output_format: str = Field(default="json", min_length=1, max_length=40)


class HandoffPreparePreviewRequest(HandoffProfileRequest):
    """Request a redaction and local-only preview before export."""

    source_kind: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=200)


class HandoffPreparePreviewResponse(BaseModel):
    """Redaction and local-only preview for a prepared handoff."""

    model_config = ConfigDict(extra="forbid")

    preview: HandoffRedactionPreview


class HandoffExportRequest(HandoffPreparePreviewRequest):
    """Write a handoff package through the API."""

    output_path: str | None = Field(default=None, min_length=1, max_length=1000)
    markdown_output_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )


class HandoffExportResponse(BaseModel):
    """Result of writing a handoff package."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=200)
    output_path: str = Field(min_length=1, max_length=1000)
    markdown_output_path: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="exported", min_length=1, max_length=40)


class HandoffPackagePathRequest(BaseModel):
    """Request body for local package path inspection."""

    model_config = ConfigDict(extra="forbid")

    package_path: str = Field(min_length=1, max_length=1000)


class HandoffChangesetPackageSummary(BaseModel):
    """Reviewer-safe changeset package inspection summary."""

    model_config = ConfigDict(extra="forbid")

    bundle_path: str | None = Field(default=None, max_length=1000)
    export_kind: str = Field(min_length=1, max_length=120)
    schema_version: int
    changeset_id: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=120)
    verification_state: str = Field(min_length=1, max_length=120)
    handoff_state: str = Field(min_length=1, max_length=120)
    feedback_count: int = Field(ge=0)
    manual_evidence_count: int = Field(ge=0)
    profile_id: str | None = Field(default=None, max_length=120)
    local_only_evidence_count: int = Field(ge=0)
    evidence_graph_node_count: int = Field(ge=0)
    evidence_graph_claim_count: int = Field(ge=0)
    redaction_report_count: int = Field(ge=0)
    non_claims: list[str] = Field(default_factory=list, max_length=50)
    safe_inspection_commands: list[str] = Field(default_factory=list, max_length=50)


class HandoffPackageInspectResponse(BaseModel):
    """Inspection-first response for a local handoff package path."""

    model_config = ConfigDict(extra="forbid")

    package_path: str = Field(min_length=1, max_length=1000)
    package_family: str = Field(min_length=1, max_length=80)
    triage: HandoffImportTriage | None = None
    changeset_summary: HandoffChangesetPackageSummary | None = None


class HandoffImportTriageResponse(BaseModel):
    """Import triage response that performs no mutation."""

    model_config = ConfigDict(extra="forbid")

    triage: HandoffImportTriage


class HandoffImportResponse(BaseModel):
    """Response for importing a session handoff into inspection state."""

    model_config = ConfigDict(extra="forbid")

    result: SessionImportResult


class HandoffReadinessUnifiedResponse(BaseModel):
    """Shared v17 handoff readiness response for local sources."""

    model_config = ConfigDict(extra="forbid")

    readiness: HandoffReadiness


__all__ = [
    "HandoffAcceptRequest",
    "HandoffArchiveRequest",
    "HandoffChangesetPackageSummary",
    "HandoffDecisionResponse",
    "HandoffExportRequest",
    "HandoffExportResponse",
    "HandoffGuidanceResponse",
    "HandoffImportResponse",
    "HandoffImportTriageResponse",
    "HandoffListResponse",
    "HandoffPackageInspectResponse",
    "HandoffPackagePathRequest",
    "HandoffPreparePreviewRequest",
    "HandoffPreparePreviewResponse",
    "HandoffProfileRequest",
    "HandoffReadinessUnifiedResponse",
    "HandoffRecordResponse",
    "HandoffRejectRequest",
]
