"""Inspection-first triage for received handoff packages."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ImportedHandoffInspected
from glassbox.core.ids import SessionId
from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffRedactionSummary
from glassbox.core.models_handoff import HandoffSafeCommand
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.core.types_handoff import HandoffIntent
from glassbox.core.types_handoff import HandoffPackageKind
from glassbox.core.types_handoff import HandoffSourceKind
from glassbox.runtime.handoff_package import HandoffPackageInspection
from glassbox.runtime.handoff_package import inspect_handoff_package_path
from glassbox.runtime.session_export import SESSION_EXPORT_KIND

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


def triage_handoff_import(package_path: Path) -> HandoffImportTriage:
    """Inspect a handoff package and recommend a safe first disposition."""

    resolved_path = package_path.resolve()
    inspection = inspect_handoff_package_path(resolved_path)
    disposition = _recommended_disposition(inspection)
    can_import = disposition == "import-for-inspection"
    return HandoffImportTriage(
        package_id=package_id_for_inspection(inspection),
        package_path=str(resolved_path),
        source=HandoffImportSourceSummary(
            source_kind=inspection.source_kind,
            source_id=inspection.source_id,
            package_kind=inspection.package_kind,
            package_format=inspection.package_format,
            schema_version=inspection.schema_version,
        ),
        recipient_intent=_optional_intent(inspection.intent),
        compatibility=inspection.compatibility,
        included_evidence=inspection.included_sections,
        local_only_omissions=_local_only_omissions(inspection),
        redaction=inspection.redaction,
        digest=inspection.digest,
        unsupported_sections=inspection.unsupported_sections,
        missing_sections=inspection.missing_optional_sections,
        limitations=_limitations(inspection),
        safe_first_commands=_safe_first_commands(
            inspection,
            package_path=resolved_path,
            can_import=can_import,
        ),
        recommended_disposition=disposition,
        can_import_for_inspection=can_import,
    )


def build_imported_handoff_inspected_event(
    inspection: HandoffPackageInspection,
    *,
    imported_session_id: SessionId,
    package_path: Path,
) -> EventEnvelope:
    """Build the durable imported-package inspection event for session import."""

    return EventEnvelope(
        session_id=imported_session_id,
        sequence=0,
        payload=ImportedHandoffInspected(
            package_id=package_id_for_inspection(inspection),
            source_kind=source_kind_for_inspection(inspection),
            source_id=inspection.source_id,
            package_kind=package_kind_for_inspection(inspection),
            intent=intent_for_inspection(inspection),
            package_digest=inspection.digest.package_digest,
            compatibility_state=inspection.compatibility.state,
            redaction_posture=inspection.redaction.posture,
            local_only_count=_local_only_count(inspection),
            safe_next_actions=[
                f"glassbox session import {package_path.resolve()} --triage"
            ],
            note="Imported package inspected before local historical import.",
        ),
    )


def package_id_for_inspection(inspection: HandoffPackageInspection) -> str:
    """Derive a stable local package id for imported-package records."""

    digest = inspection.digest.package_digest
    if digest:
        return f"pkg-{digest[:24]}"
    if inspection.package_format:
        source = inspection.source_id or "unknown"
        return f"pkg-{inspection.package_format}-{source}"[:300]
    return "pkg-unidentified"


def source_kind_for_inspection(
    inspection: HandoffPackageInspection,
) -> HandoffSourceKind:
    """Map inspected package source kind to event vocabulary."""

    if inspection.source_kind is None:
        return HandoffSourceKind.IMPORTED_PACKAGE
    try:
        return HandoffSourceKind(inspection.source_kind)
    except ValueError:
        return HandoffSourceKind.IMPORTED_PACKAGE


def package_kind_for_inspection(
    inspection: HandoffPackageInspection,
) -> HandoffPackageKind | None:
    """Map inspected package kind to event vocabulary when possible."""

    if inspection.package_format == SESSION_EXPORT_KIND:
        return HandoffPackageKind.SESSION
    if inspection.package_kind is None:
        return None
    try:
        return HandoffPackageKind(inspection.package_kind)
    except ValueError:
        return None


def intent_for_inspection(inspection: HandoffPackageInspection) -> HandoffIntent | None:
    """Map inspected package intent to event vocabulary when possible."""

    return _optional_intent(inspection.intent)


def _recommended_disposition(
    inspection: HandoffPackageInspection,
) -> HandoffImportDisposition:
    state = inspection.compatibility.state
    if state == HandoffCompatibilityState.FUTURE_VERSION:
        return "use-newer-glassbox"
    if state in {
        HandoffCompatibilityState.INVALID,
        HandoffCompatibilityState.UNSUPPORTED,
    }:
        return "reject"
    if (
        state == HandoffCompatibilityState.LEGACY_INSPECTION_ONLY
        and inspection.package_format == SESSION_EXPORT_KIND
    ):
        return "import-for-inspection"
    if _local_only_count(inspection) >= 5:
        return "inspect-local-only-gaps"
    if inspection.compatibility.warnings or inspection.missing_optional_sections:
        return "inspect-with-warnings"
    return "inspect-only"


def _safe_first_commands(
    inspection: HandoffPackageInspection,
    *,
    package_path: Path,
    can_import: bool,
) -> list[HandoffSafeCommand]:
    commands = [
        HandoffSafeCommand(
            command=[
                "glassbox",
                "session",
                "import",
                str(package_path),
                "--triage",
            ],
            display=f"glassbox session import {package_path} --triage",
            purpose="Inspect package compatibility, redaction, and local-only gaps.",
        )
    ]
    commands.extend(_inspection_commands_from_package(inspection))
    if can_import:
        commands.append(
            HandoffSafeCommand(
                command=["glassbox", "session", "import", str(package_path), "--help"],
                display=f"glassbox session import {package_path} --help",
                purpose=(
                    "Review the import command before creating historical "
                    "inspection-only local state."
                ),
            )
        )
    return commands


def _inspection_commands_from_package(
    inspection: HandoffPackageInspection,
) -> list[HandoffSafeCommand]:
    commands: list[HandoffSafeCommand] = []
    source_id = inspection.source_id
    if inspection.source_kind == HandoffSourceKind.SESSION.value and source_id:
        commands.append(
            HandoffSafeCommand(
                command=["glassbox", "session", "status", source_id],
                display=f"glassbox session status {source_id}",
                purpose="Inspect the source session identifier if it exists locally.",
            )
        )
    return commands


def _local_only_omissions(inspection: HandoffPackageInspection) -> list[str]:
    if inspection.local_only.category_counts:
        return [
            f"{category}: {count}"
            for category, count in sorted(inspection.local_only.category_counts.items())
        ]
    if inspection.local_only_inventory is not None:
        return [
            f"{category}: {count}"
            for category, count in sorted(
                inspection.local_only_inventory.category_counts.items()
            )
        ]
    return []


def _limitations(inspection: HandoffPackageInspection) -> list[str]:
    values = [
        *inspection.limitations,
        *inspection.compatibility.warnings,
        *inspection.redaction.limitations,
        *inspection.local_only.limitations,
        *inspection.digest.limitations,
    ]
    if _local_only_count(inspection):
        values.append(
            "Package depends on local-only evidence the recipient cannot verify "
            "from this file alone."
        )
    return list(dict.fromkeys(values))


def _local_only_count(inspection: HandoffPackageInspection) -> int:
    if inspection.local_only.category_counts:
        return sum(inspection.local_only.category_counts.values())
    if inspection.local_only_inventory is not None:
        return inspection.local_only_inventory.total_count
    return 0


def _optional_intent(value: str | None) -> HandoffIntent | None:
    if value is None:
        return None
    try:
        return HandoffIntent(value)
    except ValueError:
        return None


__all__ = [
    "HandoffImportDisposition",
    "HandoffImportSourceSummary",
    "HandoffImportTriage",
    "build_imported_handoff_inspected_event",
    "intent_for_inspection",
    "package_id_for_inspection",
    "package_kind_for_inspection",
    "source_kind_for_inspection",
    "triage_handoff_import",
]
