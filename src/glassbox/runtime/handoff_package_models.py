"""Runtime-local handoff package inspection models."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffLocalOnlyInventory
from glassbox.core.models_handoff import HandoffLocalOnlySummary
from glassbox.core.models_handoff import HandoffPackageV2
from glassbox.core.models_handoff import HandoffRedactionSummary
from glassbox.core.types_handoff import HandoffCompatibilityState


class HandoffPackageInspection(BaseModel):
    """Inspection-first compatibility result for one portable handoff package."""

    model_config = ConfigDict(extra="forbid")

    compatibility: HandoffCompatibilitySummary
    package_format: str | None = Field(default=None, max_length=120)
    schema_version: int | str | None = None
    package_kind: str | None = Field(default=None, max_length=120)
    source_kind: str | None = Field(default=None, max_length=120)
    source_id: str | None = Field(default=None, max_length=300)
    intent: str | None = Field(default=None, max_length=120)
    included_sections: list[str] = Field(default_factory=list, max_length=100)
    unsupported_sections: list[str] = Field(default_factory=list, max_length=100)
    missing_optional_sections: list[str] = Field(default_factory=list, max_length=100)
    redaction: HandoffRedactionSummary = Field(
        default_factory=HandoffRedactionSummary,
    )
    local_only: HandoffLocalOnlySummary = Field(
        default_factory=HandoffLocalOnlySummary,
    )
    local_only_inventory: HandoffLocalOnlyInventory | None = None
    digest: HandoffDigestSummary = Field(default_factory=HandoffDigestSummary)
    non_claims: list[str] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=50)
    package: HandoffPackageV2 | None = None


def invalid_inspection(
    *,
    warning: str,
    package_format: str | None = None,
    schema_version: int | str | None = None,
    unsupported_values: list[str] | None = None,
) -> HandoffPackageInspection:
    """Build the shared invalid-package inspection result."""

    return HandoffPackageInspection(
        package_format=package_format,
        schema_version=schema_version,
        compatibility=HandoffCompatibilitySummary(
            state=HandoffCompatibilityState.INVALID,
            unsupported_values=unsupported_values or [],
            warnings=[warning],
        ),
        limitations=["Invalid handoff packages are inspection-only."],
    )


__all__ = [
    "HandoffPackageInspection",
    "invalid_inspection",
]
