"""Accessibility evidence artifact helpers."""

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
