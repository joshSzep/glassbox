import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChangesetConsole } from "@/components/console/changeset-console";
import {
  formatReviewPostureState,
  responseBadgeVariant,
  skippedEvidencePosture,
} from "@/components/console/changeset/review-posture";
import type { components } from "@/generated/api-types";
import type { ChangesetRepositoryIntelligenceState } from "@/stores/dashboard-stores";

type BranchSearchDetail = components["schemas"]["BranchSearchDetailResponse"];
type ChangesetDetail = components["schemas"]["ChangesetDetailResponse"];
type ChangesetSummary = components["schemas"]["ChangesetSummaryResponse"];
type ChangesetVerificationPlan = components["schemas"]["ChangesetVerificationPlanPreviewResponse"];
type ChangesetVerificationPlanSummary =
  components["schemas"]["ChangesetVerificationPlanLifecycleSummaryResponse"];
type CommitMessageSuggestion = components["schemas"]["CommitMessageSuggestionResponse"];
type CommitReadiness = components["schemas"]["CommitReadinessResponse"];
type HandoffReadiness = components["schemas"]["HandoffReadinessResponse"];

describe("changeset console", () => {
  it("renders verification readiness states and safe next actions", () => {
    const changeset = makeChangesetSummary("changeset-1");
    const detail = makeChangesetDetail(changeset);
    const markup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        detail: {
          branchSearchDetail: makeBranchSearchDetail(),
          detail,
          error: null,
          commitMessage: makeCommitMessageSuggestion("changeset-1"),
          commitReadiness: makeCommitReadiness("changeset-1"),
          handoffReadiness: makeHandoffReadiness("changeset-1"),
          lastActionMessage: "Manual evidence manual-evidence-1 attached.",
          loadState: "loaded",
          repositoryIntelligence: makeChangesetRepositoryIntelligence(),
          selectedChangesetId: "changeset-1",
          verificationPlan: makeVerificationPlan("changeset-1"),
        },
        page: {
          error: null,
          items: [changeset],
          loadState: "loaded",
        },
      }),
    );

    expect(markup).toContain("Verification missing");
    expect(markup).toContain("1 failed");
    expect(markup).toContain("1 stale");
    expect(markup).toContain("2 missing");
    expect(markup).toContain("1 accepted risk");
    expect(markup).toContain("3 feedback");
    expect(markup).toContain("3 manual evidence");
    expect(markup).toContain("0 plan passed");
    expect(markup).toContain("retained verification failed");
    expect(markup).toContain("Review-loop context");
    expect(markup).toContain("1 missing response checks");
    expect(markup).toContain("pytest unit");
    expect(markup).toContain("uv run pytest tests/unit");
    expect(markup).toContain("artifact-1");
    expect(markup).toContain("Review Readiness");
    expect(markup).toContain("Review Quick Actions");
    expect(markup).toContain("Preview Verification");
    expect(markup).toContain("Feedback Status");
    expect(markup).toContain("Handoff Posture");
    expect(markup).toContain("Manual evidence summary");
    expect(markup).toContain("Actions inspect state or record explicit local evidence only");
    expect(markup).toContain("ready");
    expect(markup).toContain("Review Feedback");
    expect(markup).toContain("Record fixup");
    expect(markup).toContain('href="#feedback-feedback-1"');
    expect(markup).toContain("Clarify feedback copy");
    expect(markup).toContain("Manual Evidence Inbox");
    expect(markup).toContain('href="#evidence-manual-evidence-1"');
    expect(markup).toContain("operator says external CI passed");
    expect(markup).toContain("dashboard walkthrough rendered manual evidence");
    expect(markup).toContain("1 skipped live");
    expect(markup).toContain("not run");
    expect(markup).toContain("local dashboard server was not started");
    expect(markup).toContain("Browser/dashboard evidence is advisory and local-only");
    expect(markup).toContain("skipped browser or dashboard evidence is not a pass");
    expect(markup).toContain("focus order issue remains open");
    expect(markup).toContain("Accessibility evidence is advisory, not certification");
    expect(markup).toContain("accessibility evidence is advisory");
    expect(markup).toContain("manual evidence is not retained command evidence");
    expect(markup).toContain("1 requested");
    expect(markup).toContain("1 questions");
    expect(markup).toContain("1 accepted risks");
    expect(markup).toContain("1 responded");
    expect(markup).toContain("1 stale responses");
    expect(markup).toContain("1 unresolved feedback");
    expect(markup).toContain("3 attached");
    expect(markup).toContain("Handoff needs verification");
    expect(markup).toContain("Response planned");
    expect(markup).toContain("Verification stale");
    expect(markup).toContain("predates response-linked fixups");
    expect(markup).toContain("Inspect first:");
    expect(markup).toContain("glassbox changeset feedback fixup feedback-1 --from-workspace");
    expect(markup).toContain("app.py: matches feedback scope");
    expect(markup).toContain("Review feedback is local evidence, not approval.");
    expect(markup).toContain("Brief Artifacts");
    expect(markup).toContain("brief-artifact-1");
    expect(markup).toContain("Changed Files");
    expect(markup).toContain("3 changed paths");
    expect(markup).toContain("Affected Subsystems");
    expect(markup).toContain("glassbox - package");
    expect(markup).toContain("runtime dependency: pydantic");
    expect(markup).toContain("Repository Intelligence");
    expect(markup).toContain("Repository intelligence suggests:");
    expect(markup).toContain("Runtime changeset service");
    expect(markup).toContain("Owner hints: runtime team");
    expect(markup).toContain(
      'href="/app/repository-index?path=src%2Fglassbox%2Fruntime%2Fchangesets.py"',
    );
    expect(markup).toContain("Command Evidence");
    expect(markup).toContain("test - failed");
    expect(markup).toContain("selected verification failed before rerun");
    expect(markup).toContain("Environment captured with 2 toolchains");
    expect(markup).toContain("Final Handoff");
    expect(markup).toContain("needs verification");
    expect(markup).toContain("1 unresolved feedback");
    expect(markup).toContain("3 local-only evidence");
    expect(markup).toContain("handoff readiness is advisory local posture");
    expect(markup).toContain("Commit Preparation");
    expect(markup).toContain("needs verification");
    expect(markup).toContain("Suggested message");
    expect(markup).toContain("Glassbox did not stage");
    expect(markup).toContain("Candidate Adoption");
    expect(markup).toContain("targeted fix");
    expect(markup).toContain("Rejected Alternatives");
    expect(markup).toContain("broad refactor");
    expect(markup).toContain("Workspace mutation performed: false");
    expect(markup).toContain("Glassbox did not merge");
    expect(markup).toContain("created from selected branch-search candidate");
  });

  it("renders dashboard action states for pending, success, and failed review actions", () => {
    const changeset = makeChangesetSummary("changeset-actions");
    const detail = makeChangesetDetail(changeset);
    const baseDetailState = {
      branchSearchDetail: null,
      detail,
      error: null,
      commitMessage: null,
      commitReadiness: null,
      handoffReadiness: makeHandoffReadiness("changeset-actions"),
      lastActionMessage: null,
      loadState: "loaded" as const,
      selectedChangesetId: "changeset-actions",
      verificationPlan: makeVerificationPlan("changeset-actions"),
    };
    const page = {
      error: null,
      items: [changeset],
      loadState: "loaded" as const,
    };

    const pendingMarkup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        action: { error: null, kind: "record-feedback-fixup", state: "pending" },
        detail: baseDetailState,
        page,
      }),
    );
    const failedMarkup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        action: {
          error: "network unavailable; use the CLI fallback",
          kind: "record-feedback-fixup",
          state: "failed",
        },
        detail: baseDetailState,
        page,
      }),
    );
    const successMarkup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        action: { error: null, kind: "inspect-feedback", state: "succeeded" },
        detail: baseDetailState,
        page,
      }),
    );

    expect(pendingMarkup).toContain("record-feedback-fixup pending");
    expect(pendingMarkup).toContain("Recording");
    expect(failedMarkup).toContain("record-feedback-fixup failed");
    expect(failedMarkup).toContain("reviewer approval was not recorded");
    expect(successMarkup).toContain("inspect-feedback succeeded");
    expect(successMarkup).toContain("inspect refreshed evidence before relying on it");
  });

  it("renders ready-for-handoff response status without implying approval", () => {
    const changeset = makeChangesetSummary("changeset-ready");
    const detail = makeChangesetDetail(changeset);
    detail.review_feedback = [detail.review_feedback[1]];
    detail.review_response_summary = {
      ...detail.review_response_summary,
      blocked_count: 0,
      items: [
        {
          ...detail.review_response_summary.items[1],
          blockers: [],
          response_state: "ready_for_handoff",
          stale: false,
          stale_reason: null,
          verification_reason: "focused response check is fresh",
          verification_safe_next_actions: [],
          verification_state: "passed",
        },
      ],
      responded_count: 1,
      stale_response_count: 0,
      unresolved_count: 0,
    };
    const markup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        detail: {
          branchSearchDetail: null,
          detail,
          error: null,
          commitMessage: null,
          commitReadiness: null,
          handoffReadiness: makeHandoffReadiness("changeset-ready"),
          lastActionMessage: null,
          loadState: "loaded",
          selectedChangesetId: "changeset-ready",
          verificationPlan: makeVerificationPlan("changeset-ready"),
        },
        page: {
          error: null,
          items: [changeset],
          loadState: "loaded",
        },
      }),
    );

    expect(markup).toContain("Response ready_for_handoff");
    expect(markup).toContain("Plan link 0 selected - 1 stale");
    expect(markup).toContain("Affected check: stale passed - focused response check");
    expect(markup).toContain("Review feedback is local evidence, not approval.");
  });

  it("derives skipped evidence and response posture labels in shared helpers", () => {
    const changeset = makeChangesetSummary("changeset-posture");
    const detail = makeChangesetDetail(changeset);
    const skippedPosture = skippedEvidencePosture(detail.manual_evidence[1]);

    expect(skippedPosture).toEqual({
      reason: "local dashboard server was not started",
      state: "not_run",
      stateLabel: "not run",
    });
    expect(skippedEvidencePosture(detail.manual_evidence[0])).toBeNull();
    expect(responseBadgeVariant("ready_for_handoff")).toBe("success");
    expect(responseBadgeVariant("blocked")).toBe("warning");
    expect(formatReviewPostureState("needs_verification")).toBe("needs verification");
  });
});

