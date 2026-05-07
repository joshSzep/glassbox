"""Accessibility evidence action service."""

from collections.abc import Sequence

from glassbox.core import ChangesetId
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackId
from glassbox.runtime.accessibility_evidence import AccessibilityDisposition
from glassbox.runtime.accessibility_evidence import AccessibilityEvidenceCapture
from glassbox.runtime.accessibility_evidence import AccessibilityEvidenceCaptureState
from glassbox.runtime.accessibility_evidence import AccessibilityObservationKind
from glassbox.runtime.accessibility_evidence import AccessibilitySeverity
from glassbox.runtime.accessibility_evidence import accessibility_evidence_limitations
from glassbox.runtime.accessibility_evidence import accessibility_evidence_non_claims
from glassbox.runtime.accessibility_evidence import accessibility_evidence_note
from glassbox.runtime.changeset_models import ManualEvidenceRecordResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.manual_evidence_actions import ManualEvidenceActionService
from glassbox.services import ArtifactRepository


class AccessibilityEvidenceActionService:
    """Record advisory accessibility evidence through manual evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._manual_service = ManualEvidenceActionService(
            repository,
            artifact_repository,
        )

    def attach(
        self,
        changeset_id: ChangesetId,
        *,
        capture_state: AccessibilityEvidenceCaptureState = "observed",
        observation_kind: AccessibilityObservationKind,
        summary: str,
        source_label: str,
        environment: str | None = None,
        observed_issue: str | None = None,
        tool: str | None = "manual",
        route_label: str | None = None,
        reviewer_label: str | None = None,
        severity: AccessibilitySeverity = "medium",
        disposition: AccessibilityDisposition = "open",
        follow_up: str | None = None,
        paired_tool_output_label: str | None = None,
        skip_reason: str | None = None,
        skipped_cases: Sequence[str] = (),
        limitations: Sequence[str] = (),
        actor: str = "operator",
        target_kind: ManualEvidenceTargetKind = ManualEvidenceTargetKind.CHANGESET,
        target_id: str | None = None,
        feedback_id: ReviewFeedbackId | None = None,
        freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN,
    ) -> ManualEvidenceRecordResult:
        capture = AccessibilityEvidenceCapture(
            capture_state=capture_state,
            observation_kind=observation_kind,
            summary=summary,
            source_label=source_label,
            environment=environment,
            tool=tool,
            route_label=route_label,
            reviewer_label=reviewer_label,
            observed_issue=observed_issue,
            severity=severity,
            disposition=disposition,
            follow_up=follow_up,
            paired_tool_output_label=paired_tool_output_label,
            skip_reason=skip_reason,
            skipped_cases=list(skipped_cases),
            limitations=list(limitations),
        )
        result = self._manual_service.attach(
            changeset_id,
            evidence_kind=ManualEvidenceKind.ACCESSIBILITY_NOTE,
            summary=summary,
            source_label=source_label,
            actor=actor,
            target_kind=target_kind,
            target_id=target_id,
            feedback_id=feedback_id,
            note=accessibility_evidence_note(capture),
            freshness=freshness,
            extra_limitations=accessibility_evidence_limitations(capture),
            extra_non_claims=accessibility_evidence_non_claims(),
        )
        return result.model_copy(
            update={
                "safe_next_actions": [
                    *result.safe_next_actions,
                    "pair unresolved accessibility evidence with review feedback "
                    "before handoff",
                    "inspect docs/browser-accessibility-evidence.md before making "
                    "accessibility claims",
                ],
                "non_claims": [
                    *result.non_claims,
                    "accessibility evidence is advisory and local-only",
                    "accessibility evidence is not certification or WCAG conformance",
                ],
            }
        )


__all__ = ["AccessibilityEvidenceActionService"]
