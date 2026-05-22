"""Digest helpers for v17 handoff packages."""

import hashlib
import json

from glassbox.core.models_handoff import HandoffDigestSummary
from glassbox.core.models_handoff import HandoffPackageManifest
from glassbox.core.models_handoff import HandoffPackageV2


def digest_summary(
    *,
    manifest: HandoffPackageManifest,
    payload_sections: dict[str, object],
) -> HandoffDigestSummary:
    """Build deterministic package digests for a v2 handoff package."""

    manifest_for_digest = manifest.model_dump(mode="json", exclude={"digest"})
    payload_for_digest = jsonable(payload_sections)
    manifest_digest = sha256_json(manifest_for_digest)
    payload_digest = sha256_json(payload_for_digest)
    package_digest = sha256_json(
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


def verified_digest_summary(package: HandoffPackageV2) -> HandoffDigestSummary:
    """Verify a package's stored digest against its canonical contents."""

    expected = digest_summary(
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


def sha256_json(value: object) -> str:
    """Hash JSON using the handoff package canonicalization rules."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def canonical_json(value: object) -> str:
    """Serialize JSON deterministically for digest construction."""

    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def jsonable(value: object) -> object:
    """Normalize arbitrary JSON-like values through canonical JSON."""

    return json.loads(canonical_json(value))


__all__ = [
    "canonical_json",
    "digest_summary",
    "jsonable",
    "sha256_json",
    "verified_digest_summary",
]
