"""Changeset CLI terminal formatters."""

from glassbox.cli.changeset_command_payloads import _feedback_result_payload
from glassbox.cli.changeset_command_payloads import _fixup_inventory_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.next_action_output import next_action_record_payloads
from glassbox.cli.next_action_output import next_action_records_for_cli
from glassbox.cli.next_action_output import print_next_action_records
from glassbox.core import ChangesetRecord
from glassbox.core import ManualEvidenceRecord
from glassbox.core import NextActionPriority
from glassbox.core import NextActionTargetKind
from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionPreview
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetVerificationPlanDispositionResult
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ManualEvidenceRecordResult
from glassbox.runtime.changesets import PathVerificationPlanPreview
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryResult
from glassbox.runtime.changesets import ReviewFeedbackRecordResult
from glassbox.runtime.commit_messages import CommitMessageSuggestion
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.handoff_readiness import HandoffReadinessAssessment
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus


def _print_changeset_list(changesets: list[ChangesetRecord]) -> None:
    if not changesets:
        print("No changesets found")
        return
    print(f"Changesets: {len(changesets)}")
    for changeset in changesets:
        print(
            f"{changeset.changeset_id}  {changeset.status}  "
            f"risk {changeset.risk_level.value}  "
            f"updated {changeset.updated_at.isoformat()}"
        )
        print(f"  Session: {changeset.session_id}")
        print(f"  Objective: {changeset.objective}")
        if changeset.risk_summary is not None:
            print(f"  Risk: {changeset.risk_summary}")
        if changeset.task_id is not None:
            print(f"  Task: {changeset.task_id}")
        if changeset.branch_search_id is not None:
            print(f"  Branch search: {changeset.branch_search_id}")


def _print_adoption_preview(preview: BranchCandidateAdoptionPreview) -> None:
    print("Branch candidate adoption preview")
    print(f"Branch search: {preview.search_id}")
    print(f"Candidate: {preview.candidate_id}")
    print(f"Selected: {preview.selected}")
    print(f"Strategy: {preview.strategy_label}")
    print(f"Changed files: {preview.changed_files_summary}")
    print(f"Verification: {preview.verification_posture}")
    print(f"Risk: {preview.risk_posture}")
    if preview.worktree is not None:
        print(
            f"Worktree: {preview.worktree.worktree_id} ({preview.worktree.state.value})"
        )
    if preview.conflicts:
        print("Conflicts or cleanup blockers:")
        for conflict in preview.conflicts:
            print(f"  - {conflict}")
    if preview.stale_evidence:
        print("Stale or missing evidence:")
        for item in preview.stale_evidence:
            print(f"  - {item}")
    _print_limitations(preview.limitations)
    print("Safe next actions:")
    for action in preview.safe_next_actions:
        print(f"  - {action}")
    print("Glassbox did not merge, commit, push, or open a PR.")


