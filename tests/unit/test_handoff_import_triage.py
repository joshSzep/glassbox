"""Unit tests for inspection-first handoff import triage."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCompatibilitySummary
from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffPackageManifest
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.runtime.handoff_import_triage import triage_handoff_import
from glassbox.runtime.handoff_package import build_handoff_package_v2


def test_import_triage_accepts_supported_v2_for_inspection(
    tmp_path: Path,
) -> None:
    package_path = _write_v2_package(tmp_path)

    triage = triage_handoff_import(package_path)

    assert triage.compatibility.state == HandoffCompatibilityState.SUPPORTED
    assert triage.recommended_disposition == "inspect-only"
    assert triage.can_import_for_inspection is False
    assert triage.recipient_intent == HandoffIntent.REVIEW_ONLY
    assert triage.source.source_kind == "session"
    assert triage.digest.verified is True


def test_import_triage_marks_legacy_session_exports_importable(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "legacy.json"
    package_path.write_text(
        json.dumps(
            {
                "export_kind": "glassbox_session_export",
                "export_version": 1,
                "metadata": {"session_id": "session-123"},
                "handoff": {"summary": "Inspect this."},
                "transcript": [],
            }
        ),
        encoding="utf-8",
    )

    triage = triage_handoff_import(package_path)

    assert (
        triage.compatibility.state == HandoffCompatibilityState.LEGACY_INSPECTION_ONLY
    )
    assert triage.recommended_disposition == "import-for-inspection"
    assert triage.can_import_for_inspection is True
    assert triage.source.source_id == "session-123"
    assert triage.digest.package_digest is not None


def test_import_triage_rejects_unsupported_legacy_package(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "legacy.json"
    package_path.write_text(
        json.dumps(
            {
                "export_kind": "glassbox_session_export",
                "export_version": 999,
                "metadata": {"session_id": "session-123"},
            }
        ),
        encoding="utf-8",
    )

    triage = triage_handoff_import(package_path)

    assert triage.compatibility.state == HandoffCompatibilityState.UNSUPPORTED
    assert triage.recommended_disposition == "reject"
    assert triage.can_import_for_inspection is False


def test_import_triage_rejects_tampered_v2_package(tmp_path: Path) -> None:
    package_path = _write_v2_package(tmp_path)
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    payload["payload_sections"]["handoff.summary"]["objective"] = "Changed."
    package_path.write_text(json.dumps(payload), encoding="utf-8")

    triage = triage_handoff_import(package_path)

    assert triage.compatibility.state == HandoffCompatibilityState.INVALID
    assert triage.recommended_disposition == "reject"
    assert triage.digest.verified is False


def test_import_triage_keeps_future_schema_inspection_only(tmp_path: Path) -> None:
    package_path = _write_v2_package(tmp_path)
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 99
    package_path.write_text(json.dumps(payload), encoding="utf-8")

    triage = triage_handoff_import(package_path)

    assert triage.compatibility.state == HandoffCompatibilityState.FUTURE_VERSION
    assert triage.recommended_disposition == "use-newer-glassbox"
    assert triage.can_import_for_inspection is False
    assert triage.mutation_performed is False
    assert [command.display for command in triage.safe_first_commands] == [
        f"glassbox session import {package_path.resolve()} --triage",
        "glassbox session status session-123",
    ]


def test_import_triage_surfaces_missing_optional_sections(
    tmp_path: Path,
) -> None:
    package_path = _write_v2_package(
        tmp_path,
        compatibility=HandoffCompatibilitySummary(
            state=HandoffCompatibilityState.SUPPORTED,
            missing_optional_sections=["markdown_summary"],
        ),
    )

    triage = triage_handoff_import(package_path)

    assert triage.recommended_disposition == "inspect-with-warnings"
    assert triage.missing_sections == ["markdown_summary"]


def test_import_triage_surfaces_local_only_heavy_packages(
    tmp_path: Path,
) -> None:
    package_path = _write_v2_package(
        tmp_path,
        local_only=HandoffLocalOnlySummary(
            category_counts={"raw-command-log": 3, "screenshot": 2},
            limitations=["Raw logs and screenshots stayed local."],
        ),
    )

    triage = triage_handoff_import(package_path)

    assert triage.recommended_disposition == "inspect-local-only-gaps"
    assert triage.local_only_omissions == ["raw-command-log: 3", "screenshot: 2"]
    assert any("local-only evidence" in item for item in triage.limitations)


def _write_v2_package(
    tmp_path: Path,
    *,
    compatibility: HandoffCompatibilitySummary | None = None,
    local_only: HandoffLocalOnlySummary | None = None,
) -> Path:
    manifest = HandoffPackageManifest(
        package_kind=HandoffPackageKind.SESSION,
        source=HandoffSourceRef(
            kind=HandoffSourceKind.SESSION,
            primary_id="session-123",
        ),
        generated_at=datetime(2026, 5, 18, tzinfo=UTC),
        intent=HandoffIntent.REVIEW_ONLY,
        included_sections=["handoff.summary"],
        compatibility=compatibility or HandoffCompatibilitySummary(),
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.REVIEWER_SAFE,
        ),
        local_only=local_only or HandoffLocalOnlySummary(),
    )
    package = build_handoff_package_v2(
        manifest,
        payload_sections={"handoff.summary": {"objective": "Review this safely."}},
    )
    package_path = tmp_path / "handoff.json"
    package_path.write_text(package.model_dump_json(), encoding="utf-8")
    return package_path
