"""Disposition and safe-command helpers for handoff import triage."""

from pathlib import Path

from glassbox.core.models_handoff import HandoffSafeCommand
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.core.types_handoff import HandoffSourceKind
from glassbox.runtime.handoff_import_triage_models import HandoffImportDisposition
from glassbox.runtime.handoff_package import HandoffPackageInspection
from glassbox.runtime.session_export import SESSION_EXPORT_KIND


def recommended_disposition(
    inspection: HandoffPackageInspection,
) -> HandoffImportDisposition:
    """Map package compatibility posture to the safe first disposition."""

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
    if local_only_count(inspection) >= 5:
        return "inspect-local-only-gaps"
    if inspection.compatibility.warnings or inspection.missing_optional_sections:
        return "inspect-with-warnings"
    return "inspect-only"


def safe_first_commands(
    inspection: HandoffPackageInspection,
    *,
    package_path: Path,
    can_import: bool,
) -> list[HandoffSafeCommand]:
    """Build read-only first commands for the triage result."""

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


def local_only_omissions(inspection: HandoffPackageInspection) -> list[str]:
    """Summarize local-only evidence categories for recipient triage."""

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


def limitations(inspection: HandoffPackageInspection) -> list[str]:
    """Collect visible limitations without hiding local-only gaps."""

    values = [
        *inspection.limitations,
        *inspection.compatibility.warnings,
        *inspection.redaction.limitations,
        *inspection.local_only.limitations,
        *inspection.digest.limitations,
    ]
    if local_only_count(inspection):
        values.append(
            "Package depends on local-only evidence the recipient cannot verify "
            "from this file alone."
        )
    return list(dict.fromkeys(values))


def local_only_count(inspection: HandoffPackageInspection) -> int:
    """Return total local-only evidence count from either summary shape."""

    if inspection.local_only.category_counts:
        return sum(inspection.local_only.category_counts.values())
    if inspection.local_only_inventory is not None:
        return inspection.local_only_inventory.total_count
    return 0


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


__all__ = [
    "limitations",
    "local_only_count",
    "local_only_omissions",
    "recommended_disposition",
    "safe_first_commands",
]