def _print_changeset_detail(
    detail: ChangesetDetailView,
    *,
    verification_plan: ChangesetVerificationPlanPreview | None = None,
    handoff_readiness: HandoffReadinessAssessment | None = None,
) -> None:
    changeset = detail.changeset
    print(f"Changeset {changeset.changeset_id}")
    print(f"Status: {changeset.status}")
    print(f"Session: {changeset.session_id}")
    print(f"Objective: {changeset.objective}")
    if changeset.summary:
        print(f"Summary: {changeset.summary}")
    print(
        "Risk: "
        f"{changeset.risk_level.value} "
        f"({changeset.unresolved_risk_count} unresolved, "
        f"{changeset.accepted_risk_count} accepted)"
    )
    if changeset.risk_summary is not None:
        print(f"Risk summary: {changeset.risk_summary}")
    print(f"Sources: {len(detail.sources)}")
    for source in detail.sources:
        print(f"  {source.source_kind.value}: {source.reason}")
        if source.limitation:
            print(f"    Limitation: {source.limitation}")
    if detail.inventory is None:
        print("Inventory: none attached yet")
    else:
        print(
            "Inventory: "
            f"{detail.inventory.changed_path_count} paths "
            f"[{detail.inventory.freshness.value}]"
        )
        if detail.inventory.previous_artifact_id is not None:
            print(f"  Previous artifact: {detail.inventory.previous_artifact_id}")
    if detail.inventory_status.reason is not None:
        print(
            "Inventory freshness: "
            f"{detail.inventory_status.freshness.value} - "
            f"{detail.inventory_status.reason}"
        )
    elif detail.inventory_status.current_source_digest is not None:
        print(f"Inventory freshness: {detail.inventory_status.freshness.value}")
    if detail.verification_posture is None:
        print("Verification posture: none attached yet")
    else:
        posture = detail.verification_posture
        print(f"Verification posture: {posture.state.value} - {posture.summary}")
    if verification_plan is not None:
        readiness = verification_plan.readiness
        print(f"Verification readiness: {readiness.state.value} - {readiness.summary}")
        print(
            "Verification counts: "
            f"{readiness.failed_count} failed, "
            f"{readiness.stale_count} stale, "
            f"{readiness.missing_count} missing, "
            f"{readiness.accepted_risk_count} accepted risk"
        )
        for requirement in readiness.requirements[:5]:
            print(
                f"  {requirement.state.value}: {requirement.check_name} - "
                f"{requirement.reason}"
            )
        if verification_plan.recommended_targets:
            print("Recommended verification targets:")
            for target in verification_plan.recommended_targets[:5]:
                print(
                    f"  {target.target_kind}/{target.confidence}: "
                    f"{target.title} ({target.target_id})"
                )
        if verification_plan.stale_evidence:
            print("Stale verification guidance:")
            for target in verification_plan.stale_evidence[:5]:
                guidance = target.limitations[0] if target.limitations else target.title
                print(f"  {target.title}: {guidance}")
    command_evidence = detail.command_evidence
    print(
        "Command evidence: "
        f"{command_evidence.total_count} attempts "
        f"({command_evidence.verification_count} verification, "
        f"{command_evidence.failed_count} failed, "
        f"{command_evidence.risky_count} risky)"
    )
    for item in command_evidence.items[:5]:
        print(
            f"  {item.purpose}/{item.status}: {item.summary} "
            f"(attempt {item.tool_attempt_id[:8]})"
        )
    print(f"Review briefs: {len(detail.review_briefs)}")
    print(f"Manual evidence: {len(detail.manual_evidence)}")
    for item in detail.manual_evidence[:5]:
        print(
            f"  {item.evidence_kind.value}/{item.state.value}: "
            f"{item.summary} ({item.evidence_id})"
        )
    print(f"Review feedback: {len(detail.review_feedback)}")
    response_summary = detail.review_response_summary
    print(
        "Review responses: "
        f"{response_summary.responded_count} responded, "
        f"{response_summary.unresolved_count} unresolved, "
        f"{response_summary.stale_response_count} stale, "
        f"{response_summary.accepted_risk_count} accepted risk"
    )
    if response_summary.blockers:
        print("Response blockers:")
        for blocker in response_summary.blockers[:5]:
            print(f"  - {blocker}")
    for item in detail.review_feedback[:5]:
        print(
            f"  {item.feedback_kind.value}/{item.disposition.value}: "
            f"{item.summary} ({item.feedback_id})"
        )
    print(f"Readiness decisions: {len(detail.readiness)}")
    if handoff_readiness is not None:
        print(
            f"Handoff readiness: {handoff_readiness.state} - {handoff_readiness.reason}"
        )
        if handoff_readiness.blockers:
            print("Handoff blockers:")
            for blocker in handoff_readiness.blockers[:5]:
                print(f"  - {blocker}")
        if handoff_readiness.limitations:
            print("Handoff limitations:")
            for limitation in handoff_readiness.limitations[:5]:
                print(f"  - {limitation}")
    _print_limitations(detail.limitations)
    print("Safe next actions:")
    for action in detail.safe_next_actions:
        print(f"  - {action}")
    print_next_action_records(changeset_next_action_records(detail))


def changeset_next_action_records(detail: ChangesetDetailView):
    return next_action_records_for_cli(
        detail.safe_next_actions,
        target_kind=NextActionTargetKind.CHANGESET,
        target_id=str(detail.changeset.changeset_id),
        purpose=(
            "Inspect changeset readiness, evidence, and verification before handoff."
        ),
        evidence_summary=(
            "Changeset detail combines local inventory, verification, review, "
            "and handoff evidence."
        ),
        priority=(
            NextActionPriority.ACTION_NEEDED
            if detail.changeset.unresolved_risk_count
            or detail.review_response_summary.blockers
            else NextActionPriority.RECOMMENDED
        ),
        limitations=[
            "Safe next actions are advisory and do not publish or mutate review state."
        ],
    )


def changeset_next_action_record_payloads(detail: ChangesetDetailView) -> list[dict]:
    return next_action_record_payloads(changeset_next_action_records(detail))


