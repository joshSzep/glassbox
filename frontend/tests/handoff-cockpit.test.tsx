import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HandoffCockpit } from "../components/console/handoff-cockpit";
import type { components } from "../generated/api-types";
import type {
  HandoffActionStatus,
  HandoffDetailState,
  HandoffDraftState,
  HandoffPageState,
} from "../stores/dashboard-stores";

describe("handoff cockpit", () => {
  it("renders readiness, redaction preview, import triage, guidance, and custody actions", () => {
    const markup = renderToStaticMarkup(
      <HandoffCockpit
        action={actionStatus}
        detail={detailState}
        drafts={draftState}
        list={listState}
      />,
    );

    expect(markup).toContain("Handoff Cockpit");
    expect(markup).toContain("pkg-1");
    expect(markup).toContain("Readiness Summary");
    expect(markup).toContain("needs-verification");
    expect(markup).toContain("Redaction Preview And Local-Only Inventory");
    expect(markup).toContain("raw command logs remain local-only");
    expect(markup).toContain("Package, Triage, And Follow-Up");
    expect(markup).toContain("import-for-inspection");
    expect(markup).toContain("Run verification");
    expect(markup).toContain("custody is workflow metadata");
    expect(markup).not.toContain("super-secret-token");
  });

  it("disables import when triage is inspection-only", () => {
    const markup = renderToStaticMarkup(
      <HandoffCockpit
        action={actionStatus}
        detail={{
          ...detailState,
          triage: {
            triage: {
              ...triage.triage,
              can_import_for_inspection: false,
              recommended_disposition: "use-newer-glassbox",
            },
          },
        }}
        drafts={draftState}
        list={listState}
      />,
    );

    expect(markup).toContain("use-newer-glassbox");
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Import<\/button>/);
  });
});

const actionStatus: HandoffActionStatus = { error: null, kind: null, state: "idle" };

const safeCommand: components["schemas"]["HandoffSafeCommand"] = {
  command: ["glassbox", "handoff", "inspect", "handoff.json", "--cwd", "."],
  display: "glassbox handoff inspect handoff.json --cwd .",
  purpose: "Inspect the package before mutation.",
  read_only: true,
  requires_policy_approval: false,
};

const source: components["schemas"]["HandoffSourceRef"] = {
  identifiers: { session_id: "session-1" },
  kind: "session",
  label: "Session handoff",
  primary_id: "session-1",
};

const readiness: components["schemas"]["HandoffReadinessUnifiedResponse"] = {
  readiness: {
    accepted_risks: [],
    confidence: "medium",
    expected_custodian: null,
    freshness: "fresh",
    intent: "review-only",
    limitations: [],
    local_only_evidence: [],
    missing_evidence: [],
    non_claims: ["custody is workflow metadata, not approval"],
    reasons: [
      {
        affected_claim_ids: [],
        evidence: [],
        kind: "missing-evidence",
        limitation: null,
        portable: true,
        summary: "Verification evidence is still needed.",
      },
    ],
    recipient: null,
    safe_first_commands: [safeCommand],
    source,
    stale_evidence: [],
    state: "needs-verification",
    supporting_evidence: [],
  },
};

const redaction = {
  limitations: [],
  posture: "reviewer-safe",
  provider_output_included: false,
  raw_artifacts_included: false,
  raw_diffs_included: false,
  raw_logs_included: false,
  raw_transcript_included: false,
  redacted_categories: ["secret-like-token"],
  redacted_field_count: 1,
  screenshots_included: false,
} satisfies components["schemas"]["HandoffRedactionSummary"];

