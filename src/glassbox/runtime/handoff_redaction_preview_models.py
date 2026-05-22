"""Runtime-local redaction preview models."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceRef
from glassbox.runtime.handoff_export_profiles import HandoffExportProfile


class HandoffRedactionPreview(BaseModel):
    """Machine-readable preview for what a handoff export would include."""

    model_config = ConfigDict(extra="forbid")

    preview_kind: str = "handoff_redaction_preview"
    source: HandoffSourceRef
    intent: HandoffIntent
    profile: HandoffExportProfile | None = None
    included_sections: list[str] = Field(default_factory=list, max_length=100)
    redaction: HandoffRedactionSummary
    local_only: HandoffLocalOnlySummary
    local_only_inventory: HandoffLocalOnlyInventory
    omitted_raw_categories: list[str] = Field(default_factory=list, max_length=50)
    unsupported_evidence: list[str] = Field(default_factory=list, max_length=50)
    package_limitations: list[str] = Field(default_factory=list, max_length=50)
    safe_inspection_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )

    @computed_field
    @property
    def local_only_evidence_count(self) -> int:
        return sum(self.local_only.category_counts.values())


__all__ = ["HandoffRedactionPreview"]
