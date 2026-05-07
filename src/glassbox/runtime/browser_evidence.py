"""Browser and dashboard live evidence capture helpers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from glassbox.runtime.manual_evidence import ManualEvidenceLocalReference

BROWSER_EVIDENCE_PROTOCOL = "browser-accessibility-evidence.v1"
BrowserEvidenceCaptureState = Literal["observed", "not_run", "not_applicable"]


class BrowserEvidenceCapture(BaseModel):
    """Bounded metadata for one advisory browser or dashboard observation."""

    model_config = ConfigDict(extra="forbid")

    capture_state: BrowserEvidenceCaptureState = "observed"
    capture_kind: Literal["browser_check", "dashboard_walkthrough"]
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    route_label: str | None = Field(default=None, max_length=300)
    environment: str | None = Field(default=None, max_length=200)
    browser: str | None = Field(default="unknown", max_length=200)
    viewport_width: int | None = Field(default=None, ge=1, le=10000)
    viewport_height: int | None = Field(default=None, ge=1, le=10000)
    observed_at: datetime | None = None
    input_method: str | None = Field(default="unknown", max_length=100)
    console_checked: bool | None = None
    skip_reason: str | None = Field(default=None, max_length=1000)
    screenshot_path_hint: str | None = Field(default=None, max_length=500)
    screenshot_label: str = Field(
        default="local screenshot metadata",
        min_length=1,
        max_length=200,
    )
    screenshot_media_type: str = Field(
        default="image/png", min_length=1, max_length=100
    )
    screenshot_size_bytes: int | None = Field(default=None, ge=0)
    screenshot_width: int | None = Field(default=None, ge=1, le=10000)
    screenshot_height: int | None = Field(default=None, ge=1, le=10000)
    skipped_cases: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_capture_state(self) -> BrowserEvidenceCapture:
        if self.capture_state == "observed":
            missing = [
                name
                for name, value in (
                    ("route_label", self.route_label),
                    ("environment", self.environment),
                    ("viewport_width", self.viewport_width),
                    ("viewport_height", self.viewport_height),
                )
                if value in (None, "")
            ]
            if missing:
                raise ValueError(
                    "observed browser evidence requires " + ", ".join(missing)
                )
            return self
        if not self.skip_reason and not self.skipped_cases:
            raise ValueError(
                "skipped browser evidence requires skip_reason or skipped_cases"
            )
        if self.observed_at is not None:
            raise ValueError("skipped browser evidence cannot include observed_at")
        if self.screenshot_path_hint is not None:
            raise ValueError(
                "skipped browser evidence cannot include screenshot metadata"
            )
        if self.console_checked is True:
            raise ValueError(
                "skipped browser evidence cannot claim console was checked"
            )
        return self


def browser_evidence_note(capture: BrowserEvidenceCapture) -> str:
    """Render capture metadata as summary-first manual evidence note text."""

    skipped_cases = capture.skipped_cases or ["none recorded"]
    limitations = capture.limitations or ["none recorded beyond live advisory posture"]
    console_checked = (
        "unknown" if capture.console_checked is None else str(capture.console_checked)
    )
    observed_at = (
        capture.observed_at.isoformat()
        if capture.observed_at is not None
        else "unknown"
    )
    screenshot_metadata = (
        "local-only reference attached" if capture.screenshot_path_hint else "none"
    )
    return "\n".join(
        [
            f"protocol: {BROWSER_EVIDENCE_PROTOCOL}",
            f"capture_state: {capture.capture_state}",
            f"capture_kind: {capture.capture_kind}",
            f"summary: {capture.summary}",
            f"route_label: {capture.route_label or 'unknown'}",
            f"environment: {capture.environment or 'unknown'}",
            f"browser: {capture.browser or 'unknown'}",
            f"viewport: {_viewport_label(capture)}",
            f"observed_at: {observed_at}",
            f"input_method: {capture.input_method or 'unknown'}",
            f"console_checked: {console_checked}",
            f"skip_reason: {capture.skip_reason or 'not applicable'}",
            f"screenshot_metadata: {screenshot_metadata}",
            f"skipped_cases: {'; '.join(skipped_cases)}",
            f"limitations: {'; '.join(limitations)}",
            "non_claims: advisory live evidence; not deterministic release authority",
        ]
    )


def browser_evidence_local_reference(
    capture: BrowserEvidenceCapture,
) -> ManualEvidenceLocalReference | None:
    """Return metadata-only screenshot reference when one was supplied."""

    if capture.screenshot_path_hint is None:
        return None
    return ManualEvidenceLocalReference(
        label=capture.screenshot_label,
        path_hint=capture.screenshot_path_hint,
        media_type=capture.screenshot_media_type,
        size_bytes=capture.screenshot_size_bytes,
        width=capture.screenshot_width,
        height=capture.screenshot_height,
    )


def browser_evidence_limitations(capture: BrowserEvidenceCapture) -> list[str]:
    """Bounded limitations that keep live evidence advisory."""

    limitations = [
        "browser/dashboard evidence is advisory live evidence",
        "browser/dashboard evidence does not replace deterministic checks",
        f"capture state: {capture.capture_state}",
    ]
    if capture.capture_state != "observed":
        limitations.extend(
            [
                "skipped browser/dashboard evidence is not a pass",
                "browser, viewport, console, or environment details may be unknown",
            ]
        )
        if capture.skip_reason:
            limitations.append(f"skip reason: {capture.skip_reason}")
    if capture.screenshot_path_hint is not None:
        limitations.append("screenshot metadata is local-only")
    limitations.extend(f"skipped: {item}" for item in capture.skipped_cases[:5])
    limitations.extend(capture.limitations[:5])
    return limitations[:20]


def browser_evidence_non_claims() -> list[str]:
    """Reviewer-safe non-claims for browser and dashboard evidence."""

    return [
        "not deterministic release authority",
        "not retained command evidence",
        "not release gate evidence",
        "skipped browser/dashboard evidence is not a pass",
        "not review approval",
        "not publication authority",
    ]


def _viewport_label(capture: BrowserEvidenceCapture) -> str:
    if capture.viewport_width is None or capture.viewport_height is None:
        return "unknown"
    return f"{capture.viewport_width}x{capture.viewport_height}"


__all__ = [
    "BROWSER_EVIDENCE_PROTOCOL",
    "BrowserEvidenceCapture",
    "BrowserEvidenceCaptureState",
    "browser_evidence_limitations",
    "browser_evidence_local_reference",
    "browser_evidence_non_claims",
    "browser_evidence_note",
]
