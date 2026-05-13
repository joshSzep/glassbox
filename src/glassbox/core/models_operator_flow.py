"""Operator-flow Pydantic contracts shared across Glassbox surfaces."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types_evidence_graph import ClaimSupportState
from glassbox.core.types_operator_flow import MaintenanceCueKind
from glassbox.core.types_operator_flow import NextActionEvidenceKind
from glassbox.core.types_operator_flow import NextActionKind
from glassbox.core.types_operator_flow import NextActionPriority
from glassbox.core.types_operator_flow import NextActionSafetyClass
from glassbox.core.types_operator_flow import NextActionSeverity
from glassbox.core.types_operator_flow import NextActionSurface
from glassbox.core.types_operator_flow import NextActionTargetKind
from glassbox.core.types_operator_flow import OperatorQueueDedupeScope
from glassbox.core.types_operator_flow import OperatorQueueDismissalPolicy
from glassbox.core.types_operator_flow import OperatorQueueFamily
from glassbox.core.types_operator_flow import OperatorQueueState


class NextActionTarget(BaseModel):
    """Local object or surface a next action is about."""

    model_config = ConfigDict(extra="forbid")

    kind: NextActionTargetKind
    target_id: str | None = Field(default=None, min_length=1, max_length=300)
    label: str | None = Field(default=None, min_length=1, max_length=300)


class NextActionEvidenceRef(BaseModel):
    """Compact local evidence reference for next-action support."""

    model_config = ConfigDict(extra="forbid")

    kind: NextActionEvidenceKind
    ref_id: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    source_path: str | None = Field(default=None, min_length=1, max_length=500)
    freshness: str | None = Field(default=None, min_length=1, max_length=80)
    redaction: str | None = Field(default=None, min_length=1, max_length=120)
    reviewer_safe: bool = True


class NextActionCommandRecipe(BaseModel):
    """Advisory command shape attached to a next action."""

    model_config = ConfigDict(extra="forbid")

    command: list[str] = Field(min_length=1, max_length=64)
    display: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1, max_length=1000)
    safety_class: NextActionSafetyClass = NextActionSafetyClass.COMMAND_RECIPE
    requires_approval: bool = True
    expected_exit_codes: list[int] = Field(default_factory=lambda: [0], min_length=1)
    timeout_seconds: int | None = Field(default=None, ge=1, le=7200)
    cwd_hint: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("expected_exit_codes")
    @classmethod
    def normalize_expected_exit_codes(cls, value: list[int]) -> list[int]:
        normalized = list(dict.fromkeys(value))
        if not normalized:
            raise ValueError("expected_exit_codes must not be empty")
        for exit_code in normalized:
            if exit_code < 0 or exit_code > 255:
                raise ValueError("expected_exit_codes must be between 0 and 255")
        return normalized

    @model_validator(mode="after")
    def validate_command_recipe_safety(self) -> NextActionCommandRecipe:
        if self.safety_class == NextActionSafetyClass.PUBLICATION_BLOCKED:
            raise ValueError(
                "publication-blocked actions must not carry command recipes"
            )
        return self


class NextAction(BaseModel):
    """Shared advisory next-action contract for operator-facing surfaces."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    kind: NextActionKind
    priority: NextActionPriority
    severity: NextActionSeverity = NextActionSeverity.INFO
    safety_class: NextActionSafetyClass = NextActionSafetyClass.READ_ONLY
    target: NextActionTarget
    command: NextActionCommandRecipe | None = None
    supporting_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    missing_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    stale_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    limitations: list[str] = Field(default_factory=list, max_length=20)
    recommended_surfaces: list[NextActionSurface] = Field(
        default_factory=list,
        max_length=10,
    )
    confidence: RepositoryIntelligenceConfidence = (
        RepositoryIntelligenceConfidence.UNKNOWN
    )
    reviewer_safe: bool = True

    @model_validator(mode="after")
    def validate_command_boundary(self) -> NextAction:
        if self.command is None:
            return self
        if self.safety_class not in {
            NextActionSafetyClass.COMMAND_RECIPE,
            NextActionSafetyClass.OPERATOR_DECISION,
        }:
            raise ValueError(
                "next actions with commands must use command_recipe or "
                "operator_decision safety"
            )
        return self


