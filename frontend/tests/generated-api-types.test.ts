import { describe, expect, it } from "vitest";

import type { components, paths } from "../generated/api-types";

describe("generated OpenAPI types", () => {
  it("exposes browser transport request and response contracts", () => {
    type ApprovalResponse =
      paths["/sessions/{session_id}/approvals/{approval_id}"]["post"]["responses"][200]["content"]["application/json"];
    type SnapshotResponse =
      paths["/sessions/{session_id}"]["get"]["responses"][200]["content"]["application/json"];
    type AggregateResponse =
      paths["/sessions/aggregate"]["get"]["responses"][200]["content"]["application/json"];
    type TaskPageResponse = paths["/tasks"]["get"]["responses"][200]["content"]["application/json"];
    type BrowserEvidenceResponse =
      paths["/changesets/{changeset_id}/browser-evidence"]["post"]["responses"][200]["content"]["application/json"];

    const approvalBody: components["schemas"]["ResolveApprovalRequest"] = {
      decision: "approved",
    };
    const accepted: ApprovalResponse = { status: "ok" };
    const snapshotId: keyof SnapshotResponse = "session_id";
    const aggregateKnowledgeKey: keyof AggregateResponse = "knowledge_posture";
    const posture: components["schemas"]["WorkspaceKnowledgePosture"] = {
      cues: [
        {
          authoritative_source: "repository-index.json",
          inspect_commands: ["glassbox repo index status --cwd ."],
          key: "repository-index",
          provenance: [
            {
              label: "Repository index snapshot",
              path: ".glassbox/repository-index.json",
              source_kind: "repository-index",
            },
          ],
          source_count: 1,
          status: "fresh",
          summary: "Repository index is fresh.",
          title: "Repository Index",
        },
      ],
      next_actions: [],
      overall_status: "missing",
    };
    const taskPageKey: keyof TaskPageResponse = "items";
    const browserEvidenceBody: components["schemas"]["BrowserEvidenceAttachRequest"] = {
      actor: "operator",
      browser: "chromium",
      capture_kind: "dashboard_walkthrough",
      environment: "local-dev",
      freshness: "needs_inspection",
      input_method: "keyboard",
      route_label: "/console/changesets",
      screenshot_label: "local screenshot metadata",
      screenshot_media_type: "image/png",
      source_label: "dashboard-local",
      summary: "dashboard rendered evidence references",
      target_kind: "changeset",
      viewport_height: 900,
      viewport_width: 1440,
    };
    const browserEvidenceKey: keyof BrowserEvidenceResponse = "safe_next_actions";

    expect(approvalBody.decision).toBe("approved");
    expect(accepted.status).toBe("ok");
    expect(snapshotId).toBe("session_id");
    expect(aggregateKnowledgeKey).toBe("knowledge_posture");
    expect(posture.overall_status).toBe("missing");
    expect(posture.cues[0]?.provenance?.[0]?.source_kind).toBe("repository-index");
    expect(taskPageKey).toBe("items");
    expect(browserEvidenceBody.capture_kind).toBe("dashboard_walkthrough");
    expect(browserEvidenceKey).toBe("safe_next_actions");
  });
});
