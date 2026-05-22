"""Runtime-local models for inspection-first handoff import triage."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffRedactionSummary
from glassbox.core.models_handoff import HandoffSafeCommand
from glassbox.core.types_handoff import HandoffIntent

type HandoffImportDisposition = Literal[
    "import-for-inspection",
    "inspect-only",
    "inspect-with-warnings",
    "inspect-local-only-gaps",
    "reject",
    "use-newer-glassbox",
]


class HandoffImportSourceSummary(BaseModel):
    """Recipient-safe source description for an import candidate."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str | None = Field(default=None, max_length=120)
    source_id: str | None = Field(default=None, max_length=300)
    package_kind: str | None = Field(default=None, max_length=120)
    package_format: str | None = Field(default=None, max_length=120)
    schema_version: int | str | None = None


class HandoffImportTriage(BaseModel):
    """Read-only import triage result shown before local mutation."""

    model_config = ConfigDict(extra="forbid")

    package_id: str = Field(min_length=1, max_length=300)
    package_path: str = Field(min_length=1, max_length=1000)
    source: HandoffImportSourceSummary
    recipient_intent: HandoffIntent | None = None
    compatibility: HandoffCompatibilitySummary
    included_evidence: list[str] = Field(default_factory=list, max_length=100)
    local_only_omissions: list[str] = Field(default_factory=list, max_length=100)
    redaction: HandoffRedactionSummary = Field(
        default_factory=HandoffRedactionSummary,
    )
    digest: HandoffDigestSummary = Field(default_factory=HandoffDigestSummary)
    unsupported_sections: list[str] = Field(default_factory=list, max_length=100)
    missing_sections: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    safe_first_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )
    recommended_disposition: HandoffImportDisposition
    can_import_for_inspection: bool = False
    mutation_performed: bool = False


__all__ = [
    "HandoffImportDisposition",
    "HandoffImportSourceSummary",
    "HandoffImportTriage",
]
