"""Portable v17 handoff package schema and compatibility inspection."""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from glassbox.core.models_handoff import HANDOFF_PACKAGE_FORMAT
from glassbox.core.models_handoff import HANDOFF_PACKAGE_SCHEMA_VERSION
from glassbox.core.models_handoff import HandoffCompatibilitySummary
from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffLocalOnlySummary
from glassbox.core.models_handoff import HandoffPackageManifest
from glassbox.core.models_handoff import HandoffPackageV2
from glassbox.core.models_handoff import HandoffRedactionSummary
from glassbox.core.types_handoff import HandoffCompatibilityState
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export import SESSION_EXPORT_VERSION
from glassbox.runtime.session_import_validation import contains_unredacted_secret


class HandoffPackageInspection(BaseModel):
    """Inspection-first compatibility result for one portable handoff package."""

    model_config = ConfigDict(extra="forbid")

    compatibility: HandoffCompatibilitySummary
    package_format: str | None = Field(default=None, max_length=120)
    schema_version: int | str | None = None
    package_kind: str | None = Field(default=None, max_length=120)
    source_kind: str | None = Field(default=None, max_length=120)
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
    digest: HandoffDigestSummary = Field(default_factory=HandoffDigestSummary)
    non_claims: list[str] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=50)
    package: HandoffPackageV2 | None = None


def build_handoff_package_v2(
    manifest: HandoffPackageManifest,
    *,
    payload_sections: dict[str, object] | None = None,
) -> HandoffPackageV2:
    """Build a v2 handoff package and attach deterministic package digests."""

    payload = dict(payload_sections or {})
    digest = _digest_summary(manifest=manifest, payload_sections=payload)
    manifest_with_digest = manifest.model_copy(update={"digest": digest}, deep=True)
    return HandoffPackageV2(
        manifest=manifest_with_digest,
        payload_sections=payload,
    )


def inspect_handoff_package_path(package_path: Path) -> HandoffPackageInspection:
    """Inspect a package file without importing or mutating local state."""

    try:
        raw_package = package_path.resolve().read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing handoff package: {package_path.resolve()}") from exc
    return inspect_handoff_package(raw_package)


def inspect_handoff_package(raw_package: str) -> HandoffPackageInspection:
    """Inspect package compatibility, redaction posture, and digest status."""

    if contains_unredacted_secret(raw_package):
        return _invalid_inspection(
            warning="handoff package appears to contain unredacted secret material"
        )

    try:
        raw_payload = json.loads(raw_package)
    except json.JSONDecodeError as exc:
        return _invalid_inspection(warning=f"invalid JSON handoff package: {exc}")
    if not isinstance(raw_payload, dict):
        return _invalid_inspection(warning="handoff package must be a JSON object")

    legacy = _inspect_legacy_session_export(raw_payload)
    if legacy is not None:
        return legacy

    package_format = raw_payload.get("package_format")
    schema_version = raw_payload.get("schema_version")
    manifest_payload = raw_payload.get("manifest")
    manifest = manifest_payload if isinstance(manifest_payload, dict) else {}

    if package_format != HANDOFF_PACKAGE_FORMAT:
        return _invalid_inspection(
            package_format=_string_or_none(package_format),
            schema_version=(
                schema_version if isinstance(schema_version, int | str) else None
            ),
            warning="unsupported handoff package format",
            unsupported_values=[f"package_format={package_format!r}"],
        )
    if not isinstance(schema_version, int):
        return _invalid_inspection(
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
        return _invalid_inspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=schema_version,
            warning="unsupported older v17 handoff package schema version",
            unsupported_values=[f"schema_version={schema_version}"],
        )

    try:
        package = HandoffPackageV2.model_validate(raw_payload)
    except ValidationError as exc:
        return _invalid_inspection(
            package_format=HANDOFF_PACKAGE_FORMAT,
            schema_version=schema_version,
            warning=f"invalid v2 handoff package: {exc}",
        )

    return _inspect_supported_package(package)


def _inspect_supported_package(package: HandoffPackageV2) -> HandoffPackageInspection:
    digest = _verified_digest_summary(package)
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
        digest=digest,
        non_claims=package.manifest.non_claims,
        limitations=[
            *package.manifest.redaction.limitations,
            *package.manifest.local_only.limitations,
            *package.manifest.digest.limitations,
        ],
        package=package,
    )


def _inspect_legacy_session_export(
    raw_payload: dict[str, Any],
) -> HandoffPackageInspection | None:
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
        limitations=[
            "Legacy packages do not include v17 digest, compatibility, or "
            "local-only evidence summaries."
        ],
    )


def _invalid_inspection(
    *,
    warning: str,
    package_format: str | None = None,
    schema_version: int | str | None = None,
    unsupported_values: list[str] | None = None,
) -> HandoffPackageInspection:
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


def _verified_digest_summary(package: HandoffPackageV2) -> HandoffDigestSummary:
    expected = _digest_summary(
        manifest=package.manifest,
        payload_sections=package.payload_sections,
    )
    actual = package.manifest.digest
    verified = (
        actual.manifest_digest == expected.manifest_digest
        and actual.payload_digest == expected.payload_digest
        and actual.package_digest == expected.package_digest
    )
    return actual.model_copy(
        update={
            "verified": verified,
            "limitations": list(
                dict.fromkeys(
                    [
                        *actual.limitations,
                        (
                            "Digests validate package integrity, "
                            "not source workspace truth."
                        ),
                    ]
                )
            ),
        },
        deep=True,
    )


def _digest_summary(
    *,
    manifest: HandoffPackageManifest,
    payload_sections: dict[str, object],
) -> HandoffDigestSummary:
    manifest_for_digest = manifest.model_dump(mode="json", exclude={"digest"})
    payload_for_digest = _jsonable(payload_sections)
    manifest_digest = _sha256_json(manifest_for_digest)
    payload_digest = _sha256_json(payload_for_digest)
    package_digest = _sha256_json(
        {
            "manifest": manifest_for_digest,
            "payload_sections": payload_for_digest,
        }
    )
    return HandoffDigestSummary(
        manifest_digest=manifest_digest,
        payload_digest=payload_digest,
        package_digest=package_digest,
        verified=True,
        limitations=["Digests validate package integrity, not source workspace truth."],
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _jsonable(value: object) -> object:
    return json.loads(_canonical_json(value))


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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = [
    "HandoffPackageInspection",
    "build_handoff_package_v2",
    "inspect_handoff_package",
    "inspect_handoff_package_path",
]
