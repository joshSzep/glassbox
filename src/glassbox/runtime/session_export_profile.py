"""Session export profile and local-only metadata assembly."""

from glassbox.core.models_handoff import HandoffSourceRef
from glassbox.core.types_handoff import HandoffIntent
from glassbox.core.types_handoff import HandoffPackageKind
from glassbox.core.types_handoff import HandoffSourceKind
from glassbox.runtime.handoff_export_profiles import build_handoff_export_profile
from glassbox.runtime.handoff_local_only_inventory import (
    build_session_local_only_inventory,
)
from glassbox.runtime.session_export_models import SessionExportPayload

SESSION_EXPORT_OMITTED_RAW_CATEGORIES = [
    "raw .glassbox database",
    "raw artifact contents",
    "raw command logs",
    "raw provider output",
    "raw tool transcripts",
]


def attach_session_export_profile(
    payload: SessionExportPayload,
    *,
    intent: HandoffIntent,
    output_format: str,
) -> SessionExportPayload:
    """Attach recipient-oriented export profile metadata."""

    return payload.model_copy(
        update={
            "profile": build_handoff_export_profile(
                source=HandoffSourceRef(
                    kind=HandoffSourceKind.SESSION,
                    primary_id=str(payload.metadata.session_id),
                    label="session",
                ),
                package_kind=HandoffPackageKind.SESSION,
                intent=intent,
                output_format=output_format,
                included_sections=_included_sections(payload),
            )
        },
        deep=True,
    )


def attach_session_local_only_inventory(
    payload: SessionExportPayload,
    *,
    intent: HandoffIntent,
) -> SessionExportPayload:
    """Attach local-only inventory metadata for the selected intent."""

    return payload.model_copy(
        update={
            "local_only_inventory": build_session_local_only_inventory(
                payload,
                intent=intent,
                omitted_raw_categories=SESSION_EXPORT_OMITTED_RAW_CATEGORIES,
            )
        },
        deep=True,
    )


def _included_sections(payload: SessionExportPayload) -> list[str]:
    return [
        key
        for key, value in payload.model_dump(mode="json", exclude_none=True).items()
        if value not in ([], {})
    ]


__all__ = [
    "SESSION_EXPORT_OMITTED_RAW_CATEGORIES",
    "attach_session_export_profile",
    "attach_session_local_only_inventory",
]