function makeChangesetSummary(changesetId: string): ChangesetSummary {
  return {
    accepted_risk_count: 1,
    archived_by: null,
    archived_reason: null,
    branch_candidate_id: "candidate-1",
    branch_search_id: "search-1",
    changeset_id: changesetId,
    created_at: "2026-05-01T00:00:00Z",
    created_by: "operator",
    last_sequence: 8,
    latest_inventory_artifact_id: "artifact-inventory",
    latest_review_brief_artifact_id: "brief-artifact-1",
    latest_verification_id: "verification-1",
    objective: "Review verification posture",
    replacement_changeset_id: null,
    risk_level: "medium",
    risk_summary: "runtime and tests changed",
    session_id: "session-1",
    status: "active",
    summary: null,
    task_id: "task-1",
    turn_id: null,
    unresolved_risk_count: 1,
    updated_at: "2026-05-01T00:02:00Z",
  };
}

function makeChangesetDetail(changeset: ChangesetSummary): ChangesetDetail {
  return {
    changeset,
    inventory: {
      accepted_risk_count: 1,
      artifact_id: "artifact-inventory",
      artifact_schema_version: 1,
      branch_candidate_id: changeset.branch_candidate_id,
      branch_search_id: changeset.branch_search_id,
      changed_path_count: 3,
      changeset_id: changeset.changeset_id,
      freshness: "fresh",
      last_sequence: 7,
      previous_artifact_id: null,
      refreshed_by: "operator",
      risk_level: "medium",
      risk_summary: "runtime and tests changed",
      session_id: "session-1",
      source_digest: "sha256:current",
      task_id: "task-1",
      turn_id: null,
      unresolved_risk_count: 1,
      updated_at: "2026-05-01T00:02:00Z",
    },
    inventory_status: {
      current_source_digest: "sha256:current",
      freshness: "fresh",
      reason: null,
      recorded_source_digest: "sha256:current",
      safe_next_actions: [`glassbox changeset refresh ${changeset.changeset_id} --cwd .`],
      stale: false,
    },
    limitations: [],
    readiness: [
      {
        accepted_risk_count: 1,
        blockers: [],
        changeset_id: changeset.changeset_id,
        decided_by: "operator",
        inventory_artifact_id: "artifact-inventory",
        last_sequence: 9,
        readiness_kind: "review",
        reason: "deterministic changeset evidence is ready for reviewer inspection",
        review_brief_artifact_id: "brief-artifact-1",
        safe_next_actions: [`glassbox changeset show ${changeset.changeset_id} --cwd .`],
        session_id: "session-1",
        state: "ready",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:03:00Z",
        verification_id: "verification-1",
      },
    ],
    command_evidence: {
      artifact_count: 1,
      environment_captured_count: 1,
      failed_count: 1,
      items: [
        {
          environment_captured: true,
          local_only: true,
          output_artifact_id: "artifact-command-1",
          policy_summary: null,
          purpose: "test",
          redaction_notes: ["raw environment is not stored"],
          review_relevance: "verification",
          status: "failed",
          summary: "selected verification failed before rerun",
          supports_verification: true,
          task_id: "task-1",
          tool_attempt_id: "attempt-1",
          tool_name: "run_command",
          toolchain_count: 2,
          turn_id: "turn-1",
        },
      ],
      limitations: [],
      risky_count: 0,
      safe_next_actions: [
        "glassbox session tool-attempt inspect attempt-1 --session session-1 --cwd .",
      ],
      total_count: 1,
      verification_count: 1,
    },
    review_briefs: [
      {
        artifact_id: "brief-artifact-1",
        artifact_schema_version: 1,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:03:00Z",
        created_by: "operator",
        inventory_artifact_id: "artifact-inventory",
        last_sequence: 8,
        local_only: true,
        redacted: true,
        render_targets: ["markdown", "json"],
        session_id: "session-1",
        task_id: "task-1",
        turn_id: null,
        verification_id: "verification-1",
      },
    ],
    review_feedback: [
      {
        acceptance_reason: null,
        accepted_by: null,
        archived_by: null,
        archived_reason: null,
        artifact_id: null,
        body: "The panel should not imply approval.",
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:03:00Z",
        created_by: "operator",
        disposition: "open",
        feedback_id: "feedback-1",
        feedback_kind: "requested_change",
        last_sequence: 10,
        provenance: "reviewer",
        reopened_count: 0,
        replacement_feedback_id: null,
        residual_risk: null,
        resolution_summary: null,
        resolved_by: null,
        reviewer_label: "reviewer-1",
        risk_summary: null,
        session_id: "session-1",
        source_label: "local-review",
        source_session_id: null,
        summary: "Clarify feedback copy",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:04:00Z",
        updated_by: null,
        verification_id: null,
      },
      {
        acceptance_reason: null,
        accepted_by: null,
        archived_by: null,
        archived_reason: null,
        artifact_id: null,
        body: null,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:03:00Z",
        created_by: "operator",
        disposition: "resolved_locally",
        feedback_id: "feedback-2",
        feedback_kind: "reviewer_question",
        last_sequence: 11,
        provenance: "reviewer",
        reopened_count: 0,
        replacement_feedback_id: null,
        residual_risk: "Reviewer acceptance is not implied.",
        resolution_summary: "Answered with retained API evidence.",
        resolved_by: "operator",
        reviewer_label: "reviewer-2",
        risk_summary: null,
        session_id: "session-1",
        source_label: null,
        source_session_id: null,
        summary: "Does this expose questions?",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:04:00Z",
        updated_by: null,
        verification_id: null,
      },
      {
        acceptance_reason: "Scoped to dashboard mutation only.",
        accepted_by: "operator",
        archived_by: null,
        archived_reason: null,
        artifact_id: null,
        body: null,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:03:00Z",
        created_by: "operator",
        disposition: "accepted_with_risk",
        feedback_id: "feedback-3",
        feedback_kind: "risk",
        last_sequence: 12,
        provenance: "operator",
        reopened_count: 0,
        replacement_feedback_id: null,
        residual_risk: null,
        resolution_summary: null,
        resolved_by: null,
        reviewer_label: null,
        risk_summary: "Dashboard remains read-only for this slice.",
        session_id: "session-1",
        source_label: null,
        source_session_id: null,
        summary: "Dashboard mutation deferred",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:04:00Z",
        updated_by: null,
        verification_id: null,
      },
    ],
    manual_evidence: [
      {
        archived_reason: null,
        artifact_id: "manual-evidence-artifact-1",
        artifact_schema_version: 1,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:05:00Z",
        created_by: "operator",
        evidence_id: "manual-evidence-1",
        evidence_kind: "external_check",
        feedback_id: null,
        freshness: "current",
        last_sequence: 13,
        limitations: ["manual evidence is summary-first"],
        local_only: true,
        non_claims: ["not retained command evidence"],
        observed_at: null,
        redaction_status: "passed",
        rejected_reason: null,
        replacement_evidence_id: null,
        session_id: "session-1",
        source_label: "external-ci",
        state: "attached",
        summary: "operator says external CI passed",
        superseded_reason: null,
        target_id: changeset.changeset_id,
        target_kind: "changeset",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:05:00Z",
        verification_id: null,
      },
      {
        archived_reason: null,
        artifact_id: "browser-evidence-artifact-1",
        artifact_schema_version: 1,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:06:00Z",
        created_by: "operator",
        evidence_id: "manual-evidence-2",
        evidence_kind: "browser_observation",
        feedback_id: "feedback-1",
        freshness: "needs_inspection",
        last_sequence: 14,
        limitations: [
          "browser/dashboard evidence is advisory live evidence",
          "capture state: not_run",
          "skip reason: local dashboard server was not started",
        ],
        local_only: true,
        non_claims: [
          "not deterministic release authority",
          "skipped browser/dashboard evidence is not a pass",
        ],
        observed_at: "2026-05-01T00:06:00Z",
        redaction_status: "passed",
        rejected_reason: null,
        replacement_evidence_id: null,
        session_id: "session-1",
        source_label: "dashboard-local",
        state: "attached",
        summary: "dashboard walkthrough rendered manual evidence",
        superseded_reason: null,
        target_id: "feedback-1",
        target_kind: "feedback",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:06:00Z",
        verification_id: null,
      },
      {
        archived_reason: null,
        artifact_id: "accessibility-evidence-artifact-1",
        artifact_schema_version: 1,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:07:00Z",
        created_by: "operator",
        evidence_id: "manual-evidence-3",
        evidence_kind: "accessibility_note",
        feedback_id: "feedback-1",
        freshness: "needs_inspection",
        last_sequence: 15,
        limitations: ["severity: high", "disposition: paired_with_feedback"],
        local_only: true,
        non_claims: ["not accessibility certification"],
        observed_at: null,
        redaction_status: "passed",
        rejected_reason: null,
        replacement_evidence_id: null,
        session_id: "session-1",
        source_label: "keyboard-review",
        state: "attached",
        summary: "focus order issue remains open",
        superseded_reason: null,
        target_id: "feedback-1",
        target_kind: "feedback",
        task_id: "task-1",
        turn_id: null,
        updated_at: "2026-05-01T00:07:00Z",
        verification_id: null,
      },
    ],
    review_response_summary: {
      accepted_risk_count: 1,
      blocked_count: 1,
      blockers: [
        "feedback-2: workspace diff source digest changed since fixup inventory was recorded",
      ],
      changeset_id: changeset.changeset_id,
      items: [
        {
          blockers: [],
          changed_path_count: 0,
          changeset_id: changeset.changeset_id,
          disposition: "open",
          feedback_id: "feedback-1",
          fixup_inventory_count: 0,
          inventory_freshness: "unknown",
          latest_fixup_inventory_artifact_id: null,
          latest_fixup_inventory_at: null,
          latest_fixup_inventory_sequence: null,
          latest_source_kind: null,
          latest_source_summary: null,
          matched_scope_path_count: 0,
          non_claims: ["review response status is local evidence, not reviewer acceptance"],
          path_summaries: [],
          response_state: "planned",
          verification_reason: "feedback has no response-linked fixup inventory to verify",
          verification_requirement_ids: [],
          verification_safe_next_actions: [
            `glassbox changeset verification-plan ${changeset.changeset_id} --cwd .`,
          ],
          verification_plan_entries: [],
          selected_plan_entry_count: 0,
          stale_plan_entry_count: 0,
          skipped_plan_entry_count: 0,
          accepted_risk_plan_entry_count: 0,
          newly_required_check_count: 1,
          verification_limitations: [
            "record response-linked fixup inventory before mapping checks",
          ],
          verification_state: "missing",
          safe_next_actions: [
            "glassbox changeset feedback show feedback-1 --cwd .",
            `glassbox changeset show ${changeset.changeset_id} --cwd .`,
          ],
          stale: false,
          stale_reason: null,
          summary: "Clarify feedback copy",
        },
        {
          blockers: ["workspace diff source digest changed since fixup inventory was recorded"],
          changed_path_count: 2,
          changeset_id: changeset.changeset_id,
          disposition: "resolved_locally",
          feedback_id: "feedback-2",
          fixup_inventory_count: 1,
          inventory_freshness: "stale",
          latest_fixup_inventory_artifact_id: "fixup-artifact-1",
          latest_fixup_inventory_at: "2026-05-01T00:04:00Z",
          latest_fixup_inventory_sequence: 13,
          latest_source_kind: "manual_workspace_edit",
          latest_source_summary: "operator recorded response inventory",
          matched_scope_path_count: 1,
          non_claims: ["review response status is local evidence, not reviewer acceptance"],
          path_summaries: ["app.py: matches feedback scope"],
          response_state: "blocked",
          verification_reason:
            "focused response check passed before response-linked fixup inventory changed overlapping paths",
          verification_requirement_ids: ["verification-1", "fixup-inventory:fixup-artifact-1"],
          verification_safe_next_actions: [
            "rerun uv run pytest tests/test_app.py because focused response check predates response-linked fixups",
          ],
          verification_plan_entries: [
            {
              verification_id: "verification-1",
              check_name: "focused response check",
              status: "passed",
              relationship: "stale",
              reason: "focused response check is fresh for response-linked fixup paths",
              command: ["uv", "run", "pytest", "tests/test_app.py"],
              changed_paths: ["app.py"],
              safe_next_actions: [
                "rerun uv run pytest tests/test_app.py because response-linked fixups are newer",
              ],
            },
          ],
          selected_plan_entry_count: 0,
          stale_plan_entry_count: 1,
          skipped_plan_entry_count: 0,
          accepted_risk_plan_entry_count: 0,
          newly_required_check_count: 0,
          verification_limitations: [
            "fresh verification requires evidence newer than the fixup inventory",
          ],
          verification_state: "stale",
          safe_next_actions: [
            "glassbox changeset feedback show feedback-2 --cwd .",
            `glassbox changeset show ${changeset.changeset_id} --cwd .`,
          ],
          stale: true,
          stale_reason: "workspace diff source digest changed since fixup inventory was recorded",
          summary: "Does this expose questions?",
        },
        {
          blockers: [],
          changed_path_count: 0,
          changeset_id: changeset.changeset_id,
          disposition: "accepted_with_risk",
          feedback_id: "feedback-3",
          fixup_inventory_count: 0,
          inventory_freshness: "unknown",
          latest_fixup_inventory_artifact_id: null,
          latest_fixup_inventory_at: null,
          latest_fixup_inventory_sequence: null,
          latest_source_kind: null,
          latest_source_summary: null,
          matched_scope_path_count: 0,
          non_claims: ["review response status is local evidence, not reviewer acceptance"],
          path_summaries: [],
          response_state: "accepted_with_risk",
          verification_reason: "feedback response is accepted with local risk",
          verification_requirement_ids: [],
          verification_safe_next_actions: ["glassbox changeset feedback show feedback-3 --cwd ."],
          verification_plan_entries: [],
          selected_plan_entry_count: 0,
          stale_plan_entry_count: 0,
          skipped_plan_entry_count: 0,
          accepted_risk_plan_entry_count: 0,
          newly_required_check_count: 0,
          verification_limitations: [
            "accepted risk is local evidence and does not mark checks passed",
          ],
          verification_state: "accepted_with_risk",
          safe_next_actions: [
            "glassbox changeset feedback show feedback-3 --cwd .",
            `glassbox changeset show ${changeset.changeset_id} --cwd .`,
          ],
          stale: false,
          stale_reason: null,
          summary: "Dashboard mutation deferred",
        },
      ],
      non_claims: ["Review feedback is local evidence, not approval."],
      open_count: 1,
      responded_count: 1,
      safe_next_actions: [
        `glassbox changeset feedback list --changeset ${changeset.changeset_id} --cwd .`,
        `glassbox changeset show ${changeset.changeset_id} --cwd .`,
      ],
      stale_response_count: 1,
      total_feedback_count: 3,
      unresolved_count: 2,
    },
    safe_next_actions: [`glassbox changeset show ${changeset.changeset_id} --cwd .`],
    sources: [
      {
        artifact_id: null,
        branch_candidate_id: changeset.branch_candidate_id,
        branch_search_id: changeset.branch_search_id,
        changeset_id: changeset.changeset_id,
        created_at: "2026-05-01T00:03:00Z",
        last_sequence: 8,
        limitation: "candidate adoption does not merge parent history",
        reason: "created from selected branch-search candidate",
        session_id: "session-1",
        source_kind: "branch_search_candidate",
        source_session_id: "candidate-session-1",
        task_id: "task-1",
        turn_id: null,
        verification_id: "verification-1",
      },
    ],
    verification_plan_summary: makeVerificationPlanSummary(changeset.changeset_id),
    verification_posture: {
      accepted_risk_count: 1,
      changeset_id: changeset.changeset_id,
      failed_count: 1,
      artifact_id: "artifact-1",
      last_sequence: 8,
      missing_count: 2,
      session_id: "session-1",
      stale_count: 1,
      state: "missing",
      summary: "verification readiness is missing",
      task_id: "task-1",
      turn_id: null,
      updated_at: "2026-05-01T00:02:00Z",
      verification_id: "verification-1",
    },
  };
}

