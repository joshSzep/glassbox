"""Browser and dashboard evidence action service."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from glassbox.core import ChangesetId
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackId
from glassbox.runtime.browser_evidence import BrowserEvidenceCapture
from glassbox.runtime.browser_evidence import BrowserEvidenceCaptureState
from glassbox.runtime.browser_evidence import browser_evidence_limitations
from glassbox.runtime.browser_evidence import browser_evidence_local_reference
from glassbox.runtime.browser_evidence import browser_evidence_non_claims
from glassbox.runtime.browser_evidence import browser_evidence_note
from glassbox.runtime.changeset_models import ManualEvidenceRecordResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.manual_evidence_actions import ManualEvidenceActionService
from glassbox.services import ArtifactRepository


class BrowserEvidenceActionService:
    """Record advisory browser and dashboard evidence through manual evidence."""

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
        capture_state: BrowserEvidenceCaptureState = "observed",
        capture_kind: Literal["browser_check", "dashboard_walkthrough"],
        summary: str,
        source_label: str,
        route_label: str | None = None,
        environment: str | None = None,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
        browser: str | None = "unknown",
        observed_at: datetime | None = None,
        input_method: str | None = "unknown",
        console_checked: bool | None = None,
        skip_reason: str | None = None,
        screenshot_path_hint: str | None = None,
        screenshot_label: str = "local screenshot metadata",
        screenshot_media_type: str = "image/png",
        screenshot_size_bytes: int | None = None,
        screenshot_width: int | None = None,
        screenshot_height: int | None = None,
        skipped_cases: Sequence[str] = (),
        limitations: Sequence[str] = (),
        actor: str = "operator",
        target_kind: ManualEvidenceTargetKind = ManualEvidenceTargetKind.CHANGESET,
        target_id: str | None = None,
        feedback_id: ReviewFeedbackId | None = None,
        freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN,
    ) -> ManualEvidenceRecordResult:
        capture = BrowserEvidenceCapture(
            capture_state=capture_state,
            capture_kind=capture_kind,
            summary=summary,
            source_label=source_label,
            route_label=route_label,
            environment=environment,
            browser=browser,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            observed_at=observed_at,
            input_method=input_method,
            console_checked=console_checked,
            skip_reason=skip_reason,
            screenshot_path_hint=screenshot_path_hint,
            screenshot_label=screenshot_label,
            screenshot_media_type=screenshot_media_type,
            screenshot_size_bytes=screenshot_size_bytes,
            screenshot_width=screenshot_width,
            screenshot_height=screenshot_height,
            skipped_cases=list(skipped_cases),
            limitations=list(limitations),
        )
        local_reference = browser_evidence_local_reference(capture)
        result = self._manual_service.attach(
            changeset_id,
            evidence_kind=ManualEvidenceKind.BROWSER_OBSERVATION,
            summary=summary,
            source_label=source_label,
            actor=actor,
            target_kind=target_kind,
            target_id=target_id,
            feedback_id=feedback_id,
            note=browser_evidence_note(capture),
            local_file_label=local_reference.label if local_reference else None,
            local_file_path_hint=(
                local_reference.path_hint if local_reference is not None else None
            ),
            local_file_media_type=(
                local_reference.media_type if local_reference is not None else None
            ),
            local_file_size_bytes=(
                local_reference.size_bytes if local_reference is not None else None
            ),
            local_file_width=local_reference.width
            if local_reference is not None
            else None,
            local_file_height=(
                local_reference.height if local_reference is not None else None
            ),
            freshness=freshness,
            observed_at=observed_at,
            extra_limitations=browser_evidence_limitations(capture),
            extra_non_claims=browser_evidence_non_claims(),
        )
        return result.model_copy(
            update={
                "safe_next_actions": [
                    *result.safe_next_actions,
                    "rerun the same browser/dashboard route before relying on stale "
                    "live evidence",
                    "inspect docs/browser-accessibility-evidence.md for advisory "
                    "live evidence limits",
                ],
                "non_claims": [
                    *result.non_claims,
                    "browser/dashboard evidence is advisory and local-only",
                    "browser/dashboard evidence is not deterministic release authority",
                ],
            }
        )


__all__ = ["BrowserEvidenceActionService"]
