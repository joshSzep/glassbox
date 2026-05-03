"""Runtime service for deriving and inspecting reviewable changesets."""

import json
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import ChangesetVerificationState
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackFixupInventoryAttached
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.core import TaskVerificationId
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.runtime.accessibility_evidence import AccessibilityDisposition
from glassbox.runtime.accessibility_evidence import AccessibilityEvidenceCapture
from glassbox.runtime.accessibility_evidence import AccessibilityObservationKind
from glassbox.runtime.accessibility_evidence import AccessibilitySeverity
from glassbox.runtime.accessibility_evidence import accessibility_evidence_limitations
from glassbox.runtime.accessibility_evidence import accessibility_evidence_non_claims
from glassbox.runtime.accessibility_evidence import accessibility_evidence_note
from glassbox.runtime.browser_evidence import BrowserEvidenceCapture
from glassbox.runtime.browser_evidence import browser_evidence_limitations
from glassbox.runtime.browser_evidence import browser_evidence_local_reference
from glassbox.runtime.browser_evidence import browser_evidence_non_claims
from glassbox.runtime.browser_evidence import browser_evidence_note
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_actions import ChangesetActionService
from glassbox.runtime.changeset_derivation import ChangesetDerivationService
from glassbox.runtime.changeset_detail import (
    changeset_command_evidence_summary as _changeset_command_evidence_summary,
)
from glassbox.runtime.changeset_detail import (
    manual_evidence_for_preview as _manual_evidence_for_preview,
)
from glassbox.runtime.changeset_detail import (
    review_feedback_for_preview as _review_feedback_for_preview,
)
from glassbox.runtime.changeset_detail import (
    review_response_summary_for_preview as _review_response_summary_for_preview,
)
from glassbox.runtime.changeset_inventory_status import (
    inventory_status as _inventory_status,
)
from glassbox.runtime.changeset_inventory_status import (
    review_fixup_inventory_freshness as _review_fixup_inventory_freshness,
)
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetDerivationResult
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_models import ChangesetInventoryRefreshResult
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changeset_models import ChangesetVerificationEvidenceRecordResult
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_models import ChangesetVerificationRecipePreview
from glassbox.runtime.changeset_models import ChangesetVerificationReviewLoopSummary
from glassbox.runtime.changeset_models import ManualEvidenceRecordResult
from glassbox.runtime.changeset_models import ReviewFeedbackFixupInventoryResult
from glassbox.runtime.changeset_models import ReviewFeedbackRecordResult
from glassbox.runtime.changeset_queries import ChangesetQueryService
from glassbox.runtime.changeset_repository_contracts import (
    ChangesetDerivationRepository,
)
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_topology import ChangesetTopologyImpact
from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.changeset_workspace_diff import (
    diff_summary_without_local_state as _diff_summary_without_local_state,
)
from glassbox.runtime.changeset_workspace_diff import (
    workspace_diff_source_digest as _workspace_diff_source_digest,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.manual_evidence_actions import ManualEvidenceActionService
from glassbox.runtime.review_briefs import REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_briefs import review_brief_artifact_json
from glassbox.runtime.review_briefs import review_brief_markdown
from glassbox.runtime.review_feedback_actions import ReviewFeedbackActionService
from glassbox.runtime.review_responses import REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFixupInventoryStatus
from glassbox.runtime.review_responses import review_fixup_inventory_artifact_json
from glassbox.runtime.review_responses import (
    review_fixup_inventory_from_change_inventory,
)
from glassbox.runtime.review_responses import review_fixup_inventory_status
from glassbox.runtime.workspace_profile import load_workspace_profile
from glassbox.services import ArtifactRepository
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool


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
        capture_kind: Literal["browser_check", "dashboard_walkthrough"],
        summary: str,
        source_label: str,
        route_label: str,
        environment: str,
        viewport_width: int,
        viewport_height: int,
        browser: str = "unknown",
        observed_at: datetime | None = None,
        input_method: str = "unknown",
        console_checked: bool | None = None,
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
        observation_kind: AccessibilityObservationKind,
        summary: str,
        source_label: str,
        environment: str,
        observed_issue: str,
        tool: str = "manual",
        route_label: str | None = None,
        reviewer_label: str | None = None,
        severity: AccessibilitySeverity = "medium",
        disposition: AccessibilityDisposition = "open",
        follow_up: str | None = None,
        paired_tool_output_label: str | None = None,
        skipped_cases: Sequence[str] = (),
        limitations: Sequence[str] = (),
        actor: str = "operator",
        target_kind: ManualEvidenceTargetKind = ManualEvidenceTargetKind.CHANGESET,
        target_id: str | None = None,
        feedback_id: ReviewFeedbackId | None = None,
        freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN,
    ) -> ManualEvidenceRecordResult:
        capture = AccessibilityEvidenceCapture(
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


class ReviewFeedbackFixupInventoryService:
    """Attach bounded fixup inventory evidence to review feedback."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def record_workspace_inventory(
        self,
        feedback_id: ReviewFeedbackId,
        workspace_root: Path,
        *,
        source_kind: ReviewFixupSourceKind = (
            ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT
        ),
        source_summary: str = "operator recorded response-linked workspace inventory",
        recorded_by: str = "operator",
    ) -> ReviewFeedbackFixupInventoryResult:
        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for fixup inventory")
        feedback = self._require_feedback(feedback_id)
        changeset = self._require_changeset(feedback.changeset_id)
        scopes = self._repository.list_review_feedback_scopes(
            feedback.session_id,
            feedback.feedback_id,
        )
        latest_inventory = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        diff_summary = await DiffSummaryTool(workspace_root).execute(
            DiffSummaryArgs(
                scope=DiffSummaryScope.WORKSPACE,
                max_files=1000,
                inline_file_limit=200,
            )
        )
        diff_summary = _diff_summary_without_local_state(diff_summary)
        inventory = change_inventory_from_diff_summary(
            diff_summary,
            changeset_id=changeset.changeset_id,
            provenance_events=self._repository.read_session_events(
                changeset.session_id
            ),
        )
        source_digest = _workspace_diff_source_digest(workspace_root)
        freshness = (
            ChangesetInventoryFreshness.UNKNOWN
            if source_digest.error is not None
            else ChangesetInventoryFreshness.FRESH
        )
        fixup_inventory = review_fixup_inventory_from_change_inventory(
            inventory,
            feedback=feedback,
            scopes=scopes,
            source_kind=source_kind,
            source_summary=source_summary,
            source_digest=source_digest.digest,
            inventory_freshness=freshness,
            latest_changeset_inventory_artifact_id=(
                str(latest_inventory.artifact_id)
                if latest_inventory is not None
                else None
            ),
        )
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            review_fixup_inventory_artifact_json(fixup_inventory),
            suffix=".review-fixup-inventory.json",
        )
        status = review_fixup_inventory_status(
            feedback_id=feedback.feedback_id,
            changeset_id=changeset.changeset_id,
            recorded_source_digest=source_digest.digest,
            current_source_digest=source_digest.digest,
            current_error=source_digest.error,
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ReviewFeedbackFixupInventoryAttached(
                        feedback_id=feedback.feedback_id,
                        changeset_id=changeset.changeset_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION,
                        source_kind=source_kind,
                        source_summary=source_summary,
                        source_digest=source_digest.digest,
                        inventory_freshness=freshness,
                        changed_path_count=fixup_inventory.changed_path_count,
                        matched_scope_path_count=(
                            fixup_inventory.matched_scope_path_count
                        ),
                        stale=status.stale,
                        stale_reason=status.reason,
                        recorded_by=recorded_by,
                        paths=fixup_inventory.paths,
                        task_id=feedback.task_id or changeset.task_id,
                        turn_id=feedback.turn_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return ReviewFeedbackFixupInventoryResult(
            feedback_id=feedback.feedback_id,
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            inventory=fixup_inventory,
            event=stored[0],
            status=status,
        )

    def assess_record_freshness(
        self,
        record: ReviewFeedbackFixupInventoryRecord,
        workspace_root: Path,
    ) -> ReviewFixupInventoryStatus:
        return _review_fixup_inventory_freshness(record, workspace_root)

    def _require_feedback(self, feedback_id: ReviewFeedbackId) -> ReviewFeedbackRecord:
        feedback = self._repository.get_review_feedback(feedback_id)
        if feedback is None:
            raise ValueError(f"unknown review feedback: {feedback_id}")
        return feedback

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


class ChangesetVerificationService:
    """Preview and record changeset verification posture from retained evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def preview_plan(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
    ) -> ChangesetVerificationPlanPreview:
        changeset = self._require_changeset(changeset_id)
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        changed_paths = _inventory_paths_for_preview(inventory)
        recommendation, recommendation_limitations = _recommendation_for_preview(
            workspace_root,
            changed_paths,
        )
        topology_impacts, topology_limitations = derive_changeset_topology_impacts(
            workspace_root=workspace_root,
            changed_paths=changed_paths,
        )
        limitations = [
            *inventory_limitations,
            *recommendation_limitations,
            *topology_limitations,
            *(
                [inventory_status.reason]
                if inventory_status.reason is not None
                and inventory_status.freshness != ChangesetInventoryFreshness.FRESH
                else []
            ),
        ]
        ledger = self._task_ledger_for_changeset(changeset)
        inventory_freshness = inventory_status.freshness
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        retained_artifact_ids = _artifact_ids_from_readiness(readiness)
        review_response_summary = _review_response_summary_for_preview(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )
        manual_evidence = _manual_evidence_for_preview(self._repository, changeset)
        review_loop_summary = _review_loop_verification_summary(
            changeset=changeset,
            response_summary=review_response_summary,
            manual_evidence=manual_evidence,
            readiness=readiness,
            topology_impacts=topology_impacts,
        )
        return ChangesetVerificationPlanPreview(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            inventory_artifact_id=(
                inventory_record.artifact_id if inventory_record is not None else None
            ),
            inventory_freshness=inventory_freshness,
            changed_paths=changed_paths,
            recommended_commands=_preview_commands(
                readiness,
                recommendation,
            ),
            eval_profiles=_eval_profile_ids_for_preview(recommendation),
            recipes=_recipe_previews(recommendation),
            topology_impacts=topology_impacts,
            review_loop_summary=review_loop_summary,
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            expected_scope=changed_paths,
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            limitations=limitations,
            safe_next_actions=list(
                dict.fromkeys(
                    [
                        *readiness.safe_next_actions,
                        *review_loop_summary.safe_next_actions,
                    ]
                )
            ),
            non_claims=[
                *readiness.non_claims,
                *review_loop_summary.non_claims,
                "verification plan preview does not run commands",
                (
                    "publish, deploy, push, and upload commands are not "
                    "recommended as verification"
                ),
            ],
        )

    def record_existing_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        task_id: TaskId | None = None,
        verification_id: TaskVerificationId | None = None,
    ) -> ChangesetVerificationEvidenceRecordResult:
        changeset = self._require_changeset(changeset_id)
        resolved_task_id = task_id or changeset.task_id
        if resolved_task_id is None:
            raise ValueError(
                "task_id is required when the changeset is not task-backed"
            )
        ledger = self._repository.list_task_verification_ledger(
            changeset.session_id,
            resolved_task_id,
        )
        if verification_id is not None:
            ledger = [
                entry for entry in ledger if entry.verification_id == verification_id
            ]
        if not ledger:
            raise ValueError("no retained task verification evidence matched")
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, _limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        recommendation, _limitations = _recommendation_for_preview(
            workspace_root,
            _inventory_paths_for_preview(inventory),
        )
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_status.freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        selected = sorted(ledger, key=lambda entry: entry.last_sequence)
        primary = selected[-1]
        retained_artifact_ids = _artifact_ids_from_readiness(readiness)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset.changeset_id,
                        state=readiness.state,
                        summary=readiness.summary,
                        verification_id=primary.verification_id,
                        artifact_id=primary.latest_artifact_id
                        or primary.latest_failed_artifact_id,
                        task_id=resolved_task_id,
                        stale_count=readiness.stale_count,
                        missing_count=readiness.missing_count,
                        failed_count=readiness.failed_count,
                        accepted_risk_count=readiness.accepted_risk_count,
                    ),
                )
            ]
        )
        return ChangesetVerificationEvidenceRecordResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            selected_verification_ids=[entry.verification_id for entry in selected],
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            event=stored[0],
        )

    def _task_ledger_for_changeset(
        self,
        changeset: ChangesetRecord,
    ) -> list[TaskVerificationLedgerRecord]:
        if changeset.task_id is None:
            return []
        return self._repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


