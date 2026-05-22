"""Legacy package compatibility inspection for v17 handoff imports."""

from typing import Any

from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.runtime.handoff_package_digest import sha256_json
from glassbox.runtime.handoff_package_models import HandoffPackageInspection
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export import SESSION_EXPORT_VERSION


def inspect_legacy_session_export(
    raw_payload: dict[str, Any],
) -> HandoffPackageInspection | None:
    """Inspect a legacy session export without importing it."""

    if raw_payload.get("export_kind") != SESSION_EXPORT_KIND:
        return None
    export_version = raw_payload.get("export_version")
    if export_version == SESSION_EXPORT_VERSION:
        state = HandoffCompatibilityState.LEGACY_INSPECTION_ONLY
        warnings = [
            "Legacy session export v1 is importable for inspection, not v17 custody."
        ]
    else:
        state = HandoffCompatibilityState.UNSUPPORTED
        warnings = [f"unsupported legacy session export version: {export_version}"]

    return HandoffPackageInspection(
        package_format=SESSION_EXPORT_KIND,
        schema_version=export_version if isinstance(export_version, int) else None,
        package_kind="legacy-session-export",
        source_kind="session",
        source_id=_legacy_session_id(raw_payload),
        intent="review-only",
        included_sections=[
            key
            for key in ("metadata", "handoff", "transcript", "events")
            if key in raw_payload
        ],
        compatibility=HandoffCompatibilitySummary(
            state=state,
            supported_sections=[
                key
                for key in ("metadata", "handoff", "transcript", "events")
                if key in raw_payload
            ],
            unsupported_values=(
                []
                if state != HandoffCompatibilityState.UNSUPPORTED
                else [f"export_version={export_version}"]
            ),
            warnings=warnings,
        ),
        non_claims=[
            "legacy session export does not carry v17 custody decisions",
            "legacy session export does not prove source workspace completeness",
        ],
        digest=HandoffDigestSummary(
            package_digest=sha256_json(raw_payload),
            limitations=[
                "Legacy packages do not include v17 digest, compatibility, or "
                "local-only evidence summaries."
            ],
        ),
        limitations=[
            "Legacy packages do not include v17 digest, compatibility, or "
            "local-only evidence summaries."
        ],
    )


def _legacy_session_id(raw_payload: dict[str, Any]) -> str | None:
    metadata = raw_payload.get("metadata")
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("session_id")
    return value if isinstance(value, str) else None


__all__ = ["inspect_legacy_session_export"]
