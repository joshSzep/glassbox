"""Portable v17 handoff package facade."""

from pathlib import Path

from glassbox.core.models_handoff import HandoffPackageManifest
from glassbox.core.models_handoff import HandoffPackageV2
from glassbox.runtime.handoff_package_digest import digest_summary
from glassbox.runtime.handoff_package_inspection import inspect_handoff_package
from glassbox.runtime.handoff_package_models import HandoffPackageInspection


def build_handoff_package_v2(
    manifest: HandoffPackageManifest,
    *,
    payload_sections: dict[str, object] | None = None,
) -> HandoffPackageV2:
    """Build a v2 handoff package and attach deterministic package digests."""

    payload = dict(payload_sections or {})
    digest = digest_summary(manifest=manifest, payload_sections=payload)
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


__all__ = [
    "HandoffPackageInspection",
    "build_handoff_package_v2",
    "inspect_handoff_package",
    "inspect_handoff_package_path",
]