def _print_verification_plan(preview: ChangesetVerificationPlanPreview) -> None:
    print(f"Verification plan for changeset {preview.changeset_id}")
    print(f"Inventory: {preview.inventory_freshness.value}")
    print(f"Readiness: {preview.readiness.state.value} - {preview.readiness.summary}")
    if preview.changed_paths:
        print("Expected scope:")
        for path in preview.changed_paths[:20]:
            print(f"  - {path}")
    _print_plan_entries(preview.plan_entries)
    _print_skipped_checks(preview.skipped_checks)
    if preview.recommended_commands:
        print("Recommended commands:")
        for command in preview.recommended_commands:
            print(f"  - {command}")
    if preview.eval_profiles:
        print("Eval profiles:")
        for profile_id in preview.eval_profiles:
            print(f"  - {profile_id}")
    if preview.recipes:
        print("Recipes:")
        for recipe in preview.recipes:
            print(f"  - {recipe.title} ({recipe.recipe_id})")
            for command in recipe.commands:
                print(f"    command: {command}")
    if preview.recommended_targets:
        print("Recommended verification targets:")
        for target in preview.recommended_targets:
            print(
                f"  - {target.target_kind}/{target.confidence}: "
                f"{target.title} ({target.target_id})"
            )
            if target.command:
                print(f"    command: {target.command}")
            if target.limitations:
                print(f"    limitation: {target.limitations[0]}")
    if preview.release_surfaces:
        print("Release surfaces:")
        for surface in preview.release_surfaces:
            print(f"  - {surface.title} ({surface.confidence})")
    if preview.stale_evidence:
        print("Stale evidence:")
        for target in preview.stale_evidence:
            guidance = target.limitations[0] if target.limitations else target.title
            print(f"  - {target.title}: {guidance}")
    if preview.retained_artifact_ids:
        print("Retained verification artifacts:")
        for artifact_id in preview.retained_artifact_ids:
            print(f"  - {artifact_id}")
    _print_limitations(preview.limitations)
    print("Safe next actions:")
    for action in preview.safe_next_actions:
        print(f"  - {action}")


def _print_path_verification_plan(preview: PathVerificationPlanPreview) -> None:
    print("Verification plan for changed paths")
    print(f"Workspace: {preview.workspace_root}")
    if preview.changed_paths:
        print("Expected scope:")
        for path in preview.changed_paths[:20]:
            print(f"  - {path}")
    _print_plan_entries(preview.plan_entries)
    _print_skipped_checks(preview.skipped_checks)
    if preview.recommended_commands:
        print("Recommended commands:")
        for command in preview.recommended_commands:
            print(f"  - {command}")
    if preview.recipes:
        print("Recipes:")
        for recipe in preview.recipes:
            print(f"  - {recipe.title} ({recipe.recipe_id})")
    _print_limitations(preview.limitations)
    print("Safe next actions:")
    for action in preview.safe_next_actions:
        print(f"  - {action}")


def _print_verification_disposition(
    result: ChangesetVerificationPlanDispositionResult,
    *,
    as_json: bool,
) -> int:
    if as_json:
        print_json_output(result.model_dump(mode="json"))
        return 0
    print(f"Recorded verification plan decision: {result.action}")
    print(f"Changeset: {result.changeset_id}")
    print(f"Verification: {result.verification_id}")
    if result.replacement_verification_id is not None:
        print(f"Replacement: {result.replacement_verification_id}")
    print(f"Entry: {result.entry.check_name}")
    print(f"Events: {len(result.events)}")
    print("Safe next actions:")
    for action in result.safe_next_actions:
        print(f"  - {action}")
    print("Non-claims:")
    for non_claim in result.non_claims:
        print(f"  - {non_claim}")
    return 0


def _print_plan_entries(entries) -> None:
    if not entries:
        return
    print("Plan entries:")
    for entry in entries:
        print(
            f"  - {entry.lifecycle_state.value}/{entry.kind.value}: {entry.check_name}"
        )
        if entry.command:
            print(f"    command: {' '.join(entry.command)}")
        if entry.selection_rationale:
            print(f"    why: {entry.selection_rationale}")
        if entry.stale_reasons:
            print(f"    stale: {entry.stale_reasons[0]}")


def _print_skipped_checks(skipped_checks) -> None:
    if not skipped_checks:
        return
    print("Skipped checks:")
    for skipped in skipped_checks:
        print(f"  - {skipped.target_kind}/{skipped.target_id}: {skipped.explanation}")


