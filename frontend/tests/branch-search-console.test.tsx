import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BranchSearchConsole } from "@/components/console/branch-search-console";
import type { components } from "@/generated/api-types";
import type { BranchSearchDetailState, BranchSearchPageState } from "@/stores/dashboard-stores";

type BranchCandidate = components["schemas"]["BranchCandidateResponse"];
type BranchCandidateDecisionSupport =
  components["schemas"]["BranchCandidateDecisionSupportResponse"];
type BranchSearchDecisionSupport = components["schemas"]["BranchSearchDecisionSupportResponse"];
type BranchSearchSummary = components["schemas"]["BranchSearchSummaryResponse"];

describe("branch search console", () => {
  it("renders candidate comparison evidence and metadata actions", () => {
    const search = makeSearch("search-1", { selected_candidate_id: "candidate-1" });
    const selected = makeCandidate("candidate-1", { selection_state: "selected" });
    const selectedSupport = makeCandidateSupport("candidate-1", {
      recommended_follow_up_action:
        "Inspect the selected candidate session before manually carrying work forward.",
      selection_state: "selected",
    });
    const failed = makeCandidate("candidate-2", {
      candidate_session_id: null,
      changed_files: [],
      residual_risks: ["Verification ended failed."],
      selection_state: "needs_review",
      strategy_label: "Try broader rewrite",
      verification_status: "failed",
      verification_summary: "Regression test failed.",
    });
    const failedSupport = makeCandidateSupport("candidate-2", {
      accepted_risks: ["candidate verification failed"],
      candidate_session_id: null,
      cost_estimate: "unknown",
      evidence: [{ kind: "verification", summary: "Regression test failed." }],
      recommended_follow_up_action:
        "Review the candidate session and verification evidence before selecting or rejecting it.",
      risk_posture: "review",
      selection_state: "needs_review",
      strategy_label: "Try broader rewrite",
      verification_posture: "risky",
      verification_recommendations: [
        {
          rationale:
            "Branch search search-1 does not retain changed-file evidence for this candidate yet.",
          source: "missing-changed-files",
        },
      ],
    });
    const markup = renderToStaticMarkup(
      React.createElement(BranchSearchConsole, {
        detail: {
          detail: {
            candidates: [selected, failed],
            decision_support: makeDecisionSupport("search-1", {
              candidates: [selectedSupport, failedSupport],
              selected_candidate_id: "candidate-1",
            }),
            search,
          },
          error: null,
          loadState: "loaded",
          selectedSearchId: "search-1",
        },
        page: {
          error: null,
          items: [search],
          loadState: "loaded",
        },
      }),
    );

    expect(markup).toContain("Branch Search");
    expect(markup).toContain("Metadata only");
    expect(markup).toContain('aria-label="Branch search list"');
    expect(markup).toContain("Try minimal fix");
    expect(markup).toContain("Targeted tests passed.");
    expect(markup).toContain("Risk strong");
    expect(markup).toContain("Cost low");
    expect(markup).toContain("pnpm --dir frontend test");
    expect(markup).toContain("candidate verification failed");
    expect(markup).toContain("Changed-file evidence is not captured");
    expect(markup).toContain("Session session-...");
    expect(markup).toContain("Select");
    expect(markup).toContain("Review");
    expect(markup).toContain("Reject");
    expect(markup).toContain('aria-label="Select Try minimal fix"');
    expect(markup).toContain('aria-label="Reject Try broader rewrite"');
  });

  it("renders loading and empty states", () => {
    expect(
      renderToStaticMarkup(
        React.createElement(BranchSearchConsole, {
          detail: idleDetail,
          page: { ...idlePage, loadState: "loading" },
        }),
      ),
    ).toContain("Loading branch searches");

    expect(
      renderToStaticMarkup(
        React.createElement(BranchSearchConsole, {
          detail: idleDetail,
          page: { ...idlePage, loadState: "loaded" },
        }),
      ),
    ).toContain("No branch searches are available");
  });
});

const idlePage: BranchSearchPageState = {
  error: null,
  items: [],
  loadState: "idle",
};

const idleDetail: BranchSearchDetailState = {
  detail: null,
  error: null,
  loadState: "idle",
  selectedSearchId: null,
};

function makeSearch(
  searchId: string,
  overrides: Partial<BranchSearchSummary> = {},
): BranchSearchSummary {
  return {
    abandoned_reason: null,
    candidate_count: 2,
    created_at: "2026-04-23T00:00:00Z",
    last_sequence: 4,
    objective: "Compare repair options",
    parent_session_id: "session-1",
    search_id: searchId,
    selected_candidate_id: null,
    session_id: "session-1",
    status: "completed",
    task_id: "task-1",
    updated_at: "2026-04-23T00:01:00Z",
    ...overrides,
  };
}

function makeCandidateSupport(
  candidateId: string,
  overrides: Partial<BranchCandidateDecisionSupport> = {},
): BranchCandidateDecisionSupport {
  return {
    accepted_risks: [],
    candidate_id: candidateId,
    candidate_session_id: "session-child",
    changed_files: [],
    changed_files_summary:
      "Changed-file evidence is not captured in current branch-search projections.",
    cost_estimate: "low",
    evidence: [
      {
        kind: "session",
        session_id: "session-child",
        summary: "Candidate session is retained for inspection.",
      },
      {
        kind: "verification",
        summary: "Targeted tests passed.",
        verification_id: "verification-1",
      },
    ],
    objective: "Compare repair options",
    recommended_follow_up_action:
      "Candidate is eligible for operator review and explicit selection.",
    risk_posture: "strong",
    search_id: "search-1",
    selection_state: null,
    status: "verified",
    strategy_label: "Try minimal fix",
    verification_posture: "strong",
    verification_recommendations: [
      {
        commands: ["pnpm --dir frontend test"],
        rationale: "Candidate changed files matched repository verification recommendations.",
        recipe_ids: ["frontend-dashboard"],
        source: "changed-files",
      },
    ],
    ...overrides,
  };
}

function makeDecisionSupport(
  searchId: string,
  overrides: Partial<BranchSearchDecisionSupport> = {},
): BranchSearchDecisionSupport {
  return {
    automatic_merge: false,
    candidates: [makeCandidateSupport("candidate-1", { search_id: searchId })],
    non_goal:
      "Branch search records candidate evidence and operator decisions; it does not automatically merge or mutate parent history.",
    objective: "Compare repair options",
    search_id: searchId,
    selected_candidate_id: null,
    ...overrides,
  };
}

function makeCandidate(
  candidateId: string,
  overrides: Partial<BranchCandidate> = {},
): BranchCandidate {
  return {
    artifact_id: "artifact-1",
    candidate_id: candidateId,
    candidate_session_id: "session-child",
    changed_files: ["src/glassbox/runtime/example.py"],
    created_at: "2026-04-23T00:00:00Z",
    last_sequence: 4,
    parent_session_id: "session-1",
    patch_summary: "Updated runtime branch search handling.",
    policy_budget_summary: "Used one branch attempt from the task budget.",
    residual_risks: ["Needs operator merge review."],
    search_id: "search-1",
    selection_state: null,
    status: "verified",
    strategy_label: "Try minimal fix",
    updated_at: "2026-04-23T00:01:00Z",
    verification_id: "verification-1",
    verification_status: "passed",
    verification_summary: "Targeted tests passed.",
    ...overrides,
  };
}