function makeBranchSearchDetail(): BranchSearchDetail {
  return {
    candidates: [
      {
        artifact_id: "candidate-artifact-1",
        candidate_id: "candidate-1",
        candidate_session_id: "candidate-session-1",
        changed_files: ["src/glassbox/runtime/changesets.py"],
        created_at: "2026-05-01T00:01:00Z",
        last_sequence: 5,
        parent_session_id: "session-1",
        patch_summary: "focused changeset adoption path",
        policy_budget_summary: null,
        residual_risks: ["manual review still required"],
        search_id: "search-1",
        selection_state: "selected",
        status: "completed",
        strategy_label: "targeted fix",
        updated_at: "2026-05-01T00:02:00Z",
        verification_id: "verification-1",
        verification_status: "passed",
        verification_summary: "unit coverage retained",
      },
      {
        artifact_id: "candidate-artifact-2",
        candidate_id: "candidate-2",
        candidate_session_id: "candidate-session-2",
        changed_files: ["src/glassbox/runtime/changesets.py", "frontend/app/page.tsx"],
        created_at: "2026-05-01T00:01:00Z",
        last_sequence: 5,
        parent_session_id: "session-1",
        patch_summary: "larger implementation sweep",
        policy_budget_summary: null,
        residual_risks: ["broader review surface"],
        search_id: "search-1",
        selection_state: "rejected",
        status: "completed",
        strategy_label: "broad refactor",
        updated_at: "2026-05-01T00:02:00Z",
        verification_id: null,
        verification_status: "not_run",
        verification_summary: "no verification retained",
      },
    ],
    decision_support: {
      automatic_merge: false,
      candidates: [
        {
          accepted_risks: ["manual review still required"],
          candidate_id: "candidate-1",
          candidate_session_id: "candidate-session-1",
          changed_files: ["src/glassbox/runtime/changesets.py"],
          changed_files_summary: "1 focused runtime path changed",
          cost_estimate: "low",
          evidence: [],
          objective: "Review verification posture",
          recommended_follow_up_action: "refresh inventory after adoption",
          risk_posture: "review",
          search_id: "search-1",
          selection_state: "selected",
          status: "completed",
          strategy_label: "targeted fix",
          verification_posture: "passed",
          verification_recommendations: [],
        },
        {
          accepted_risks: [],
          candidate_id: "candidate-2",
          candidate_session_id: "candidate-session-2",
          changed_files: ["src/glassbox/runtime/changesets.py", "frontend/app/page.tsx"],
          changed_files_summary: "runtime and frontend paths changed",
          cost_estimate: "medium",
          evidence: [],
          objective: "Review verification posture",
          recommended_follow_up_action: "inspect diff before reconsidering",
          risk_posture: "higher",
          search_id: "search-1",
          selection_state: "rejected",
          status: "completed",
          strategy_label: "broad refactor",
          verification_posture: "missing",
          verification_recommendations: [],
        },
      ],
      non_goal: "Branch search does not automatically merge candidates.",
      objective: "Review verification posture",
      search_id: "search-1",
    },
    search: {
      abandoned_reason: null,
      candidate_count: 2,
      created_at: "2026-05-01T00:00:00Z",
      last_sequence: 5,
      objective: "Review verification posture",
      parent_session_id: "session-1",
      search_id: "search-1",
      selected_candidate_id: "candidate-1",
      session_id: "session-1",
      status: "completed",
      task_id: "task-1",
      updated_at: "2026-05-01T00:02:00Z",
    },
  };
}

