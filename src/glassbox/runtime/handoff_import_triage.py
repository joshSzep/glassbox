"""Inspection-first triage facade for received handoff packages."""

from pathlib import Path

from glassbox.core.types_handoff import HandoffIntent
from glassbox.runtime.handoff_import_triage_disposition import limitations
from glassbox.runtime.handoff_import_triage_disposition import local_only_omissions
from glassbox.runtime.handoff_import_triage_disposition import recommended_disposition
from glassbox.runtime.handoff_import_triage_disposition import safe_first_commands
from glassbox.runtime.handoff_import_triage_events import (
    build_imported_handoff_inspected_event,
)
from glassbox.runtime.handoff_import_triage_events import intent_for_inspection
from glassbox.runtime.handoff_import_triage_events import package_id_for_inspection
from glassbox.runtime.handoff_import_triage_events import package_kind_for_inspection
from glassbox.runtime.handoff_import_triage_events import source_kind_for_inspection
from glassbox.runtime.handoff_import_triage_models import HandoffImportDisposition
from glassbox.runtime.handoff_import_triage_models import HandoffImportSourceSummary
from glassbox.runtime.handoff_import_triage_models import HandoffImportTriage
from glassbox.runtime.handoff_package import inspect_handoff_package_path


def triage_handoff_import(package_path: Path) -> HandoffImportTriage:
    """Inspect a handoff package and recommend a safe first disposition."""

    resolved_path = package_path.resolve()
    inspection = inspect_handoff_package_path(resolved_path)
    disposition = recommended_disposition(inspection)
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
        local_only_omissions=local_only_omissions(inspection),
        redaction=inspection.redaction,
        digest=inspection.digest,
        unsupported_sections=inspection.unsupported_sections,
        missing_sections=inspection.missing_optional_sections,
        limitations=limitations(inspection),
        safe_first_commands=safe_first_commands(
            inspection,
            package_path=resolved_path,
            can_import=can_import,
        ),
        recommended_disposition=disposition,
        can_import_for_inspection=can_import,
    )


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