const preview: components["schemas"]["HandoffPreparePreviewResponse"] = {
  preview: {
    included_sections: ["manifest", "handoff.summary"],
    intent: "review-only",
    local_only: {
      category_counts: { raw_logs: 1 },
      limitations: ["raw command logs remain local-only"],
      safe_local_inspection_commands: [safeCommand],
    },
    local_only_evidence_count: 1,
    local_only_inventory: {
      category_counts: { raw_logs: 1 },
      intent: "review-only",
      inventory_kind: "handoff_local_only_inventory",
      items: [
        {
          affected_claim_ids: [],
          category: "raw_logs",
          count: 1,
          portable: false,
          reason: "local-only-evidence",
          recipient_limitation: "Recipient cannot inspect raw local command logs.",
          safe_local_inspection_commands: [safeCommand],
          summary: "raw command logs remain local-only",
        },
      ],
      limitations: [],
      safe_local_inspection_commands: [safeCommand],
      source,
      total_count: 1,
    },
    omitted_raw_categories: ["raw_logs"],
    package_limitations: [],
    preview_kind: "handoff_redaction_preview",
    profile: null,
    redaction,
    safe_inspection_commands: [safeCommand],
    source,
    unsupported_evidence: [],
  },
};

const triage: components["schemas"]["HandoffImportTriageResponse"] = {
  triage: {
    can_import_for_inspection: true,
    compatibility: {
      missing_optional_sections: [],
      state: "supported",
      supported_sections: ["manifest"],
      unsupported_sections: [],
      unsupported_values: [],
      warnings: [],
    },
    digest: undefined,
    included_evidence: ["handoff.summary"],
    limitations: [],
    local_only_omissions: ["raw_logs"],
    missing_sections: [],
    mutation_performed: false,
    package_id: "pkg-1",
    package_path: "handoff.json",
    recipient_intent: "review-only",
    recommended_disposition: "import-for-inspection",
    redaction,
    safe_first_commands: [safeCommand],
    source: {
      package_format: "session-export",
      package_kind: "session-handoff",
      schema_version: 2,
      source_id: "session-1",
      source_kind: "session",
    },
    unsupported_sections: [],
  },
};

const selectedRecord: components["schemas"]["HandoffRecordResponse"] = {
  action_state: "awaiting-recipient",
  record: {
    archived: false,
    artifact_id: "artifact-handoff-1",
    changeset_id: null,
    compatibility_state: "supported",
    created_at: "2026-04-23T00:00:00Z",
    current_custodian: null,
    custody_state: "proposed",
    decision_by: null,
    decision_reason: null,
    expected_custodian: "reviewer",
    exported_by: "operator",
    follow_up_intent: null,
    imported: false,
    intent: "review-only",
    last_event_type: "HandoffCustodyProposed",
    last_sequence: 1,
    local_only_count: 1,
    note: "ready",
    package_digest: "sha256:package",
    package_id: "pkg-1",
    package_kind: "session-handoff",
    redaction_posture: "reviewer-safe",
    safe_next_actions: ["glassbox handoff inspect handoff.json --cwd ."],
    session_id: "session-1",
    source_id: "session-1",
    source_kind: "session",
    task_id: null,
    updated_at: "2026-04-23T00:05:00Z",
  },
};

const guidance: components["schemas"]["HandoffGuidanceResponse"] = {
  guidance: {
    blockers: [],
    non_claims: ["guidance does not approve continuation"],
    package_id: "pkg-1",
    paths: [
      {
        path_id: "run-verification",
        recommended: true,
        requires_explicit_mutation: false,
        summary: "Verify before continuation.",
        title: "Run verification",
      },
    ],
    safe_commands: [safeCommand],
    session_id: "session-1",
    state: "run-verification",
    summary: "Run verification before continuing.",
  },
};

const detailState: HandoffDetailState = {
  exported: null,
  guidance,
  importResult: null,
  inspect: null,
  preview,
  readiness,
  selected: selectedRecord,
  triage,
};

const draftState: HandoffDraftState = {
  decisionActor: "operator",
  decisionReason: "accept follow-up",
  expectedCustodian: "reviewer",
  exportedBy: "operator",
  followUpIntent: "verification-needed",
  intent: "review-only",
  markdownOutputPath: "",
  note: "",
  outputFormat: "json",
  outputPath: "",
  packagePath: "handoff.json",
  recipient: "reviewer",
  sourceId: "session-1",
  sourceKind: "session",
};

const listState: HandoffPageState = {
  error: null,
  items: [selectedRecord],
  loadState: "loaded",
};
