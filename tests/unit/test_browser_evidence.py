"""Browser and dashboard evidence artifact helpers."""

from datetime import datetime

import pytest

from glassbox.runtime.browser_evidence import BrowserEvidenceCapture
from glassbox.runtime.browser_evidence import browser_evidence_limitations
from glassbox.runtime.browser_evidence import browser_evidence_local_reference
from glassbox.runtime.browser_evidence import browser_evidence_non_claims
from glassbox.runtime.browser_evidence import browser_evidence_note


def test_browser_evidence_capture_renders_advisory_metadata() -> None:
    capture = BrowserEvidenceCapture(
        capture_kind="dashboard_walkthrough",
        summary="dashboard rendered the manual evidence inbox",
        source_label="dashboard-local",
        route_label="/console/changesets/abc",
        environment="local-dev",
        browser="chromium",
        viewport_width=1440,
        viewport_height=900,
        observed_at=datetime(2026, 5, 1, 12, 30),
        input_method="keyboard",
        console_checked=True,
        screenshot_path_hint=".glassbox/evidence/abc/dashboard/inbox.png",
        screenshot_width=1440,
        screenshot_height=900,
        skipped_cases=["mobile viewport"],
        limitations=["live data fixture only"],
    )

    note = browser_evidence_note(capture)
    reference = browser_evidence_local_reference(capture)
    limitations = browser_evidence_limitations(capture)
    non_claims = browser_evidence_non_claims()

    assert "protocol: browser-accessibility-evidence.v1" in note
    assert "capture_kind: dashboard_walkthrough" in note
    assert "viewport: 1440x900" in note
    assert "non_claims: advisory live evidence" in note
    assert reference is not None
    assert reference.local_only is True
    assert reference.path_hint == ".glassbox/evidence/abc/dashboard/inbox.png"
    assert reference.width == 1440
    assert "browser/dashboard evidence is advisory live evidence" in limitations
    assert "screenshot metadata is local-only" in limitations
    assert "not deterministic release authority" in non_claims
    assert "not publication authority" in non_claims


def test_skipped_browser_evidence_does_not_require_fake_viewport() -> None:
    capture = BrowserEvidenceCapture(
        capture_state="not_run",
        capture_kind="dashboard_walkthrough",
        summary="dashboard walkthrough intentionally skipped",
        source_label="dashboard-local",
        skip_reason="local server was not started for this docs-only pass",
        skipped_cases=["viewport unknown", "console not checked"],
    )

    note = browser_evidence_note(capture)
    limitations = browser_evidence_limitations(capture)
    non_claims = browser_evidence_non_claims()

    assert "capture_state: not_run" in note
    assert "viewport: unknown" in note
    assert "environment: unknown" in note
    assert "skip_reason: local server was not started" in note
    assert "skipped browser/dashboard evidence is not a pass" in limitations
    assert "skipped browser/dashboard evidence is not a pass" in non_claims


def test_skipped_browser_evidence_rejects_live_observation_claims() -> None:
    with pytest.raises(ValueError, match="console was checked"):
        BrowserEvidenceCapture(
            capture_state="not_run",
            capture_kind="browser_check",
            summary="browser pass was skipped",
            source_label="local-browser",
            skip_reason="not applicable",
            console_checked=True,
        )


def test_observed_browser_evidence_requires_viewport_and_environment() -> None:
    with pytest.raises(ValueError, match="observed browser evidence requires"):
        BrowserEvidenceCapture(
            capture_kind="browser_check",
            summary="browser rendered",
            source_label="local-browser",
            route_label="/app/changesets",
            environment="local-dev",
        )
