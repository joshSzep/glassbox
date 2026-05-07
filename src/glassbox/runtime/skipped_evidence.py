"""Helpers for recognizing intentionally skipped advisory live evidence."""

from collections.abc import Iterable
from typing import Literal

from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord

SkippedEvidenceState = Literal["not_run", "not_applicable", "skipped"]

LIVE_EVIDENCE_KINDS = {
    ManualEvidenceKind.BROWSER_OBSERVATION,
    ManualEvidenceKind.SCREENSHOT,
    ManualEvidenceKind.ACCESSIBILITY_NOTE,
}


def is_live_evidence(evidence: ManualEvidenceRecord) -> bool:
    return evidence.evidence_kind in LIVE_EVIDENCE_KINDS


def skipped_evidence_state(
    evidence: ManualEvidenceRecord,
) -> SkippedEvidenceState | None:
    """Return retained skipped posture encoded in advisory evidence limitations."""

    text = [*evidence.limitations, *evidence.non_claims]
    for item in text:
        normalized = item.strip().lower()
        if normalized == "capture state: not_run":
            return "not_run"
        if normalized == "capture state: not_applicable":
            return "not_applicable"
    return None


def is_skipped_live_evidence(evidence: ManualEvidenceRecord) -> bool:
    return is_live_evidence(evidence) and skipped_evidence_state(evidence) is not None


def skipped_evidence_reason(evidence: ManualEvidenceRecord) -> str | None:
    for limitation in evidence.limitations:
        if limitation.lower().startswith("skip reason: "):
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
    skipped = [item for item in evidence if is_skipped_live_evidence(item)]
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


__all__ = [
    "LIVE_EVIDENCE_KINDS",
    "SkippedEvidenceState",
    "is_live_evidence",
    "is_skipped_live_evidence",
    "skipped_evidence_label",
    "skipped_evidence_reason",
    "skipped_evidence_state",
    "skipped_live_evidence_counts",
    "skipped_live_evidence_summary",
]
