"""Accessibility evidence artifact helpers."""

import pytest

from glassbox.runtime.accessibility_evidence import AccessibilityEvidenceCapture
from glassbox.runtime.accessibility_evidence import accessibility_evidence_limitations
from glassbox.runtime.accessibility_evidence import accessibility_evidence_non_claims
from glassbox.runtime.accessibility_evidence import accessibility_evidence_note


def test_accessibility_evidence_capture_renders_bounded_non_claims() -> None:
    capture = AccessibilityEvidenceCapture(
        observation_kind="focus_order_issue",
        summary="focus leaves the feedback dialog",
        source_label="keyboard-review",
        environment="local-dev",
        tool="manual keyboard",
        route_label="/console/changesets/abc",
        reviewer_label="reviewer-a",
        observed_issue="Tab moved focus behind the modal after the second step.",
        severity="high",
        disposition="paired_with_feedback",
        follow_up="Link to feedback before handoff.",
        paired_tool_output_label="playwright keyboard smoke",
        skipped_cases=["screen reader pairing"],
        limitations=["manual pass only"],
    )

    note = accessibility_evidence_note(capture)
    limitations = accessibility_evidence_limitations(capture)
    non_claims = accessibility_evidence_non_claims()

    assert "protocol: accessibility-evidence.v1" in note
    assert "observation_kind: focus_order_issue" in note
    assert "severity: high" in note
    assert "disposition: paired_with_feedback" in note
    assert "not WCAG certification" in note
    assert "severity: high" in limitations
    assert "follow-up: Link to feedback before handoff." in limitations
    assert "not accessibility certification" in non_claims
    assert "not deterministic release authority" in non_claims


def test_skipped_accessibility_evidence_does_not_require_fake_environment() -> None:
    capture = AccessibilityEvidenceCapture(
        capture_state="not_applicable",
        observation_kind="screen_reader_note",
        summary="screen reader pairing was not applicable for docs-only change",
        source_label="accessibility-review",
        skip_reason="docs-only change had no rendered interaction surface",
        skipped_cases=["screen reader pairing", "keyboard pass"],
    )

    note = accessibility_evidence_note(capture)
    limitations = accessibility_evidence_limitations(capture)
    non_claims = accessibility_evidence_non_claims()

    assert "capture_state: not_applicable" in note
    assert "environment: unknown" in note
    assert "observed_issue: not observed" in note
    assert "skip_reason: docs-only change" in note
    assert "skipped accessibility evidence is not a pass" in limitations
    assert "skipped accessibility evidence is not a pass" in non_claims


def test_skipped_accessibility_evidence_rejects_observed_issue_claims() -> None:
    with pytest.raises(ValueError, match="cannot include an observed issue"):
        AccessibilityEvidenceCapture(
            capture_state="not_run",
            observation_kind="keyboard_pass",
            summary="keyboard pass was skipped",
            source_label="keyboard-review",
            skip_reason="not run",
            observed_issue="Tab order was checked.",
        )


def test_observed_accessibility_evidence_requires_environment_and_issue() -> None:
    with pytest.raises(ValueError, match="observed accessibility evidence requires"):
        AccessibilityEvidenceCapture(
            observation_kind="keyboard_pass",
            summary="keyboard pass completed",
            source_label="keyboard-review",
        )
