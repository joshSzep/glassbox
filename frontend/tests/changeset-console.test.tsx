import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChangesetConsole } from "@/components/console/changeset-console";
import type { components } from "@/generated/api-types";

type ChangesetDetail = components["schemas"]["ChangesetDetailResponse"];
type ChangesetSummary = components["schemas"]["ChangesetSummaryResponse"];
type ChangesetVerificationPlan = components["schemas"]["ChangesetVerificationPlanPreviewResponse"];

describe("changeset console", () => {
  it("renders verification readiness states and safe next actions", () => {
    const changeset = makeChangesetSummary("changeset-1");
    const detail = makeChangesetDetail(changeset);
    const markup = renderToStaticMarkup(
      React.createElement(ChangesetConsole, {
        detail: {
          detail,
          error: null,
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
  });
});

function makeChangesetSummary(changesetId: string): ChangesetSummary {
  return {
    accepted_risk_count: 1,
    archived_by: null,
    archived_reason: null,
    branch_candidate_id: null,
    branch_search_id: null,
    changeset_id: changesetId,
    created_at: "2026-05-01T00:00:00Z",
    created_by: "operator",
    last_sequence: 8,
    latest_inventory_artifact_id: "artifact-inventory",
    latest_review_brief_artifact_id: null,
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
    inventory: null,
    inventory_status: {
      current_source_digest: "sha256:current",
      freshness: "fresh",
      reason: null,
      recorded_source_digest: "sha256:current",
      safe_next_actions: [`glassbox changeset refresh ${changeset.changeset_id} --cwd .`],
      stale: false,
    },
    limitations: [],
    readiness: [],
    review_briefs: [],
    safe_next_actions: [`glassbox changeset show ${changeset.changeset_id} --cwd .`],
    sources: [],
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
    retained_artifact_ids: ["artifact-1"],
    safe_next_actions: ["uv run pytest tests/unit"],
    session_id: "session-1",
  };
}