function makeVerificationPlan(changesetId: string): ChangesetVerificationPlan {
  return {
    changed_paths: ["src/glassbox/runtime/changesets.py"],
    changeset_id: changesetId,
    eval_profiles: [],
    expected_scope: ["src/glassbox/runtime/changesets.py"],
    inventory_artifact_id: "artifact-inventory",
    inventory_freshness: "fresh",
    limitations: [],
    non_claims: ["verification plan preview does not run commands"],
    plan_summary: makeVerificationPlanSummary(changesetId),
    plan_entries: [],
    review_loop_summary: {
      accepted_risk_response_count: 1,
      accessibility_evidence_count: 1,
      browser_evidence_count: 1,
      skipped_accessibility_evidence_count: 0,
      skipped_browser_evidence_count: 1,
      skipped_live_evidence_count: 1,
      failed_response_verification_count: 0,
      feedback_count: 3,
      manual_evidence_count: 3,
      manual_evidence_kind_counts: {
        accessibility_note: 1,
        browser_observation: 1,
        external_check: 1,
      },
      missing_response_verification_count: 1,
      non_claims: [
        "manual evidence suggests context only; retained verification decides check state",
      ],
      open_feedback_count: 1,
      response_state_counts: {
        accepted_with_risk: 1,
        blocked: 1,
        planned: 1,
      },
      retained_verification_state: "missing",
      safe_next_actions: [`glassbox changeset evidence list --changeset ${changesetId} --cwd .`],
      stale_check_count: 1,
      stale_response_count: 1,
      topology_impact_count: 1,
      limitations: [
        "manual evidence can inform verification choice but is not retained verification proof",
      ],
    },
    readiness: {
      accepted_risk_count: 1,
      failed_count: 1,
      missing_count: 2,
      non_claims: ["verification readiness is advisory review posture, not proof"],
      requirements: [
        {
          artifact_id: "artifact-1",
          blocking: true,
          changed_paths: ["src/glassbox/runtime/changesets.py"],
          check_name: "pytest unit",
          command: ["uv", "run", "pytest", "tests/unit"],
          evidence_summary: "unit test failed",
          kind: "test",
          reason: "retained verification failed",
          requirement_id: "changed-path-ledger",
          safe_next_actions: ["inspect retained verification output before retrying"],
          source: "changed_paths",
          state: "failed",
          verification_id: "verification-1",
        },
      ],
      safe_next_actions: ["uv run pytest tests/unit"],
      stale_count: 1,
      state: "missing",
      summary: "verification readiness is missing: 1 failed, 1 stale, 2 missing",
    },
    reason_groups: [],
    recommended_commands: ["uv run pytest tests/unit"],
    recipes: [],
    topology_impacts: [
      {
        component_id: "package:glassbox",
        dependency_hints: ["runtime dependency: pydantic"],
        kind: "package",
        limitations: [],
        matched_paths: ["src/glassbox/runtime/changesets.py"],
        name: "glassbox",
        ownership_hints: ["runtime"],
        recommendation_posture: "fresh",
        root_path: ".",
        test_roots: ["tests"],
        topology_freshness: "fresh",
      },
    ],
    retained_artifact_ids: ["artifact-1"],
    safe_next_actions: ["uv run pytest tests/unit"],
    session_id: "session-1",
    skipped_checks: [],
  };
}