def _print_commit_message_suggestion(
    suggestion: CommitMessageSuggestion,
) -> None:
    print("Commit message suggestion (not committed):")
    print(suggestion.message)
    if suggestion.limitations:
        _print_limitations(suggestion.limitations)
    print("Non-claims:")
    for non_claim in suggestion.non_claims:
        print(f"  - {non_claim}")


def _print_commit_prep(
    readiness: CommitReadinessAssessment,
    suggestion: CommitMessageSuggestion,
    handoff_readiness: HandoffReadinessAssessment,
) -> None:
    print("Commit preparation (read-only):")
    print(f"Readiness: {readiness.state.value} - {readiness.reason}")
    print(
        "Review loop: "
        f"{readiness.review_feedback_count} feedback, "
        f"{readiness.unresolved_feedback_count} unresolved, "
        f"{readiness.stale_response_count} stale responses"
    )
    print(
        "Manual evidence: "
        f"{readiness.manual_evidence_count} attached, "
        f"{readiness.local_only_evidence_count} local-only"
    )
    print(f"Handoff readiness: {handoff_readiness.state} - {handoff_readiness.reason}")
    if readiness.blockers:
        print("Blockers:")
        for blocker in readiness.blockers:
            print(f"  - {blocker}")
    print("Suggested message:")
    print(suggestion.message)
    risky_paths = list(
        dict.fromkeys(
            readiness.git.policy_sensitive_paths
            + readiness.git.generated_paths
            + readiness.git.untracked_paths
            + readiness.git.unstaged_paths
        )
    )
    if risky_paths:
        print("Risky or ambiguous paths:")
        for path in risky_paths[:20]:
            print(f"  - {path}")
    if readiness.safe_next_actions:
        print("Safe next commands:")
        for action in readiness.safe_next_actions:
            print(f"  - {action}")
    print("Glassbox did not stage, commit, push, or open a PR.")


def _print_handoff_readiness(readiness: HandoffReadinessAssessment) -> None:
    print("Handoff readiness (read-only):")
    print(f"Changeset: {readiness.changeset_id}")
    print(f"State: {readiness.state}")
    print(f"Reason: {readiness.reason}")
    print(f"Commit readiness: {readiness.commit_readiness_state.value}")
    print(
        "Evidence: "
        f"{readiness.evidence.feedback_count} feedback, "
        f"{readiness.evidence.unresolved_feedback_count} unresolved, "
        f"{readiness.evidence.manual_evidence_count} manual evidence, "
        f"{readiness.evidence.review_brief_count} lifecycle briefs, "
        f"{readiness.evidence.accepted_risk_count} accepted risk"
    )
    if readiness.blockers:
        print("Blockers:")
        for blocker in readiness.blockers:
            print(f"  - {blocker}")
    if readiness.limitations:
        print("Limitations:")
        for limitation in readiness.limitations:
            print(f"  - {limitation}")
    if readiness.safe_next_actions:
        print("Safe next commands:")
        for action in readiness.safe_next_actions:
            print(f"  - {action}")
        print_next_action_records(handoff_next_action_records(readiness))
    print("Non-claims:")
    for non_claim in readiness.non_claims:
        print(f"  - {non_claim}")


def handoff_next_action_records(readiness: HandoffReadinessAssessment):
    return next_action_records_for_cli(
        readiness.safe_next_actions,
        target_kind=NextActionTargetKind.CHANGESET,
        target_id=str(readiness.changeset_id),
        purpose=(
            "Inspect handoff blockers and evidence before exporting review materials."
        ),
        evidence_summary=(
            "Handoff readiness is derived from local review, evidence, and risk "
            "posture."
        ),
        priority=(
            NextActionPriority.ACTION_NEEDED
            if readiness.blockers
            else NextActionPriority.RECOMMENDED
        ),
        limitations=[
            "Readiness preview does not stage, commit, push, open a PR, or merge."
        ],
    )


def handoff_next_action_record_payloads(
    readiness: HandoffReadinessAssessment,
) -> list[dict]:
    return next_action_record_payloads(handoff_next_action_records(readiness))


def _print_limitations(limitations: list[str]) -> None:
    if not limitations:
        return
    print("Limitations:")
    for limitation in limitations:
        print(f"  - {limitation}")