class OperatorQueueEvidenceSummary(BaseModel):
    """Bounded evidence summary attached to a unified operator queue item."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    support_state: ClaimSupportState | None = None
    evidence_graph_id: str | None = Field(default=None, min_length=1, max_length=300)
    claim_id: str | None = Field(default=None, min_length=1, max_length=300)
    supporting_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    missing_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    stale_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    limitation_count: int = Field(default=0, ge=0)


class OperatorQueueDedupeKey(BaseModel):
    """Stable merge key for queue items about the same underlying problem."""

    model_config = ConfigDict(extra="forbid")

    scope: OperatorQueueDedupeScope
    key: str = Field(min_length=1, max_length=500)
    target: NextActionTarget


class OperatorQueueItem(BaseModel):
    """Shared contract for one derived operator attention item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=300)
    family: OperatorQueueFamily
    state: OperatorQueueState
    priority: NextActionPriority
    severity: NextActionSeverity = NextActionSeverity.INFO
    target: NextActionTarget
    owner_surface: NextActionSurface
    owner_label: str = Field(min_length=1, max_length=300)
    safe_next_action: NextAction
    evidence_summary: OperatorQueueEvidenceSummary
    dedupe_key: OperatorQueueDedupeKey
    dismissal_policy: OperatorQueueDismissalPolicy = (
        OperatorQueueDismissalPolicy.NOT_DISMISSIBLE
    )
    action_needed: bool = False
    blocking: bool = False
    stale: bool = False
    updated_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_operator_queue_item(self) -> OperatorQueueItem:
        action_target = self.safe_next_action.target
        if action_target.kind != self.target.kind:
            raise ValueError("queue item action target kind must match item target")
        if (
            self.target.target_id is not None
            and action_target.target_id is not None
            and action_target.target_id != self.target.target_id
        ):
            raise ValueError("queue item action target id must match item target")
        if self.dedupe_key.target.kind != self.target.kind:
            raise ValueError("queue item dedupe target kind must match item target")
        if (
            self.family
            in {
                OperatorQueueFamily.WORK_BLOCKING,
                OperatorQueueFamily.REVIEW_BLOCKING,
                OperatorQueueFamily.VERIFICATION_BLOCKING,
            }
            and not self.blocking
        ):
            raise ValueError("blocking queue families must set blocking=true")
        if self.action_needed and self.priority in {
            NextActionPriority.OPTIONAL,
            NextActionPriority.HISTORICAL,
        }:
            raise ValueError("action-needed queue items must not be optional")
        if self.stale and self.state not in {
            OperatorQueueState.STALE,
            OperatorQueueState.DEGRADED,
            OperatorQueueState.BLOCKED,
        }:
            raise ValueError("stale queue items must use stale/degraded/blocked state")
        return self


class MaintenanceCue(BaseModel):
    """Typed maintenance or recovery cue surfaced beside active work."""

    model_config = ConfigDict(extra="forbid")

    cue_id: str = Field(min_length=1, max_length=300)
    kind: MaintenanceCueKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    priority: NextActionPriority
    severity: NextActionSeverity = NextActionSeverity.INFO
    target: NextActionTarget
    safe_next_actions: list[NextAction] = Field(default_factory=list, max_length=10)
    supporting_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    missing_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    stale_evidence: list[NextActionEvidenceRef] = Field(
        default_factory=list,
        max_length=20,
    )
    limitations: list[str] = Field(default_factory=list, max_length=20)
    destructive_remediation_available: bool = False
    destructive_remediation_note: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_cue_actions(self) -> MaintenanceCue:
        for action in self.safe_next_actions:
            if action.target.kind != self.target.kind:
                raise ValueError("maintenance cue action target kind must match cue")
            if (
                self.target.target_id is not None
                and action.target.target_id is not None
                and action.target.target_id != self.target.target_id
            ):
                raise ValueError("maintenance cue action target id must match cue")
        if (
            self.destructive_remediation_available
            and self.destructive_remediation_note is None
        ):
            raise ValueError("destructive remediation cues must include a note")
        return self


__all__ = [
    "MaintenanceCue",
    "NextAction",
    "NextActionCommandRecipe",
    "NextActionEvidenceRef",
    "NextActionTarget",
    "OperatorQueueDedupeKey",
    "OperatorQueueEvidenceSummary",
    "OperatorQueueItem",
]
