"""Local handoff Pydantic contracts shared across Glassbox surfaces."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from glassbox.core.models_operator_flow import NextActionEvidenceRef
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.core.types_handoff import HandoffCustodyState
from glassbox.core.types_handoff import HandoffEvidenceFreshness
from glassbox.core.types_handoff import HandoffIntent
from glassbox.core.types_handoff import HandoffLabelMetadataPosture
from glassbox.core.types_handoff import HandoffLabelSource
from glassbox.core.types_handoff import HandoffPackageKind
from glassbox.core.types_handoff import HandoffReadinessReasonKind
from glassbox.core.types_handoff import HandoffReadinessState
from glassbox.core.types_handoff import HandoffRedactionPosture
from glassbox.core.types_handoff import HandoffSourceKind

HANDOFF_MANIFEST_SCHEMA_VERSION = "glassbox-handoff-package.v2"
HANDOFF_PACKAGE_FORMAT = "glassbox_handoff_package"
HANDOFF_PACKAGE_SCHEMA_VERSION = 2
HANDOFF_DEFAULT_NON_CLAIMS = [
    "handoff does not grant continuation authority",
    "handoff does not approve review, verification, release, or publication",
    "handoff does not prove source workspace completeness",
    "handoff does not include raw local evidence unless explicitly declared",
]


class HandoffLabel(BaseModel):
    """Recipient, custodian, exporter, or actor label for local coordination."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)
    source: HandoffLabelSource = HandoffLabelSource.OPERATOR
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    metadata_posture: HandoffLabelMetadataPosture = HandoffLabelMetadataPosture.PORTABLE
    local_only_metadata: bool = False
    note: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_metadata_posture(self) -> HandoffLabel:
        if self.local_only_metadata and (
            self.metadata_posture != HandoffLabelMetadataPosture.LOCAL_ONLY
        ):
            raise ValueError(
                "local_only_metadata labels must use local-only metadata posture"
            )
        return self


class HandoffSourceRef(BaseModel):
    """Stable source reference for a handoff package or readiness result."""

    model_config = ConfigDict(extra="forbid")

    kind: HandoffSourceKind
    primary_id: str | None = Field(default=None, min_length=1, max_length=300)
    identifiers: dict[str, str] = Field(default_factory=dict, max_length=20)
    label: str | None = Field(default=None, min_length=1, max_length=300)


class HandoffSafeCommand(BaseModel):
    """Safe inspection command shown before any handoff mutation."""

    model_config = ConfigDict(extra="forbid")

    command: list[str] = Field(min_length=1, max_length=64)
    display: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1, max_length=1000)
    read_only: bool = True
    requires_policy_approval: bool = False

    @model_validator(mode="after")
    def validate_safe_command(self) -> HandoffSafeCommand:
        if not self.read_only:
            raise ValueError("handoff safe commands must be read-only")
        return self


class HandoffReadinessReason(BaseModel):
    """One bounded reason supporting or limiting handoff readiness."""

    model_config = ConfigDict(extra="forbid")

    kind: HandoffReadinessReasonKind
    summary: str = Field(min_length=1, max_length=2000)
    evidence: list[NextActionEvidenceRef] = Field(default_factory=list, max_length=20)
    affected_claim_ids: list[str] = Field(default_factory=list, max_length=50)
    limitation: str | None = Field(default=None, min_length=1, max_length=1000)
    portable: bool = True