def _print_feedback_list(feedback: list[ReviewFeedbackRecord]) -> None:
    if not feedback:
        print("No review feedback found")
        return
    print(f"Review feedback: {len(feedback)}")
    for item in feedback:
        print(
            f"{item.feedback_id}  {item.feedback_kind.value}  "
            f"{item.disposition.value}  updated {item.updated_at.isoformat()}"
        )
        print(f"  Changeset: {item.changeset_id}")
        print(f"  Summary: {item.summary}")
        if item.reviewer_label is not None:
            print(f"  Reviewer label: {item.reviewer_label}")


def _print_manual_evidence_list(evidence: list[ManualEvidenceRecord]) -> None:
    if not evidence:
        print("No manual evidence found")
        return
    print(f"Manual evidence: {len(evidence)}")
    for item in evidence:
        print(
            f"{item.evidence_id}  {item.evidence_kind.value}  "
            f"{item.state.value}  updated {item.updated_at.isoformat()}"
        )
        if item.changeset_id is not None:
            print(f"  Changeset: {item.changeset_id}")
        print(f"  Target: {item.target_kind.value} {item.target_id}")
        print(f"  Source: {item.source_label}")
        print(f"  Summary: {item.summary}")
        print("  Manual provenance: not retained command evidence")


def _print_manual_evidence_result(
    result: ManualEvidenceRecordResult,
    as_json: bool,
) -> int:
    payload = {
        "evidence": result.evidence.model_dump(mode="json"),
        "artifact_id": (
            str(result.artifact.artifact_id) if result.artifact is not None else None
        ),
        "artifact_path": (
            result.artifact.relative_path.as_posix()
            if result.artifact is not None
            else None
        ),
        "event_sequence": result.event.sequence,
        "safe_next_actions": result.safe_next_actions,
        "non_claims": result.non_claims,
    }
    if as_json:
        print_json_output(payload)
    else:
        evidence = result.evidence
        print(f"Manual evidence {evidence.state.value}: {evidence.evidence_id}")
        print(f"Changeset: {evidence.changeset_id}")
        print(f"Kind: {evidence.evidence_kind.value}")
        print(f"Target: {evidence.target_kind.value} {evidence.target_id}")
        print(f"Source: {evidence.source_label}")
        print(f"Summary: {evidence.summary}")
        print("Manual provenance: not retained command evidence")
        if result.artifact is not None:
            print(f"Artifact: {result.artifact.relative_path.as_posix()}")
        print("Safe next actions:")
        for action in result.safe_next_actions:
            print(f"  - {action}")
        print("Non-claims:")
        for non_claim in result.non_claims:
            print(f"  - {non_claim}")
    return 0


def _print_feedback_detail(
    feedback: ReviewFeedbackRecord,
    scopes,
    *,
    response_status: ReviewFeedbackResponseStatus,
) -> None:
    print(f"Review feedback {feedback.feedback_id}")
    print(f"Changeset: {feedback.changeset_id}")
    print(f"Kind: {feedback.feedback_kind.value}")
    print(f"Disposition: {feedback.disposition.value}")
    print(f"Provenance: {feedback.provenance.value}")
    print(f"Summary: {feedback.summary}")
    if feedback.body is not None:
        print(f"Body: {feedback.body}")
    if feedback.resolution_summary is not None:
        print(f"Resolution: {feedback.resolution_summary}")
    if feedback.residual_risk is not None:
        print(f"Residual risk: {feedback.residual_risk}")
    if feedback.risk_summary is not None:
        print(f"Accepted risk: {feedback.risk_summary}")
    if feedback.acceptance_reason is not None:
        print(f"Acceptance reason: {feedback.acceptance_reason}")
    if feedback.archived_reason is not None:
        print(f"Archived reason: {feedback.archived_reason}")
    print(f"Scopes: {len(scopes)}")
    for scope in scopes:
        print(f"  {scope.scope_kind.value}: {scope.reason}")
        if scope.file_path is not None:
            suffix = ""
            if scope.line_start is not None:
                suffix = f":{scope.line_start}"
                if scope.line_end is not None and scope.line_end != scope.line_start:
                    suffix += f"-{scope.line_end}"
            print(f"    File: {scope.file_path}{suffix}")
    print("Response status:")
    print(f"  State: {response_status.response_state.value}")
    print(
        "  Fixup inventory: "
        f"{response_status.fixup_inventory_count} records, "
        f"{response_status.changed_path_count} changed paths, "
        f"{response_status.matched_scope_path_count} scoped matches"
    )
    if response_status.latest_fixup_inventory_artifact_id is not None:
        print(
            f"  Latest artifact: {response_status.latest_fixup_inventory_artifact_id}"
        )
    if response_status.stale_reason is not None:
        print(
            f"  Freshness: {response_status.inventory_freshness.value} - "
            f"{response_status.stale_reason}"
        )
    else:
        print(f"  Freshness: {response_status.inventory_freshness.value}")
    if response_status.path_summaries:
        print("  Response paths:")
        for summary in response_status.path_summaries[:5]:
            print(f"    - {summary}")
    if response_status.blockers:
        print("  Blockers:")
        for blocker in response_status.blockers:
            print(f"    - {blocker}")
    print("Safe next actions:")
    for action in response_status.safe_next_actions:
        print(f"  - {action}")
    print("Non-claims:")
    for non_claim in response_status.non_claims:
        print(f"  - {non_claim}")