function makeChangesetRepositoryIntelligence(): ChangesetRepositoryIntelligenceState {
  const provenance = [
    {
      content_sha256: null,
      line_end: 1,
      line_start: 1,
      note: null,
      path: "src/glassbox/runtime/changesets.py",
      source_label: null,
      source_type: "test_fixture",
      tool_name: "fixture-indexer",
    },
  ];
  const commandRecipe = {
    command: "uv run pytest tests/integration/test_web_changeset_routes.py",
    confidence: "high",
    limitations: [],
    name: "Changeset route integration tests",
    provenance,
    purpose: "Validate changeset API behavior for runtime and dashboard changes.",
    recipe_id: "recipe-changesets",
    review_relevance: "verification",
    risk: "read_only",
    scope_paths: ["src/glassbox/runtime/changesets.py"],
    timeout_seconds: 120,
    toolchain: "uv",
  };
  return {
    commandRecipes: [commandRecipe],
    error: null,
    freshness: {
      cues: [],
      index: {
        builder_version: "test",
        built_at: "2026-05-01T00:00:00Z",
        command_recipe_count: 1,
        detail: null,
        doc_root_count: 0,
        entry_count: 1,
        freshness_cues: [],
        generated_path_count: 0,
        limitations: [],
        memory_reference_count: 0,
        ownership_hint_count: 1,
        package_boundary_count: 1,
        path: "/tmp/repo-index.json",
        policy_sensitive_path_count: 0,
        release_surface_count: 1,
        schema_version: 1,
        source_digest: "digest",
        source_manifest_count: 0,
        source_root_count: 1,
        status: "fresh",
        subsystem_count: 1,
        test_root_count: 1,
      },
      next_actions: [],
      topology: null,
    },
    loadState: "loaded",
    pathInspections: [
      {
        command_recipes: [commandRecipe],
        next_actions: ["uv run pytest tests/integration/test_web_changeset_routes.py"],
        ownership_hints: [
          {
            confidence: "medium",
            hint_id: "owner-runtime",
            limitations: [],
            owner_label: "runtime team",
            provenance,
            scope_paths: ["src/glassbox/runtime"],
            subsystem: "Runtime changeset service",
          },
        ],
        packages: [
          {
            confidence: "high",
            doc_roots: [],
            generated_paths: [],
            kind: "python",
            limitations: [],
            manifest_paths: ["pyproject.toml"],
            name: "glassbox",
            package_id: "package-glassbox",
            provenance,
            root: ".",
            source_roots: ["src"],
            test_roots: ["tests"],
          },
        ],
        path: "src/glassbox/runtime/changesets.py",
        path_hints: [],
        release_surfaces: [
          {
            command_recipe_ids: ["recipe-changesets"],
            confidence: "medium",
            kind: "runtime",
            limitations: [],
            name: "Changeset review surface",
            provenance,
            scope_paths: ["src/glassbox/runtime"],
            surface_id: "surface-changesets",
          },
        ],
        snapshot_status: "fresh",
        subsystems: [
          {
            confidence: "high",
            limitations: [],
            name: "Runtime changeset service",
            owner_hint_ids: ["owner-runtime"],
            package_ids: ["package-glassbox"],
            provenance,
            release_surface_ids: ["surface-changesets"],
            scope_paths: ["src/glassbox/runtime"],
            subsystem_id: "subsystem-changesets",
            tags: ["runtime", "changesets"],
          },
        ],
      },
    ],
    verification: {
      detail: null,
      next_actions: ["uv run pytest tests/integration/test_web_changeset_routes.py"],
      paths: ["src/glassbox/runtime/changesets.py"],
      report: null,
      status: "ok",
    },
  };
}