class ChangesetReviewBriefService:
    """Generate reviewer-safe briefs from deterministic changeset evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def generate(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        created_by: str = "operator",
    ) -> ChangesetReviewBriefGenerationResult:
        """Generate and retain one redacted review brief for a changeset."""

        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for review briefs")
        changeset = self._require_changeset(changeset_id)
        sources = self._repository.list_changeset_sources(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        verification_posture = self._repository.get_changeset_verification_posture(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset.changeset_id, workspace_root)
        command_evidence = _changeset_command_evidence_summary(
            self._repository,
            changeset,
        )
        review_feedback = _review_feedback_for_preview(self._repository, changeset)
        review_response_summary = _review_response_summary_for_preview(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )
        manual_evidence = _manual_evidence_for_preview(self._repository, changeset)
        limitations = _review_brief_limitations(
            sources=sources,
            inventory=inventory,
            inventory_status=inventory_status,
            inventory_limitations=inventory_limitations,
            verification_plan=verification_plan,
            command_evidence=command_evidence,
            review_response_summary=review_response_summary,
            manual_evidence=manual_evidence,
        )
        review_state, blockers = _review_readiness_state(
            inventory_status=inventory_status,
            verification_plan=verification_plan,
            changeset=changeset,
            review_response_summary=review_response_summary,
        )
        brief = _review_brief_artifact(
            changeset=changeset,
            sources=sources,
            inventory_record=inventory_record,
            inventory=inventory,
            inventory_status=inventory_status,
            verification_posture=verification_posture,
            verification_plan=verification_plan,
            command_evidence=command_evidence,
            review_feedback=review_feedback,
            review_response_summary=review_response_summary,
            manual_evidence=manual_evidence,
            limitations=limitations,
        )
        content = review_brief_artifact_json(brief)
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            content,
            suffix=".changeset-review-brief.json",
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReviewBriefCreated(
                        changeset_id=changeset.changeset_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION,
                        render_targets=brief.render_targets,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        created_by=created_by,
                        redacted=brief.redacted,
                        local_only=brief.local_only,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReadinessDecided(
                        changeset_id=changeset.changeset_id,
                        readiness_kind=ChangesetReadinessKind.REVIEW,
                        state=review_state,
                        reason=_review_readiness_reason(review_state, blockers),
                        blockers=blockers,
                        safe_next_actions=brief.safe_inspection_commands,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        review_brief_artifact_id=artifact.artifact_id,
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        accepted_risk_count=changeset.accepted_risk_count,
                        decided_by=created_by,
                    ),
                ),
            ]
        )
        return ChangesetReviewBriefGenerationResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            brief=brief,
            markdown=review_brief_markdown(brief),
            event=stored[0],
            readiness_event=stored[1],
            limitations=limitations,
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


def _changeset_inventory_artifact_path(
    session_id: SessionId,
    artifact_id: ArtifactId,
) -> Path:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.changeset-inventory.json"
    )


def _inventory_paths_for_preview(
    inventory: ChangeInventoryArtifact | None,
) -> list[str]:
    if inventory is None:
        return []
    return [entry.path for entry in inventory.paths[:100]]


def _safe_eval_recommendation(
    recommendation: EvalRecommendationReport | None,
) -> EvalRecommendationReport | None:
    if recommendation is None:
        return None
    recipes = [
        recipe.model_copy(
            update={
                "commands": [
                    command
                    for command in recipe.commands
                    if _is_safe_verification_command(command)
                ]
            }
        )
        for recipe in recommendation.recipes
    ]
    return recommendation.model_copy(
        update={
            "suggested_commands": [
                command
                for command in recommendation.suggested_commands
                if _is_safe_verification_command(command)
            ],
            "fallback_policy_commands": [
                command
                for command in recommendation.fallback_policy_commands
                if _is_safe_verification_command(command)
            ],
            "recipes": recipes,
        }
    )


def _recommendation_for_preview(
    workspace_root: Path,
    changed_paths: list[str],
) -> tuple[EvalRecommendationReport | None, list[str]]:
    if not changed_paths:
        return None, []
    try:
        return (
            _safe_eval_recommendation(
                recommend_eval_change_impact(
                    workspace_root,
                    touched_paths=changed_paths,
                )
            ),
            [],
        )
    except ValueError as exc:
        return None, [f"eval recommendation unavailable: {exc}"]


def _preview_commands(
    readiness: ChangesetVerificationReadiness,
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    commands = (
        list(recommendation.suggested_commands) if recommendation is not None else []
    )
    for requirement in readiness.requirements:
        if requirement.command:
            commands.append(" ".join(requirement.command))
    return [
        command
        for command in dict.fromkeys(commands)
        if _is_safe_verification_command(command)
    ]


def _is_safe_verification_command(command: str) -> bool:
    tokens = {part.lower() for part in command.replace(";", " ").split()}
    blocked = {
        "deploy",
        "publish",
        "push",
        "rm",
        "upload",
        "release",
        "release:publish",
    }
    return not tokens.intersection(blocked)


def _review_loop_verification_summary(
    *,
    changeset: ChangesetRecord,
    response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord],
    readiness: ChangesetVerificationReadiness,
    topology_impacts: Sequence[ChangesetTopologyImpact],
) -> ChangesetVerificationReviewLoopSummary:
    response_state_counts: dict[str, int] = {}
    for item in response_summary.items:
        key = item.response_state.value
        response_state_counts[key] = response_state_counts.get(key, 0) + 1

    manual_evidence_kind_counts: dict[str, int] = {}
    for item in manual_evidence:
        key = item.evidence_kind.value
        manual_evidence_kind_counts[key] = manual_evidence_kind_counts.get(key, 0) + 1

    missing_response_verification_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.MISSING
    )
    failed_response_verification_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.FAILED
    )
    accepted_risk_response_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.ACCEPTED_WITH_RISK
    )
    browser_evidence_count = sum(
        1
        for item in manual_evidence
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
        }
    )
    accessibility_evidence_count = sum(
        1
        for item in manual_evidence
        if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
    )
    safe_next_actions = [
        *response_summary.safe_next_actions,
        (
            "glassbox changeset evidence list --changeset "
            f"{changeset.changeset_id} --cwd ."
        ),
        f"glassbox changeset verification-plan {changeset.changeset_id} --cwd .",
    ]
    limitations: list[str] = []
    if manual_evidence:
        limitations.append(
            "manual evidence can inform verification choice but is not retained "
            "verification proof"
        )
    if missing_response_verification_count:
        limitations.append(
            "one or more review responses lack retained verification mapped to "
            "their fixup paths"
        )
    return ChangesetVerificationReviewLoopSummary(
        feedback_count=response_summary.total_feedback_count,
        open_feedback_count=response_summary.open_count,
        response_state_counts=response_state_counts,
        stale_response_count=response_summary.stale_response_count,
        missing_response_verification_count=missing_response_verification_count,
        failed_response_verification_count=failed_response_verification_count,
        accepted_risk_response_count=accepted_risk_response_count,
        manual_evidence_count=len(manual_evidence),
        manual_evidence_kind_counts=manual_evidence_kind_counts,
        browser_evidence_count=browser_evidence_count,
        accessibility_evidence_count=accessibility_evidence_count,
        stale_check_count=readiness.stale_count,
        topology_impact_count=len(topology_impacts),
        retained_verification_state=readiness.state,
        safe_next_actions=list(dict.fromkeys(safe_next_actions)),
        limitations=limitations,
        non_claims=[
            (
                "manual evidence suggests context only; retained verification "
                "decides check state"
            ),
            "browser and accessibility evidence remain advisory review-loop context",
            "verification plan output is preview-only and does not run commands",
        ],
    )


def _eval_profile_ids_for_preview(
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    if recommendation is None:
        return []
    profile_ids = [profile.profile_id for profile in recommendation.profiles]
    for recipe in recommendation.recipes:
        profile_ids.extend(recipe.profile_ids)
    return list(dict.fromkeys(profile_ids))


def _recipe_previews(
    recommendation: EvalRecommendationReport | None,
) -> list[ChangesetVerificationRecipePreview]:
    if recommendation is None:
        return []
    return [
        ChangesetVerificationRecipePreview(
            recipe_id=recipe.recipe_id,
            title=recipe.title,
            confidence=recipe.confidence,
            source=recipe.source,
            matched_paths=recipe.matched_paths,
            component_ids=recipe.component_ids,
            commands=recipe.commands,
            profile_ids=recipe.profile_ids,
            case_ids=recipe.case_ids,
            notes=recipe.notes,
            limitations=recipe.limitations,
        )
        for recipe in recommendation.recipes
    ]


def _artifact_ids_from_readiness(
    readiness: ChangesetVerificationReadiness,
) -> list[ArtifactId]:
    artifact_ids = [
        requirement.artifact_id
        for requirement in readiness.requirements
        if requirement.artifact_id is not None
    ]
    return list(dict.fromkeys(artifact_ids))


def _review_brief_artifact(
    *,
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    command_evidence: ChangesetCommandEvidenceSummary,
    review_feedback: list[ReviewFeedbackRecord],
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
    limitations: list[str],
) -> ReviewBriefArtifact:
    return ReviewBriefArtifact(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        task_id=changeset.task_id,
        branch_search_id=changeset.branch_search_id,
        branch_candidate_id=changeset.branch_candidate_id,
        local_only=_review_brief_local_only(
            sources,
            inventory_record,
            verification_posture,
            command_evidence,
            manual_evidence,
        ),
        objective=changeset.objective,
        change_summary=_review_brief_change_summary(changeset),
        changed_file_inventory=_review_brief_inventory_section(
            inventory_record,
            inventory,
            inventory_status,
        ),
        affected_subsystems=_review_brief_topology_section(verification_plan),
        provenance=_review_brief_provenance_section(sources, inventory),
        lifecycle_summary=_review_brief_lifecycle_section(
            changeset,
            review_response_summary,
            manual_evidence,
            verification_plan,
        ),
        review_feedback=_review_brief_feedback_section(review_feedback),
        review_responses=_review_brief_response_section(review_response_summary),
        manual_evidence=_review_brief_manual_evidence_section(manual_evidence),
        live_review_evidence=_review_brief_live_evidence_section(manual_evidence),
        verification=_review_brief_verification_section(
            verification_posture,
            verification_plan,
        ),
        stale_verification=_review_brief_stale_verification_section(
            review_response_summary,
            verification_plan,
        ),
        command_evidence=_review_brief_command_evidence_section(command_evidence),
        branch_candidate_rationale=_review_brief_branch_candidate_section(
            changeset,
            sources,
        ),
        publication_boundary=_review_brief_publication_boundary_section(changeset),
        risks=_review_brief_risk_section(changeset, inventory),
        non_claims=[
            "review brief is a deterministic lifecycle summary, not proof",
            "raw command output is not included",
            "raw manual evidence, screenshots, and browser traces are not included",
            "raw diffs and file contents are not included",
            "review feedback response does not imply reviewer acceptance",
            "manual evidence is advisory unless retained verification supports it",
            "handoff posture is advisory and does not mean publication occurred",
            "commit, push, PR, and merge remain explicit operator actions",
        ],
        reviewer_checklist=_reviewer_checklist(changeset, verification_plan),
        safe_inspection_commands=_review_brief_safe_commands(
            changeset,
            verification_plan,
        ),
        limitations=limitations,
    )


def _review_brief_change_summary(
    changeset: ChangesetRecord,
) -> ReviewBriefSection:
    summary = changeset.summary or "No operator-written changeset summary is attached."
    body = (
        f"{summary} Status is {changeset.status}. Risk is "
        f"{changeset.risk_level.value} with "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s)."
    )
    return ReviewBriefSection(
        title="Change Summary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="changeset",
                identifier=str(changeset.changeset_id),
                summary="changeset projection supplied objective, summary, and risk",
            )
        ],
    )


def _review_brief_inventory_section(
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
) -> ReviewBriefSection:
    if inventory_record is None:
        return ReviewBriefSection(
            title="Changed-File Inventory",
            body="No structured change inventory is attached yet.",
        )
    if inventory is None:
        body = (
            f"Inventory artifact {inventory_record.artifact_id} is projected with "
            f"{inventory_record.changed_path_count} changed path(s), but the "
            "artifact could not be loaded for path details."
        )
    else:
        paths = ", ".join(entry.path for entry in inventory.paths[:10])
        if len(inventory.paths) > 10:
            paths = f"{paths}, and {len(inventory.paths) - 10} more"
        body = (
            f"Inventory records {inventory.summary.changed_path_count} changed "
            f"path(s), {inventory.summary.test_path_count} test path(s), "
            f"{inventory.summary.docs_path_count} docs path(s), and "
            f"{inventory.summary.policy_sensitive_path_count} policy-sensitive "
            f"path(s). Freshness is {inventory_status.freshness.value}."
        )
        if paths:
            body = f"{body} Included paths: {paths}."
    if inventory_status.reason is not None:
        body = f"{body} Freshness note: {inventory_status.reason}."
    return ReviewBriefSection(
        title="Changed-File Inventory",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="inventory",
                identifier=str(inventory_record.artifact_id),
                artifact_id=inventory_record.artifact_id,
                summary=(
                    f"latest inventory has {inventory_record.changed_path_count} "
                    f"path(s) and freshness {inventory_status.freshness.value}"
                ),
                local_only=True,
            )
        ],
    )


def _review_brief_provenance_section(
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    source_summary = "; ".join(
        f"{source.source_kind.value}: {source.reason}" for source in sources[:8]
    )
    if not source_summary:
        source_summary = "No changeset source records are attached."
    provenance_body = source_summary
    if inventory is not None:
        provenance_body = (
            f"{provenance_body} Path provenance counts: "
            f"{inventory.summary.provenance_direct_path_count} direct, "
            f"{inventory.summary.provenance_inferred_path_count} inferred, "
            f"{inventory.summary.provenance_unknown_path_count} unknown."
        )
    return ReviewBriefSection(
        title="Provenance",
        body=provenance_body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=f"source-sequence-{source.last_sequence}",
                summary=f"{source.source_kind.value}: {source.reason}",
                artifact_id=source.artifact_id,
                local_only=source.artifact_id is not None,
            )
            for source in sources[:8]
        ],
    )


def _review_brief_topology_section(
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection | None:
    impacts = verification_plan.topology_impacts
    if not impacts:
        return None
    lines = []
    refs = []
    for impact in impacts[:8]:
        owners = (
            f"; owners {', '.join(impact.ownership_hints)}"
            if impact.ownership_hints
            else ""
        )
        tests = f"; tests {', '.join(impact.test_roots)}" if impact.test_roots else ""
        deps = (
            f"; dependencies {', '.join(impact.dependency_hints[:4])}"
            if impact.dependency_hints
            else ""
        )
        lines.append(
            f"{impact.name} ({impact.kind}, {impact.root_path}) matched "
            f"{len(impact.matched_paths)} path(s); topology is "
            f"{impact.topology_freshness}{owners}{tests}{deps}."
        )
        refs.append(
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=impact.component_id,
                summary=(
                    f"{impact.name} matched {len(impact.matched_paths)} "
                    f"path(s) with {impact.recommendation_posture} topology posture"
                ),
            )
        )
    body = " ".join(lines)
    return ReviewBriefSection(
        title="Affected Subsystems",
        body=body,
        evidence_refs=refs,
    )


def _review_brief_lifecycle_section(
    changeset: ChangesetRecord,
    response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    review_loop = verification_plan.review_loop_summary
    body = (
        f"Lifecycle summary for changeset {changeset.changeset_id}: "
        f"{response_summary.total_feedback_count} feedback item(s), "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale response(s), "
        f"{response_summary.accepted_risk_count} accepted-risk response(s), "
        f"{len(manual_evidence)} manual evidence item(s), and verification "
        f"readiness {verification_plan.readiness.state.value}. "
        "The lifecycle brief summarizes retained local evidence and does not "
        "claim reviewer approval or publication."
    )
    return ReviewBriefSection(
        title="Lifecycle Summary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="readiness",
                identifier=f"review-loop-{changeset.changeset_id}",
                summary=(
                    f"verification preview has "
                    f"{review_loop.open_feedback_count} open feedback item(s), "
                    f"{review_loop.stale_response_count} stale response(s), and "
                    f"{review_loop.manual_evidence_count} manual evidence item(s)"
                ),
            )
        ],
    )


def _review_brief_feedback_section(
    feedback: list[ReviewFeedbackRecord],
) -> ReviewBriefSection | None:
    if not feedback:
        return None
    disposition_counts = _value_counts(item.disposition.value for item in feedback)
    kind_counts = _value_counts(item.feedback_kind.value for item in feedback)
    body = (
        f"Review feedback includes {len(feedback)} item(s). "
        f"Disposition counts: {_format_counts(disposition_counts)}. "
        f"Kind counts: {_format_counts(kind_counts)}. "
        "Unresolved feedback remains visible even when verification is passing."
    )
    return ReviewBriefSection(
        title="Review Feedback",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="feedback",
                identifier=str(item.feedback_id),
                artifact_id=item.artifact_id,
                verification_id=item.verification_id,
                summary=(
                    f"{item.feedback_kind.value}/{item.disposition.value}: "
                    f"{item.summary}"
                ),
                local_only=item.artifact_id is not None,
            )
            for item in feedback[:8]
        ],
    )


def _review_brief_response_section(
    response_summary: ChangesetReviewResponseSummary,
) -> ReviewBriefSection | None:
    if response_summary.total_feedback_count == 0:
        return None
    body = (
        f"Response posture covers {response_summary.total_feedback_count} feedback "
        f"item(s): {response_summary.responded_count} responded, "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale, "
        f"{response_summary.blocked_count} blocked, and "
        f"{response_summary.accepted_risk_count} accepted with risk. "
        "Response state is local evidence and does not imply reviewer acceptance."
    )
    return ReviewBriefSection(
        title="Review Responses",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="response",
                identifier=str(item.feedback_id),
                artifact_id=item.latest_fixup_inventory_artifact_id,
                summary=(
                    f"{item.response_state.value}: {item.summary}; "
                    f"{item.changed_path_count} fixup path(s), verification "
                    f"{item.verification_state.value}"
                ),
                local_only=item.latest_fixup_inventory_artifact_id is not None,
            )
            for item in response_summary.items[:8]
        ],
    )


def _review_brief_manual_evidence_section(
    manual_evidence: list[ManualEvidenceRecord],
) -> ReviewBriefSection | None:
    if not manual_evidence:
        return None
    kind_counts = _value_counts(item.evidence_kind.value for item in manual_evidence)
    state_counts = _value_counts(item.state.value for item in manual_evidence)
    local_only_count = sum(1 for item in manual_evidence if item.local_only)
    body = (
        f"Manual evidence includes {len(manual_evidence)} item(s), "
        f"{local_only_count} local-only. Kind counts: "
        f"{_format_counts(kind_counts)}. State counts: {_format_counts(state_counts)}. "
        "Manual evidence remains advisory and is not retained command evidence."
    )
    return ReviewBriefSection(
        title="Manual Evidence",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind=_manual_evidence_ref_kind(item),
                identifier=str(item.evidence_id),
                artifact_id=item.artifact_id,
                verification_id=item.verification_id,
                summary=(
                    f"{item.evidence_kind.value}/{item.state.value}: {item.summary}"
                ),
                local_only=item.local_only,
            )
            for item in manual_evidence[:8]
        ],
    )


def _review_brief_live_evidence_section(
    manual_evidence: list[ManualEvidenceRecord],
) -> ReviewBriefSection | None:
    live_evidence = [
        item
        for item in manual_evidence
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
            ManualEvidenceKind.ACCESSIBILITY_NOTE,
        }
    ]
    if not live_evidence:
        return None
    kind_counts = _value_counts(item.evidence_kind.value for item in live_evidence)
    body = (
        f"Live review evidence includes {len(live_evidence)} browser, dashboard, "
        f"screenshot, or accessibility item(s). Kind counts: "
        f"{_format_counts(kind_counts)}. These observations are advisory unless a "
        "deterministic fixture-backed gate separately promotes them."
    )
    return ReviewBriefSection(
        title="Live Review Evidence",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind=_manual_evidence_ref_kind(item),
                identifier=str(item.evidence_id),
                artifact_id=item.artifact_id,
                summary=f"{item.evidence_kind.value}: {item.summary}",
                local_only=item.local_only,
            )
            for item in live_evidence[:8]
        ],
    )


def _review_brief_verification_section(
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    readiness = verification_plan.readiness
    body = (
        f"Readiness is {readiness.state.value}: {readiness.summary}. "
        f"Counts are {readiness.failed_count} failed, {readiness.stale_count} stale, "
        f"{readiness.missing_count} missing, and "
        f"{readiness.accepted_risk_count} accepted risk."
    )
    if verification_posture is None:
        body = f"{body} No retained changeset verification posture is attached yet."
    else:
        body = (
            f"{body} Latest retained posture is "
            f"{verification_posture.state.value}: {verification_posture.summary}."
        )
    refs = []
    if verification_posture is not None:
        refs.append(
            ReviewBriefEvidenceRef(
                kind="verification",
                identifier=str(
                    verification_posture.verification_id
                    or verification_posture.last_sequence
                ),
                verification_id=verification_posture.verification_id,
                artifact_id=verification_posture.artifact_id,
                summary=verification_posture.summary,
                local_only=verification_posture.artifact_id is not None,
            )
        )
    refs.extend(
        ReviewBriefEvidenceRef(
            kind="verification",
            identifier=requirement.requirement_id,
            verification_id=requirement.verification_id,
            artifact_id=requirement.artifact_id,
            summary=f"{requirement.state.value}: {requirement.reason}",
            local_only=requirement.artifact_id is not None,
        )
        for requirement in readiness.requirements[:8]
    )
    return ReviewBriefSection(title="Verification", body=body, evidence_refs=refs)


def _review_brief_stale_verification_section(
    response_summary: ChangesetReviewResponseSummary,
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection | None:
    stale_responses = [
        item
        for item in response_summary.items
        if item.stale or item.verification_state == ChangesetVerificationState.STALE
    ]
    if (
        not stale_responses
        and verification_plan.readiness.state != ChangesetVerificationState.STALE
    ):
        return None
    body = (
        f"Stale verification posture includes {len(stale_responses)} stale "
        f"response-linked item(s) and changeset readiness "
        f"{verification_plan.readiness.state.value}: "
        f"{verification_plan.readiness.summary}. Rerun focused checks before "
        "handoff when response-linked fixups changed after retained passes."
    )
    return ReviewBriefSection(
        title="Stale Verification",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="verification",
                identifier=str(item.feedback_id),
                artifact_id=item.latest_fixup_inventory_artifact_id,
                summary=(
                    f"{item.response_state.value}: "
                    f"{item.verification_reason or item.stale_reason or item.summary}"
                ),
                local_only=item.latest_fixup_inventory_artifact_id is not None,
            )
            for item in stale_responses[:8]
        ],
    )


def _review_brief_command_evidence_section(
    command_evidence: ChangesetCommandEvidenceSummary,
) -> ReviewBriefSection:
    if command_evidence.total_count == 0:
        body = "No retained command evidence matched this changeset."
    else:
        body = (
            f"Command evidence includes {command_evidence.total_count} retained "
            f"attempt(s): {command_evidence.verification_count} verification, "
            f"{command_evidence.failed_count} failed, "
            f"{command_evidence.risky_count} publish/deploy/destructive-risk, "
            f"{command_evidence.environment_captured_count} with redacted "
            "environment posture, and "
            f"{command_evidence.artifact_count} with output artifact references."
        )
    refs = [
        ReviewBriefEvidenceRef(
            kind="command",
            identifier=item.tool_attempt_id,
            artifact_id=item.output_artifact_id,
            summary=(
                f"{item.purpose}/{item.status}: {item.summary}; "
                f"environment captured {item.environment_captured}"
            ),
            local_only=item.local_only,
        )
        for item in command_evidence.items[:8]
    ]
    return ReviewBriefSection(title="Command Evidence", body=body, evidence_refs=refs)


def _review_brief_publication_boundary_section(
    changeset: ChangesetRecord,
) -> ReviewBriefSection:
    body = (
        "Publication boundary posture is advisory in this lifecycle brief. "
        "Glassbox generated local evidence only; it did not stage, commit, push, "
        "open a pull request, merge, deploy, or publish. Final handoff and "
        "publication require explicit operator action."
    )
    return ReviewBriefSection(
        title="Publication Boundary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="publication_boundary",
                identifier=str(changeset.changeset_id),
                summary=(
                    "local lifecycle brief records non-publication posture for "
                    "this changeset"
                ),
            )
        ],
    )


def _review_brief_branch_candidate_section(
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
) -> ReviewBriefSection | None:
    if changeset.branch_search_id is None and changeset.branch_candidate_id is None:
        return None
    candidate_sources = [
        source
        for source in sources
        if source.source_kind == ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE
    ]
    body = (
        f"Branch search {changeset.branch_search_id} selected candidate "
        f"{changeset.branch_candidate_id}. No workspace mutation is claimed by "
        "this review brief."
    )
    return ReviewBriefSection(
        title="Branch-Candidate Rationale",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="branch_candidate",
                identifier=str(source.branch_candidate_id or source.last_sequence),
                artifact_id=source.artifact_id,
                summary=source.reason,
                local_only=source.artifact_id is not None,
            )
            for source in candidate_sources
        ],
    )


def _review_brief_risk_section(
    changeset: ChangesetRecord,
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    body = (
        f"Changeset risk is {changeset.risk_level.value}. "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s) are projected."
    )
    if changeset.risk_summary is not None:
        body = f"{body} Summary: {changeset.risk_summary}."
    if inventory is not None:
        body = (
            f"{body} Inventory risk counts: "
            f"{inventory.summary.high_risk_path_count} high, "
            f"{inventory.summary.medium_risk_path_count} medium, "
            f"{inventory.summary.low_risk_path_count} low."
        )
    return ReviewBriefSection(
        title="Risks",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="risk",
                identifier=str(changeset.changeset_id),
                summary=body,
            )
        ],
    )


def _reviewer_checklist(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    checklist = [
        "Inspect the changed-file inventory before reviewing implementation details",
        "Review provenance confidence for changed paths with unknown source evidence",
        "Inspect verification readiness and retained evidence references",
    ]
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        checklist.append("Resolve missing, stale, failed, or accepted-risk checks")
    if changeset.unresolved_risk_count > 0:
        checklist.append("Review unresolved risk classification before commit prep")
    return checklist


def _review_brief_safe_commands(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    commands = [
        f"glassbox changeset show {changeset.changeset_id} --cwd .",
        f"glassbox changeset verification-plan {changeset.changeset_id} --cwd .",
        f"glassbox changeset brief {changeset.changeset_id} --cwd . --json",
    ]
    commands.extend(verification_plan.safe_next_actions)
    return list(dict.fromkeys(commands))


def _manual_evidence_ref_kind(
    evidence: ManualEvidenceRecord,
) -> Literal[
    "manual_evidence",
    "browser_evidence",
    "dashboard_evidence",
    "accessibility_evidence",
]:
    if evidence.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE:
        return "accessibility_evidence"
    if evidence.evidence_kind == ManualEvidenceKind.BROWSER_OBSERVATION:
        summary = evidence.summary.lower()
        return "dashboard_evidence" if "dashboard" in summary else "browser_evidence"
    if evidence.evidence_kind == ManualEvidenceKind.SCREENSHOT:
        return "browser_evidence"
    return "manual_evidence"


def _value_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key} {value}" for key, value in sorted(counts.items()))


def _review_brief_local_only(
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    verification_posture: ChangesetVerificationPostureRecord | None,
    command_evidence: ChangesetCommandEvidenceSummary,
    manual_evidence: list[ManualEvidenceRecord],
) -> bool:
    return (
        inventory_record is not None
        or verification_posture is not None
        or command_evidence.environment_captured_count > 0
        or command_evidence.artifact_count > 0
        or any(item.local_only for item in manual_evidence)
        or any(source.artifact_id is not None for source in sources)
    )


def _review_brief_limitations(
    *,
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    inventory_limitations: list[str],
    verification_plan: ChangesetVerificationPlanPreview,
    command_evidence: ChangesetCommandEvidenceSummary,
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
) -> list[str]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    limitations.extend(inventory_limitations)
    if inventory_status.reason is not None:
        limitations.append(inventory_status.reason)
    if inventory is not None:
        limitations.extend(inventory.limitations)
    limitations.extend(verification_plan.limitations)
    limitations.extend(command_evidence.limitations)
    limitations.extend(review_response_summary.blockers)
    for evidence in manual_evidence:
        limitations.extend(evidence.limitations)
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        limitations.append(
            f"verification readiness is {verification_plan.readiness.state.value}"
        )
    if review_response_summary.unresolved_count > 0:
        limitations.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
    if review_response_summary.stale_response_count > 0:
        limitations.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
    return list(dict.fromkeys(limitations))


def _review_readiness_state(
    *,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    changeset: ChangesetRecord,
    review_response_summary: ChangesetReviewResponseSummary,
) -> tuple[ChangesetReadinessState, list[str]]:
    blockers: list[str] = []
    if review_response_summary.blockers:
        blockers.extend(review_response_summary.blockers)
    if review_response_summary.stale_response_count > 0:
        blockers.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if review_response_summary.unresolved_count > 0:
        blockers.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
        return ChangesetReadinessState.NEEDS_REVIEW, blockers
    readiness = verification_plan.readiness
    if inventory_status.stale:
        blockers.append(
            inventory_status.reason
            or "structured change inventory is stale against the current workspace"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if inventory_status.freshness == ChangesetInventoryFreshness.UNKNOWN:
        blockers.append(
            inventory_status.reason
            or "structured change inventory freshness is unknown"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state == ChangesetVerificationState.FAILED:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.FAILED_CHECKS, blockers
    if readiness.state == ChangesetVerificationState.STALE:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state in {
        ChangesetVerificationState.MISSING,
        ChangesetVerificationState.PLANNED,
        ChangesetVerificationState.RUNNING,
        ChangesetVerificationState.SKIPPED,
    }:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if readiness.state == ChangesetVerificationState.ACCEPTED_WITH_RISK:
        return ChangesetReadinessState.ACCEPTED_WITH_RISK, [readiness.summary]
    return ChangesetReadinessState.READY, blockers


def _review_readiness_reason(
    state: ChangesetReadinessState,
    blockers: list[str],
) -> str:
    if blockers:
        return "; ".join(blockers)
    if state == ChangesetReadinessState.READY:
        return "deterministic changeset evidence is ready for reviewer inspection"
    return f"review readiness is {state.value}"


__all__ = [
    "ChangesetActionService",
    "ChangesetDetailView",
    "ChangesetDerivationRepository",
    "ChangesetDerivationResult",
    "ChangesetDerivationService",
    "ChangesetInventoryRefreshResult",
    "ChangesetInventoryStatus",
    "ChangesetQueryService",
    "ChangesetRepository",
    "ChangesetReviewBriefGenerationResult",
    "ChangesetReviewBriefService",
    "ChangesetVerificationEvidenceRecordResult",
    "ChangesetVerificationPlanPreview",
    "ChangesetVerificationRecipePreview",
    "ChangesetVerificationService",
    "AccessibilityEvidenceActionService",
    "BrowserEvidenceActionService",
    "ManualEvidenceActionService",
    "ManualEvidenceRecordResult",
    "ReviewFeedbackActionService",
    "ReviewFeedbackFixupInventoryResult",
    "ReviewFeedbackFixupInventoryService",
    "ReviewFeedbackRecordResult",
]
