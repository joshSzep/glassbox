import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChangesetConsole } from "@/components/console/changeset-console";
import type { components } from "@/generated/api-types";

type BranchSearchDetail = components["schemas"]["BranchSearchDetailResponse"];
type ChangesetDetail = components["schemas"]["ChangesetDetailResponse"];
type ChangesetSummary = components["schemas"]["ChangesetSummaryResponse"];
type ChangesetVerificationPlan = components["schemas"]["ChangesetVerificationPlanPreviewResponse"];
type CommitMessageSuggestion = components["schemas"]["CommitMessageSuggestionResponse"];
type CommitReadiness = components["schemas"]["CommitReadinessResponse"];

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
          loadState: "loaded",
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
    expect(markup).toContain("pytest unit");
    expect(markup).toContain("uv run pytest tests/unit");
    expect(markup).toContain("artifact-1");
    expect(markup).toContain("Review Readiness");
    expect(markup).toContain("ready");
    expect(markup).toContain("Review Feedback");
    expect(markup).toContain("Clarify feedback copy");
    expect(markup).toContain("1 requested");
    expect(markup).toContain("1 questions");
    expect(markup).toContain("1 accepted risks");
    expect(markup).toContain("1 responded");
    expect(markup).toContain("1 stale responses");
    expect(markup).toContain("Response planned");
    expect(markup).toContain("app.py: matches feedback scope");
    expect(markup).toContain("Review feedback is local evidence, not approval.");
    expect(markup).toContain("Brief Artifacts");
    expect(markup).toContain("brief-artifact-1");
    expect(markup).toContain("Changed Files");
    expect(markup).toContain("3 changed paths");
    expect(markup).toContain("Affected Subsystems");
    expect(markup).toContain("glassbox - package");
    expect(markup).toContain("runtime dependency: pydantic");
    expect(markup).toContain("Command Evidence");
    expect(markup).toContain("test - failed");
    expect(markup).toContain("selected verification failed before rerun");
    expect(markup).toContain("Environment captured with 2 toolchains");
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
    non_claims: ["this model does not stage files or run git commit"],
    readiness_kind: "commit",
    reason: "verification readiness is missing",
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
    verification_id: "verification-1",
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