function makeCommitReadiness(changesetId: string): CommitReadiness {
  return {
    accepted_risk_count: 1,
    blockers: ["verification readiness is missing"],
    changeset_id: changesetId,
    git: {
      ahead: 0,
      behind: 0,
      branch: "main",
      clean: false,
      error: null,
      generated_paths: ["frontend/generated/api-types.ts"],
      policy_sensitive_paths: ["docs/tasks-v12.md"],
      staged_path_count: 1,
      staged_paths: ["src/glassbox/runtime/changesets.py"],
      untracked_paths: ["notes.txt"],
      unstaged_paths: ["docs/tasks-v12.md"],
      workspace_path_count: 3,
    },
    inventory_artifact_id: "artifact-inventory",
    local_only_evidence_count: 3,
    manual_evidence_count: 3,
    non_claims: ["this model does not stage files or run git commit"],
    readiness_kind: "commit",
    reason: "verification readiness is missing",
    review_feedback_count: 3,
    review_brief_artifact_id: "brief-artifact-1",
    safe_next_actions: ["git status --short"],
    session_id: "session-1",
    signals: [
      {
        blocking: true,
        paths: [],
        signal_id: "verification-readiness",
        state: "needs_verification",
        summary: "verification readiness is missing",
      },
    ],
    state: "needs_verification",
    stale_response_count: 1,
    unresolved_feedback_count: 1,
    verification_id: "verification-1",
  };
}

