"""Inspection helpers for supported v17 handoff packages."""

import json
from typing import Any

from pydantic import ValidationError

from glassbox.core.models_handoff import HANDOFF_PACKAGE_FORMAT
from glassbox.core.models_handoff import HANDOFF_PACKAGE_SCHEMA_VERSION
from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffPackageV2
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.runtime.handoff_package_digest import verified_digest_summary
from glassbox.runtime.handoff_package_legacy import inspect_legacy_session_export
from glassbox.runtime.handoff_package_models import HandoffPackageInspection
from glassbox.runtime.handoff_package_models import invalid_inspection
from glassbox.runtime.session_import_validation import contains_unredacted_secret


def inspect_handoff_package(raw_package: str) -> HandoffPackageInspection:
    """Inspect package compatibility, redaction posture, and digest status."""

    if contains_unredacted_secret(raw_package):
        return invalid_inspection(
            warning="handoff package appears to contain unredacted secret material"
        )

    try:
        raw_payload = json.loads(raw_package)
    except json.JSONDecodeError as exc:
        return invalid_inspection(warning=f"invalid JSON handoff package: {exc}")
    if not isinstance(raw_payload, dict):
        return invalid_inspection(warning="handoff package must be a JSON object")

    legacy = inspect_legacy_session_export(raw_payload)
    if legacy is not None:
        return legacy

    package_format = raw_payload.get("package_format")
    schema_version = raw_payload.get("schema_version")
    manifest_payload = raw_payload.get("manifest")
    manifest = manifest_payload if isinstance(manifest_payload, dict) else {}

    if package_format != HANDOFF_PACKAGE_FORMAT:
        return invalid_inspection(
            package_format=_string_or_none(package_format),
            schema_version=(
                schema_version if isinstance(schema_version, int | str) else None
            ),
            warning="unsupported handoff package format",
            unsupported_values=[f"package_format={package_format!r}"],
        )
    if not isinstance(schema_version, int):
        return invalid_inspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=_string_or_none(schema_version),
            warning="handoff package schema_version must be an integer",
            unsupported_values=[f"schema_version={schema_version!r}"],
        )
    if schema_version > HANDOFF_PACKAGE_SCHEMA_VERSION:
        return HandoffPackageInspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=schema_version,
            package_kind=_manifest_string(manifest, "package_kind"),
            source_kind=_manifest_source_kind(manifest),
            source_id=_manifest_source_id(manifest),
            intent=_manifest_string(manifest, "intent"),
            compatibility=HandoffCompatibilitySummary(
                state=HandoffCompatibilityState.FUTURE_VERSION,
                unsupported_values=[f"schema_version={schema_version}"],
                warnings=[
                    "Inspect this package with a newer Glassbox before relying on it."
                ],
            ),
            included_sections=_string_list(manifest.get("included_sections")),
            unsupported_sections=_string_list(manifest.get("unsupported_sections")),
            non_claims=_string_list(manifest.get("non_claims")),
            limitations=[
                "Future package versions are inspection-only in this Glassbox build."
            ],
        )
    if schema_version < HANDOFF_PACKAGE_SCHEMA_VERSION:
        return invalid_inspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=schema_version,
            warning="unsupported older v17 handoff package schema version",
            unsupported_values=[f"schema_version={schema_version}"],
        )

    try:
        package = HandoffPackageV2.model_validate(raw_payload)
    except ValidationError as exc:
        return invalid_inspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=schema_version,
            warning=f"invalid v2 handoff package: {exc}",
        )

    return inspect_supported_package(package)


def inspect_supported_package(package: HandoffPackageV2) -> HandoffPackageInspection:
    """Inspect a schema-supported handoff package."""

    digest = verified_digest_summary(package)
    warnings = list(package.manifest.compatibility.warnings)
    state = package.manifest.compatibility.state
    if not digest.verified:
        state = HandoffCompatibilityState.INVALID
        warnings.append("handoff package digest validation failed")
    elif state == HandoffCompatibilityState.SUPPORTED and warnings:
        state = HandoffCompatibilityState.SUPPORTED_WITH_WARNINGS

    compatibility = package.manifest.compatibility.model_copy(
        update={"state": state, "warnings": warnings},
        deep=True,
    )
    return HandoffPackageInspection(
        package_format=package.package_format,
        schema_version=package.schema_version,
        package_kind=package.manifest.package_kind.value,
        source_kind=package.manifest.source.kind.value,
        source_id=package.manifest.source.primary_id,
        intent=package.manifest.intent.value,
        compatibility=compatibility,
        included_sections=[
            *package.manifest.included_sections,
            *[
                section
                for section in package.payload_sections
                if section not in package.manifest.included_sections
            ],
        ],
        unsupported_sections=[
            *package.manifest.unsupported_sections,
            *package.manifest.compatibility.unsupported_sections,
        ],
        missing_optional_sections=package.manifest.compatibility.missing_optional_sections,
        redaction=package.manifest.redaction,
        local_only=package.manifest.local_only,
        local_only_inventory=package.manifest.local_only_inventory,
        digest=digest,
        non_claims=package.manifest.non_claims,
        limitations=[
            *package.manifest.redaction.limitations,
            *package.manifest.local_only.limitations,
            *package.manifest.digest.limitations,
        ],
        package=package,
    )


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _manifest_string(manifest: dict[str, Any], key: str) -> str | None:
    value = manifest.get(key)
    return value if isinstance(value, str) else None


def _manifest_source_kind(manifest: dict[str, Any]) -> str | None:
    source = manifest.get("source")
    if not isinstance(source, dict):
        return None
    value = source.get("kind")
    return value if isinstance(value, str) else None


def _manifest_source_id(manifest: dict[str, Any]) -> str | None:
    source = manifest.get("source")
    if not isinstance(source, dict):
        return None
    value = source.get("primary_id")
    return value if isinstance(value, str) else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = [
    "inspect_handoff_package",
    "inspect_supported_package",
]
