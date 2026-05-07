"""Accessibility review evidence capture helpers."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

ACCESSIBILITY_EVIDENCE_PROTOCOL = "accessibility-evidence.v1"
AccessibilityEvidenceCaptureState = Literal["observed", "not_run", "not_applicable"]

AccessibilityObservationKind = Literal[
    "keyboard_pass",
    "screen_reader_note",
    "focus_order_issue",
    "wrapping_issue",
    "contrast_observation",
    "responsive_review",
]

AccessibilitySeverity = Literal["info", "low", "medium", "high", "blocker"]
AccessibilityDisposition = Literal[
    "open",
    "paired_with_feedback",
    "resolved_locally",
    "accepted_with_risk",
    "needs_follow_up",
]


class AccessibilityEvidenceCapture(BaseModel):
    """Bounded metadata for one advisory accessibility observation."""

    model_config = ConfigDict(extra="forbid")

    capture_state: AccessibilityEvidenceCaptureState = "observed"
    observation_kind: AccessibilityObservationKind
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    environment: str | None = Field(default=None, max_length=200)
    tool: str | None = Field(default="manual", max_length=200)
    route_label: str | None = Field(default=None, max_length=300)
    reviewer_label: str | None = Field(default=None, max_length=200)
    observed_issue: str | None = Field(default=None, max_length=2000)
    severity: AccessibilitySeverity = "medium"
    disposition: AccessibilityDisposition = "open"
    follow_up: str | None = Field(default=None, max_length=2000)
    paired_tool_output_label: str | None = Field(default=None, max_length=300)
    skip_reason: str | None = Field(default=None, max_length=1000)
    skipped_cases: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_capture_state(self) -> AccessibilityEvidenceCapture:
        if self.capture_state == "observed":
            missing = [
                name
                for name, value in (
                    ("environment", self.environment),
                    ("observed_issue", self.observed_issue),
                )
                if value in (None, "")
            ]
            if missing:
                raise ValueError(
                    "observed accessibility evidence requires " + ", ".join(missing)
                )
            return self
        if not self.skip_reason and not self.skipped_cases:
            raise ValueError(
                "skipped accessibility evidence requires skip_reason or skipped_cases"
            )
        if self.observed_issue:
            raise ValueError(
                "skipped accessibility evidence cannot include an observed issue"
            )
        if self.follow_up is not None or self.paired_tool_output_label is not None:
            raise ValueError(
                "skipped accessibility evidence cannot cite follow-up or paired output"
            )
        return self


def accessibility_evidence_note(capture: AccessibilityEvidenceCapture) -> str:
    """Render accessibility metadata as summary-first manual evidence note text."""

    skipped_cases = capture.skipped_cases or ["none recorded"]
    limitations = capture.limitations or ["none recorded beyond advisory posture"]
    route_label = capture.route_label or "unknown"
    reviewer_label = capture.reviewer_label or "unknown"
    follow_up = capture.follow_up or "none recorded"
    paired_tool_output = capture.paired_tool_output_label or "none"
    return "\n".join(
        [
            f"protocol: {ACCESSIBILITY_EVIDENCE_PROTOCOL}",
            f"capture_state: {capture.capture_state}",
            f"observation_kind: {capture.observation_kind}",
            f"summary: {capture.summary}",
            f"environment: {capture.environment or 'unknown'}",
            f"tool: {capture.tool or 'unknown'}",
            f"route_label: {route_label}",
            f"reviewer_label: {reviewer_label}",
            f"observed_issue: {capture.observed_issue or 'not observed'}",
            f"severity: {capture.severity}",
            f"disposition: {capture.disposition}",
            f"follow_up: {follow_up}",
            f"paired_tool_output_label: {paired_tool_output}",
            f"skip_reason: {capture.skip_reason or 'not applicable'}",
            f"skipped_cases: {'; '.join(skipped_cases)}",
            f"limitations: {'; '.join(limitations)}",
            "non_claims: advisory accessibility evidence; not WCAG certification",
        ]
    )


def accessibility_evidence_limitations(
    capture: AccessibilityEvidenceCapture,
) -> list[str]:
    """Bounded limitations for accessibility review evidence."""

    limitations = [
        "accessibility evidence is advisory review-loop evidence",
        f"capture state: {capture.capture_state}",
        f"observation kind: {capture.observation_kind}",
        f"severity: {capture.severity}",
        f"disposition: {capture.disposition}",
    ]
    if capture.capture_state != "observed":
        limitations.extend(
            [
                "skipped accessibility evidence is not a pass",
                (
                    "assistive technology, keyboard, contrast, or environment "
                    "details may be unknown"
                ),
            ]
        )
        if capture.skip_reason:
            limitations.append(f"skip reason: {capture.skip_reason}")
    if capture.follow_up is not None:
        limitations.append(f"follow-up: {capture.follow_up}")
    if capture.paired_tool_output_label is not None:
        limitations.append(f"paired tool output: {capture.paired_tool_output_label}")
    limitations.extend(f"skipped: {item}" for item in capture.skipped_cases[:5])
    limitations.extend(capture.limitations[:5])
    return limitations[:20]


def accessibility_evidence_non_claims() -> list[str]:
    """Reviewer-safe non-claims for accessibility evidence."""

    return [
        "not accessibility certification",
        "not WCAG conformance",
        "not deterministic release authority",
        "skipped accessibility evidence is not a pass",
        "not review approval",
        "not publication authority",
    ]


__all__ = [
    "ACCESSIBILITY_EVIDENCE_PROTOCOL",
    "AccessibilityDisposition",
    "AccessibilityEvidenceCaptureState",
    "AccessibilityEvidenceCapture",
    "AccessibilityObservationKind",
    "AccessibilitySeverity",
    "accessibility_evidence_limitations",
    "accessibility_evidence_non_claims",
    "accessibility_evidence_note",
]