function makeHandoffReadiness(changesetId: string): HandoffReadiness {
  return {
    blockers: ["verification readiness is missing"],
    changeset_id: changesetId,
    commit_readiness_state: "needs_verification",
    evidence: {
      accepted_risk_count: 1,
      accessibility_evidence_count: 1,
      browser_evidence_count: 1,
      feedback_count: 3,
      local_only_evidence_count: 3,
      manual_evidence_count: 3,
      needs_inspection_evidence_count: 2,
      review_brief_count: 1,
      skipped_accessibility_evidence_count: 0,
      skipped_browser_evidence_count: 1,
      skipped_live_evidence_count: 1,
      stale_manual_evidence_count: 0,
      stale_response_count: 1,
      unresolved_feedback_count: 1,
    },
    git: {
      ahead: 0,
      behind: 0,
      branch: "main",
      clean: false,
      error: null,
      generated_paths: ["frontend/generated/api-types.ts"],
      policy_sensitive_paths: ["docs/tasks-v12.md"],
      staged_path_count: 1,
      staged_paths: ["src/glassbox/runtime/changesets.py"],
      untracked_paths: ["notes.txt"],
      unstaged_paths: ["docs/tasks-v12.md"],
      workspace_path_count: 3,
    },
    inventory_artifact_id: "artifact-inventory",
    limitations: ["local-only evidence can support local handoff context"],
    non_claims: ["handoff readiness is advisory local posture, not publication"],
    readiness_kind: "handoff",
    reason: "needs verification: verification readiness is missing",
    review_brief_artifact_id: "brief-artifact-1",
    verification_plan_summary: makeVerificationPlanSummary(changesetId),
    safe_next_actions: [
      `glassbox changeset show ${changesetId} --cwd .`,
      `glassbox changeset verification-plan ${changesetId} --cwd .`,
    ],
    session_id: "session-1",
    signals: [
      {
        blocking: true,
        paths: ["src/glassbox/runtime/changesets.py"],
        signal_id: "verification-not-passed",
        state: "needs_verification",
        summary: "verification readiness is missing",
      },
      {
        blocking: false,
        paths: [],
        signal_id: "local-only-evidence",
        state: "handoff_ready",
        summary: "3 local-only evidence items must remain labeled",
      },
    ],
    state: "needs_verification",
    verification_id: "verification-1",
  };
}

