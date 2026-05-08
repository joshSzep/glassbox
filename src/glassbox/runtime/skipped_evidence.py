"""Helpers for recognizing intentionally skipped advisory live evidence."""

from collections.abc import Iterable
from typing import Literal

from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord

SkippedEvidenceState = Literal["not_run", "not_applicable", "skipped"]
EvidenceCaptureState = Literal["observed", "not_run", "not_applicable", "skipped"]
SKIPPED_CAPTURE_STATE_PREFIX = "capture state: "
SKIPPED_REASON_PREFIX = "skip reason: "

LIVE_EVIDENCE_KINDS = {
    ManualEvidenceKind.BROWSER_OBSERVATION,
    ManualEvidenceKind.SCREENSHOT,
    ManualEvidenceKind.ACCESSIBILITY_NOTE,
}


def is_live_evidence(evidence: ManualEvidenceRecord) -> bool:
    return evidence.evidence_kind in LIVE_EVIDENCE_KINDS


def live_evidence_items(
    evidence: Iterable[ManualEvidenceRecord],
) -> list[ManualEvidenceRecord]:
    return [item for item in evidence if is_live_evidence(item)]


def skipped_evidence_state(
    evidence: ManualEvidenceRecord,
) -> SkippedEvidenceState | None:
    """Return retained skipped posture encoded in advisory evidence limitations."""

    text = [*evidence.limitations, *evidence.non_claims]
    for item in text:
        normalized = item.strip().lower()
        if normalized == skipped_capture_state_limitation("not_run"):
            return "not_run"
        if normalized == skipped_capture_state_limitation("not_applicable"):
            return "not_applicable"
        if normalized == skipped_capture_state_limitation("skipped"):
            return "skipped"
    return None


def is_skipped_live_evidence(evidence: ManualEvidenceRecord) -> bool:
    return is_live_evidence(evidence) and skipped_evidence_state(evidence) is not None


def skipped_live_evidence_items(
    evidence: Iterable[ManualEvidenceRecord],
) -> list[ManualEvidenceRecord]:
    return [item for item in evidence if is_skipped_live_evidence(item)]


def skipped_evidence_reason(evidence: ManualEvidenceRecord) -> str | None:
    for limitation in evidence.limitations:
        if limitation.lower().startswith(SKIPPED_REASON_PREFIX):
            return limitation.split(": ", 1)[1]
    return None


def skipped_evidence_label(evidence: ManualEvidenceRecord) -> str:
    state = skipped_evidence_state(evidence)
    if state is None:
        return "observed"
    return state.replace("_", " ")


def skipped_live_evidence_counts(
    evidence: Iterable[ManualEvidenceRecord],
) -> tuple[int, int, int]:
    skipped = skipped_live_evidence_items(evidence)
    browser = [
        item
        for item in skipped
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
        }
    ]
    accessibility = [
        item
        for item in skipped
        if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
    ]
    return len(skipped), len(browser), len(accessibility)


def skipped_live_evidence_summary(evidence: ManualEvidenceRecord) -> str:
    reason = skipped_evidence_reason(evidence)
    suffix = f"; reason: {reason}" if reason else ""
    return f"{skipped_evidence_label(evidence)}: {evidence.summary}{suffix}"


def skipped_capture_state_limitation(state: EvidenceCaptureState) -> str:
    return f"{SKIPPED_CAPTURE_STATE_PREFIX}{state}"


def skipped_reason_limitation(reason: str) -> str:
    return f"{SKIPPED_REASON_PREFIX}{reason}"


def skipped_case_limitations(cases: Iterable[str], *, limit: int = 5) -> list[str]:
    return [f"skipped: {item}" for item in list(cases)[:limit]]


__all__ = [
    "EvidenceCaptureState",
    "LIVE_EVIDENCE_KINDS",
    "SKIPPED_CAPTURE_STATE_PREFIX",
    "SKIPPED_REASON_PREFIX",
    "SkippedEvidenceState",
    "is_live_evidence",
    "is_skipped_live_evidence",
    "live_evidence_items",
    "skipped_capture_state_limitation",
    "skipped_case_limitations",
    "skipped_evidence_label",
    "skipped_evidence_reason",
    "skipped_evidence_state",
    "skipped_live_evidence_items",
    "skipped_live_evidence_counts",
    "skipped_live_evidence_summary",
    "skipped_reason_limitation",
]
