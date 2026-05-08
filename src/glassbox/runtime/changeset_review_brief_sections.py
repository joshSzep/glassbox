"""Review brief artifact assembly facade."""

from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_branch_candidate_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_change_summary,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_command_evidence_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_inventory_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_provenance_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_risk_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_topology_section,
)
from glassbox.runtime.changeset_review_brief_core_sections import (
    review_brief_verification_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_feedback_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_lifecycle_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_live_evidence_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_manual_evidence_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_publication_boundary_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_response_section,
)
from glassbox.runtime.changeset_review_brief_review_sections import (
    review_brief_stale_verification_section,
)
from glassbox.runtime.changeset_safe_commands import changeset_brief_command
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefLimitationSummary
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary


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
    limitation_summary: ReviewBriefLimitationSummary | None,
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
        change_summary=review_brief_change_summary(changeset),
        changed_file_inventory=review_brief_inventory_section(
            inventory_record,
            inventory,
            inventory_status,
        ),
        affected_subsystems=review_brief_topology_section(verification_plan),
        provenance=review_brief_provenance_section(sources, inventory),
        lifecycle_summary=review_brief_lifecycle_section(
            changeset,
            review_response_summary,
            manual_evidence,
            verification_plan,
        ),
        review_feedback=review_brief_feedback_section(review_feedback),
        review_responses=review_brief_response_section(review_response_summary),
        manual_evidence=review_brief_manual_evidence_section(manual_evidence),
        live_review_evidence=review_brief_live_evidence_section(manual_evidence),
        verification=review_brief_verification_section(
            verification_posture,
            verification_plan,
        ),
        stale_verification=review_brief_stale_verification_section(
            review_response_summary,
            verification_plan,
        ),
        command_evidence=review_brief_command_evidence_section(command_evidence),
        branch_candidate_rationale=review_brief_branch_candidate_section(
            changeset,
            sources,
        ),
        publication_boundary=review_brief_publication_boundary_section(changeset),
        risks=review_brief_risk_section(changeset, inventory),
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
        limitation_summary=limitation_summary,
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
        show_changeset_command(changeset.changeset_id),
        changeset_verification_plan_command(changeset.changeset_id),
        changeset_brief_command(changeset.changeset_id, json=True),
    ]
    commands.extend(verification_plan.safe_next_actions)
    return list(dict.fromkeys(commands))


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