function makeVerificationPlanSummary(changesetId: string): ChangesetVerificationPlanSummary {
  return {
    accepted_risk_count: 1,
    command_count: 1,
    entries: [
      {
        accepted_risk_count: 0,
        accepted_risks: [],
        artifact_id: "artifact-1",
        blocking: true,
        changed_paths: ["src/glassbox/runtime/changesets.py"],
        check_name: "pytest unit",
        command: ["uv", "run", "pytest", "tests/unit"],
        failed_artifact_id: "artifact-1",
        failure_summary: "unit test failed",
        kind: "test",
        last_sequence: 8,
        lifecycle_state: "failed",
        reason: "retained verification failed",
        source: "changed_paths",
        stale_reasons: [],
        status: "failed",
        verification_id: "verification-1",
      },
    ],
    failed_count: 1,
    latest_status: "failed",
    latest_verification_id: "verification-1",
    manual_only_count: 0,
    non_claims: ["verification plan summary is local evidence, not reviewer approval"],
    passed_count: 0,
    proposed_count: 0,
    running_count: 0,
    safe_next_actions: [`glassbox changeset verification-plan ${changesetId} --cwd .`],
    selected_count: 0,
    skipped_count: 0,
    stale_count: 1,
    total_count: 1,
  };
}

function makeCommitMessageSuggestion(changesetId: string): CommitMessageSuggestion {
  return {
    body: ["Commit readiness: needs_verification"],
    changeset_id: changesetId,
    commit_readiness_state: "needs_verification",
    deterministic: true,
    evidence: [],
    limitations: [],
    message: "Review verification posture\n\n- Commit readiness: needs_verification",
    non_claims: ["commit message is a deterministic suggestion, not a commit action"],
    schema_version: 1,
    session_id: "session-1",
    style: "plain",
    subject: "Review verification posture",
    suggestion_kind: "changeset_commit_message_suggestion",
    suggestion_label: "suggestion_only_not_committed",
  };
}