class HandoffReadiness(BaseModel):
    """Shared handoff readiness contract for sessions, tasks, and changesets."""

    model_config = ConfigDict(extra="forbid")

    source: HandoffSourceRef
    intent: HandoffIntent
    state: HandoffReadinessState
    confidence: RepositoryIntelligenceConfidence = (
        RepositoryIntelligenceConfidence.UNKNOWN
    )
    freshness: HandoffEvidenceFreshness = HandoffEvidenceFreshness.UNKNOWN
    recipient: HandoffLabel | None = None
    expected_custodian: HandoffLabel | None = None
    reasons: list[HandoffReadinessReason] = Field(
        default_factory=list,
        max_length=50,
    )
    supporting_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=50,
    )
    missing_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=50,
    )
    stale_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=50,
    )
    local_only_evidence: list[HandoffReadinessReason] = Field(
        default_factory=list,
        max_length=50,
    )
    accepted_risks: list[HandoffReadinessReason] = Field(
        default_factory=list,
        max_length=50,
    )
    limitations: list[str] = Field(default_factory=list, max_length=50)
    safe_first_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )
    non_claims: list[str] = Field(
        default_factory=lambda: list(HANDOFF_DEFAULT_NON_CLAIMS),
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_state_evidence(self) -> HandoffReadiness:
        if (
            self.state == HandoffReadinessState.LOCAL_ONLY_EVIDENCE
            and not self.local_only_evidence
        ):
            raise ValueError(
                "local-only handoff readiness must include local_only_evidence"
            )
        if (
            self.state == HandoffReadinessState.ACCEPTED_WITH_RISK
            and not self.accepted_risks
        ):
            raise ValueError(
                "accepted-with-risk handoff readiness must include accepted_risks"
            )
        return self


class HandoffRedactionSummary(BaseModel):
    """Portable redaction and raw-inclusion posture for a package manifest."""

    model_config = ConfigDict(extra="forbid")

    posture: HandoffRedactionPosture = HandoffRedactionPosture.UNKNOWN
    redacted_field_count: int = Field(default=0, ge=0)
    redacted_categories: list[str] = Field(default_factory=list, max_length=50)
    raw_transcript_included: bool = False
    raw_logs_included: bool = False
    raw_artifacts_included: bool = False
    raw_diffs_included: bool = False
    screenshots_included: bool = False
    provider_output_included: bool = False
    limitations: list[str] = Field(default_factory=list, max_length=50)


class HandoffLocalOnlySummary(BaseModel):
    """Summary of evidence that exists locally but did not travel."""

    model_config = ConfigDict(extra="forbid")

    category_counts: dict[str, int] = Field(default_factory=dict, max_length=50)
    affected_claim_ids: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=50)
    safe_local_inspection_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )


class HandoffCompatibilitySummary(BaseModel):
    """Compatibility posture for a package manifest."""

    model_config = ConfigDict(extra="forbid")

    state: HandoffCompatibilityState = HandoffCompatibilityState.SUPPORTED
    supported_sections: list[str] = Field(default_factory=list, max_length=100)
    unsupported_sections: list[str] = Field(default_factory=list, max_length=100)
    missing_optional_sections: list[str] = Field(default_factory=list, max_length=100)
    unsupported_values: list[str] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_unsupported_state(self) -> HandoffCompatibilitySummary:
        if self.state in {
            HandoffCompatibilityState.UNSUPPORTED,
            HandoffCompatibilityState.FUTURE_VERSION,
            HandoffCompatibilityState.INVALID,
        } and not (
            self.unsupported_sections or self.unsupported_values or self.warnings
        ):
            raise ValueError(
                "unsupported compatibility states must include a warning, "
                "unsupported section, or unsupported value"
            )
        return self


