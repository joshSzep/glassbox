"""Unit tests for v17 handoff package schema inspection."""

import json
from datetime import UTC
from datetime import datetime

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffPackageManifest
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.runtime.handoff_package import build_handoff_package_v2
from glassbox.runtime.handoff_package import inspect_handoff_package


def _manifest() -> HandoffPackageManifest:
    return HandoffPackageManifest(
        package_kind=HandoffPackageKind.SESSION,
        source=HandoffSourceRef(
            kind=HandoffSourceKind.SESSION,
            primary_id="session-123",
        ),
        generated_at=datetime(2026, 5, 14, tzinfo=UTC),
        intent=HandoffIntent.REVIEW_ONLY,
        included_sections=["handoff.summary"],
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.REVIEWER_SAFE,
            redacted_field_count=1,
            redacted_categories=["local-path"],
        ),
    )


def test_handoff_package_v2_inspection_validates_digests() -> None:
    package = build_handoff_package_v2(
        _manifest(),
        payload_sections={"handoff.summary": {"objective": "Review this safely."}},
    )
    raw_package = package.model_dump_json()

    inspection = inspect_handoff_package(raw_package)

    assert inspection.compatibility.state == HandoffCompatibilityState.SUPPORTED
    assert inspection.package is not None
    assert inspection.schema_version == 2
    assert inspection.package_kind == "session-handoff"
    assert inspection.source_kind == "session"
    assert inspection.intent == "review-only"
    assert inspection.digest.verified is True
    assert "handoff.summary" in inspection.included_sections
    assert inspection.redaction.raw_logs_included is False


def test_handoff_package_v2_inspection_flags_tampered_payload() -> None:
    package = build_handoff_package_v2(
        _manifest(),
        payload_sections={"handoff.summary": {"objective": "Review this safely."}},
    )
    payload = json.loads(package.model_dump_json())
    payload["payload_sections"]["handoff.summary"]["objective"] = "Changed later."

    inspection = inspect_handoff_package(json.dumps(payload))

    assert inspection.compatibility.state == HandoffCompatibilityState.INVALID
    assert inspection.digest.verified is False
    assert "digest validation failed" in inspection.compatibility.warnings[0]


def test_handoff_package_v2_inspection_warns_for_future_schema() -> None:
    package = build_handoff_package_v2(_manifest())
    payload = json.loads(package.model_dump_json())
    payload["schema_version"] = 99
    payload["manifest"]["unsupported_sections"] = ["future.audit_trail"]
    payload["manifest"]["non_claims"] = ["future package is not approval"]

    inspection = inspect_handoff_package(json.dumps(payload))

    assert inspection.compatibility.state == HandoffCompatibilityState.FUTURE_VERSION
    assert inspection.schema_version == 99
    assert inspection.package_kind == "session-handoff"
    assert inspection.package is None
    assert inspection.unsupported_sections == ["future.audit_trail"]
    assert inspection.non_claims == ["future package is not approval"]
    assert inspection.limitations == [
        "Future package versions are inspection-only in this Glassbox build."
    ]


def test_handoff_package_v2_inspection_rejects_unknown_format() -> None:
    raw_package = json.dumps(
        {
            "package_format": "some_other_format",
            "schema_version": 2,
            "manifest": {},
            "payload_sections": {},
        }
    )

    inspection = inspect_handoff_package(raw_package)

    assert inspection.compatibility.state == HandoffCompatibilityState.INVALID
    assert "unsupported handoff package format" in inspection.compatibility.warnings[0]


def test_legacy_session_export_is_inspection_only() -> None:
    raw_package = json.dumps(
        {
            "export_kind": "glassbox_session_export",
            "export_version": 1,
            "metadata": {"session_id": "session-123"},
            "handoff": {"next_action_summary": "Inspect only."},
        }
    )

    inspection = inspect_handoff_package(raw_package)

    assert (
        inspection.compatibility.state
        == HandoffCompatibilityState.LEGACY_INSPECTION_ONLY
    )
    assert inspection.package_format == "glassbox_session_export"
    assert inspection.package_kind == "legacy-session-export"
    assert "v17 custody" in inspection.compatibility.warnings[0]


def test_unsupported_legacy_session_export_version_is_reported() -> None:
    raw_package = json.dumps(
        {
            "export_kind": "glassbox_session_export",
            "export_version": 999,
            "metadata": {"session_id": "session-123"},
        }
    )

    inspection = inspect_handoff_package(raw_package)

    assert inspection.compatibility.state == HandoffCompatibilityState.UNSUPPORTED
    assert "export_version=999" in inspection.compatibility.unsupported_values


def test_secret_like_package_is_invalid_before_schema_validation() -> None:
    inspection = inspect_handoff_package(
        '{"package_format":"glassbox_handoff_package",'
        '"schema_version":2,'
        '"manifest":{"note":"OPENAI_API_KEY=sk-secret-value-123456"}}'
    )

    assert inspection.compatibility.state == HandoffCompatibilityState.INVALID
    assert "unredacted secret material" in inspection.compatibility.warnings[0]
