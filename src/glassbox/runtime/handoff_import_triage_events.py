"""Imported handoff inspection event helpers."""

from pathlib import Path

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ImportedHandoffInspected
from glassbox.core.ids import SessionId
from glassbox.core.types_handoff import HandoffIntent
from glassbox.core.types_handoff import HandoffPackageKind
from glassbox.core.types_handoff import HandoffSourceKind
from glassbox.runtime.handoff_import_triage_disposition import local_only_count
from glassbox.runtime.handoff_package import HandoffPackageInspection
from glassbox.runtime.session_export import SESSION_EXPORT_KIND


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
            local_only_count=local_only_count(inspection),
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

    value = inspection.intent
    if value is None:
        return None
    try:
        return HandoffIntent(value)
    except ValueError:
        return None


__all__ = [
    "build_imported_handoff_inspected_event",
    "intent_for_inspection",
    "package_id_for_inspection",
    "package_kind_for_inspection",
    "source_kind_for_inspection",
]
