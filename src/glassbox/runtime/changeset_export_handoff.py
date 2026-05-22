"""Handoff metadata helpers for reviewer-safe changeset exports."""

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffSourceRef
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.handoff_export_profiles import HandoffExportProfile
from glassbox.runtime.handoff_export_profiles import build_handoff_export_profile
from glassbox.runtime.handoff_local_only_inventory import (
    build_changeset_local_only_inventory,
)

CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES = [
    "raw .glassbox database",
    "raw command output",
    "raw provider transcripts",
    "raw manual evidence text",
    "raw external logs",
    "raw diffs",
    "raw file contents",
    "raw screenshots",
    "browser traces",
    "accessibility transcripts",
]


def build_changeset_export_profile(
    *,
    source: HandoffSourceRef,
    intent: HandoffIntent,
    output_format: str,
) -> HandoffExportProfile:
    """Build profile metadata for a reviewer-safe changeset package."""

    return build_handoff_export_profile(
        source=source,
        package_kind=HandoffPackageKind.CHANGESET,
        intent=intent,
        output_format=output_format,
        included_sections=[
            "changeset",
            "evidence_graph",
            "verification",
            "handoff_readiness",
            "local_only_inventory",
        ],
    )


def build_changeset_export_local_only_inventory(
    detail: ChangesetDetailView,
    verification_plan: ChangesetVerificationPlanPreview,
    *,
    source: HandoffSourceRef,
    intent: HandoffIntent,
) -> HandoffLocalOnlyInventory:
    """Build local-only inventory metadata for a changeset export."""

    return build_changeset_local_only_inventory(
        detail,
        verification_plan,
        source=source,
        intent=intent,
        omitted_raw_categories=CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES,
    )


def changeset_export_redaction_report() -> list[str]:
    """Stable redaction report lines for reviewer-safe changeset packages."""

    return [
        "raw .glassbox database state is not included",
        "raw command output is not included",
        "raw provider transcripts are not included",
        "raw manual evidence text and raw external logs are not included",
        "raw diffs and file contents are not included",
        (
            "raw screenshots, browser traces, and accessibility transcripts "
            "are not included"
        ),
        "artifact paths remain local-only references by artifact ID",
    ]


def changeset_export_non_claims() -> list[str]:
    """Stable non-claims for reviewer-safe changeset packages."""

    return [
        "export package is a summary index, not proof every changed line was reviewed",
        "stale verification is not treated as fresh",
        "review feedback response state is not reviewer approval",
        "manual evidence is not retained Glassbox command evidence",
        "browser, dashboard, and accessibility evidence remains advisory",
        "local-only artifacts are not shareable without separate review",
        "commit, push, PR, and merge remain explicit operator actions",
        "export package does not publish the changeset",
    ]


def changeset_export_safe_inspection_commands(
    detail: ChangesetDetailView,
) -> list[str]:
    """Return read-only local inspection commands retained in the export."""

    return list(detail.safe_next_actions)


__all__ = [
    "CHANGESET_EXPORT_OMITTED_RAW_CATEGORIES",
    "build_changeset_export_local_only_inventory",
    "build_changeset_export_profile",
    "changeset_export_non_claims",
    "changeset_export_redaction_report",
    "changeset_export_safe_inspection_commands",
]