class HandoffDigestSummary(BaseModel):
    """Package integrity digests, not proof of source workspace completeness."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str = Field(default="sha256", min_length=1, max_length=40)
    manifest_digest: str | None = Field(default=None, min_length=1, max_length=256)
    payload_digest: str | None = Field(default=None, min_length=1, max_length=256)
    package_digest: str | None = Field(default=None, min_length=1, max_length=256)
    verified: bool = False
    limitations: list[str] = Field(default_factory=list, max_length=20)


class HandoffPackageManifest(BaseModel):
    """Stable manifest metadata for portable local handoff packages."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(
        default=HANDOFF_MANIFEST_SCHEMA_VERSION,
        min_length=1,
        max_length=80,
    )
    package_kind: HandoffPackageKind
    source: HandoffSourceRef
    generated_at: datetime
    intent: HandoffIntent
    recipient: HandoffLabel | None = None
    expected_custodian: HandoffLabel | None = None
    exported_by: HandoffLabel | None = None
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    readiness: HandoffReadiness | None = None
    included_sections: list[str] = Field(default_factory=list, max_length=100)
    unsupported_sections: list[str] = Field(default_factory=list, max_length=100)
    redaction: HandoffRedactionSummary = Field(
        default_factory=HandoffRedactionSummary,
    )
    local_only: HandoffLocalOnlySummary = Field(
        default_factory=HandoffLocalOnlySummary,
    )
    compatibility: HandoffCompatibilitySummary = Field(
        default_factory=HandoffCompatibilitySummary,
    )
    digest: HandoffDigestSummary = Field(default_factory=HandoffDigestSummary)
    safe_inspection_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )
    non_claims: list[str] = Field(
        default_factory=lambda: list(HANDOFF_DEFAULT_NON_CLAIMS),
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_manifest_alignment(self) -> HandoffPackageManifest:
        if self.readiness is not None:
            if self.readiness.intent != self.intent:
                raise ValueError("manifest intent must match readiness intent")
            if self.readiness.source.kind != self.source.kind:
                raise ValueError(
                    "manifest source kind must match readiness source kind"
                )
        return self


class HandoffPackageV2(BaseModel):
    """Portable v2 handoff package wrapper."""

    model_config = ConfigDict(extra="forbid")

    package_format: str = Field(
        default=HANDOFF_PACKAGE_FORMAT,
        min_length=1,
        max_length=80,
    )
    schema_version: int = Field(default=HANDOFF_PACKAGE_SCHEMA_VERSION, ge=2)
    manifest: HandoffPackageManifest
    payload_sections: dict[str, object] = Field(default_factory=dict, max_length=100)

    @model_validator(mode="after")
    def validate_package_version(self) -> HandoffPackageV2:
        if self.package_format != HANDOFF_PACKAGE_FORMAT:
            raise ValueError("unsupported handoff package format")
        if self.schema_version != HANDOFF_PACKAGE_SCHEMA_VERSION:
            raise ValueError("unsupported handoff package schema version")
        return self


class HandoffProjectionRecord(BaseModel):
    """Latest local workflow posture for one handoff package."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=80)
    package_id: str = Field(min_length=1, max_length=300)
    source_kind: HandoffSourceKind
    source_id: str | None = Field(default=None, min_length=1, max_length=300)
    task_id: str | None = Field(default=None, min_length=1, max_length=80)
    changeset_id: str | None = Field(default=None, min_length=1, max_length=80)
    package_kind: HandoffPackageKind | None = None
    intent: HandoffIntent | None = None
    artifact_id: str | None = Field(default=None, min_length=1, max_length=80)
    package_digest: str | None = Field(default=None, min_length=1, max_length=256)
    compatibility_state: HandoffCompatibilityState | None = None
    redaction_posture: HandoffRedactionPosture | None = None
    local_only_count: int = Field(default=0, ge=0)
    custody_state: HandoffCustodyState
    expected_custodian: str | None = Field(default=None, min_length=1, max_length=200)
    current_custodian: str | None = Field(default=None, min_length=1, max_length=200)
    exported_by: str | None = Field(default=None, min_length=1, max_length=200)
    decision_by: str | None = Field(default=None, min_length=1, max_length=200)
    decision_reason: str | None = Field(default=None, min_length=1, max_length=2000)
    follow_up_intent: HandoffIntent | None = None
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    imported: bool = False
    archived: bool = False
    created_at: datetime
    updated_at: datetime
    last_event_type: str = Field(min_length=1, max_length=120)
    last_sequence: int = Field(ge=0)


__all__ = [
    "HANDOFF_DEFAULT_NON_CLAIMS",
    "HANDOFF_MANIFEST_SCHEMA_VERSION",
    "HANDOFF_PACKAGE_FORMAT",
    "HANDOFF_PACKAGE_SCHEMA_VERSION",
    "HandoffCompatibilitySummary",
    "HandoffDigestSummary",
    "HandoffLabel",
    "HandoffLocalOnlySummary",
    "HandoffPackageManifest",
    "HandoffPackageV2",
    "HandoffProjectionRecord",
    "HandoffReadiness",
    "HandoffReadinessReason",
    "HandoffRedactionSummary",
    "HandoffSafeCommand",
    "HandoffSourceRef",
]