def _print_review_response_summary(
    summary: ChangesetReviewResponseSummary,
) -> None:
    print(f"Review response status for changeset {summary.changeset_id}")
    print(
        f"Feedback: {summary.total_feedback_count} total, "
        f"{summary.open_count} open, "
        f"{summary.responded_count} responded, "
        f"{summary.unresolved_count} unresolved, "
        f"{summary.stale_response_count} stale, "
        f"{summary.accepted_risk_count} accepted risk"
    )
    if summary.items:
        for item in summary.items:
            print(
                f"{item.feedback_id}  {item.response_state.value}  "
                f"{item.disposition.value}  {item.summary}"
            )
            print(
                "  Fixup: "
                f"{item.fixup_inventory_count} records, "
                f"{item.changed_path_count} paths, "
                f"{item.matched_scope_path_count} scoped matches"
            )
            if item.stale_reason is not None:
                print(
                    "  Freshness: "
                    f"{item.inventory_freshness.value} - {item.stale_reason}"
                )
            if item.blockers:
                print("  Blockers:")
                for blocker in item.blockers:
                    print(f"    - {blocker}")
    else:
        print("No local review feedback is attached to this changeset.")
    if summary.safe_next_actions:
        print("Safe next actions:")
        for action in summary.safe_next_actions:
            print(f"  - {action}")
    print("Non-claims:")
    for non_claim in summary.non_claims:
        print(f"  - {non_claim}")


def _print_feedback_result(
    result: ReviewFeedbackRecordResult,
    as_json: bool,
    headline: str,
) -> int:
    if as_json:
        print_json_output(_feedback_result_payload(result))
    else:
        print(f"{headline}: {result.feedback.feedback_id}")
        print(f"Changeset: {result.feedback.changeset_id}")
        print(f"Disposition: {result.feedback.disposition.value}")
        print(f"Summary: {result.feedback.summary}")
        print("Safe next actions:")
        for action in result.safe_next_actions:
            print(f"  - {action}")
        print("Glassbox did not stage, commit, push, open a PR, or merge.")
    return 0


def _print_fixup_inventory_result(
    result: ReviewFeedbackFixupInventoryResult,
    *,
    response_status: ReviewFeedbackResponseStatus,
    as_json: bool,
) -> int:
    if as_json:
        print_json_output(
            _fixup_inventory_payload(result, response_status=response_status)
        )
    else:
        print(f"Recorded response-linked fixup inventory: {result.feedback_id}")
        print(f"Changeset: {result.changeset_id}")
        print(f"Artifact: {result.artifact.relative_path.as_posix()}")
        print(
            "Paths: "
            f"{result.inventory.changed_path_count} changed, "
            f"{result.inventory.matched_scope_path_count} scoped matches"
        )
        print(f"Freshness: {result.status.freshness.value}")
        if result.status.reason is not None:
            print(f"Freshness reason: {result.status.reason}")
        print(f"Verification: {response_status.verification_state.value}")
        if response_status.verification_reason is not None:
            print(f"Verification reason: {response_status.verification_reason}")
        if result.inventory.paths:
            print("Path summaries:")
            for path in result.inventory.paths[:5]:
                matches_scope = str(path.matches_feedback_scope).lower()
                print(
                    f"  - {path.path}: {path.change_kind}; "
                    f"matches feedback scope: {matches_scope}"
                )
        print("Safe next actions:")
        for action in response_status.safe_next_actions:
            print(f"  - {action}")
        print("Non-claims:")
        for non_claim in result.inventory.non_claims:
            print(f"  - {non_claim}")
    return 0
