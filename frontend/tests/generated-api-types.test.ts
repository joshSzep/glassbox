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

    const approvalBody: components["schemas"]["ResolveApprovalRequest"] = {
      decision: "approved",
    };
    const accepted: ApprovalResponse = { status: "ok" };
    const snapshotId: keyof SnapshotResponse = "session_id";
    const aggregateKnowledgeKey: keyof AggregateResponse = "knowledge_posture";
    const posture: components["schemas"]["WorkspaceKnowledgePosture"] = {
      cues: [],
      next_actions: [],
      overall_status: "missing",
    };
    const taskPageKey: keyof TaskPageResponse = "items";

    expect(approvalBody.decision).toBe("approved");
    expect(accepted.status).toBe("ok");
    expect(snapshotId).toBe("session_id");
    expect(aggregateKnowledgeKey).toBe("knowledge_posture");
    expect(posture.overall_status).toBe("missing");
    expect(taskPageKey).toBe("items");
  });
});
