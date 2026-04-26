import { describe, expect, it } from "vitest";

import type { components, paths } from "../generated/api-types";

describe("generated OpenAPI types", () => {
  it("exposes browser transport request and response contracts", () => {
    type ApprovalResponse =
      paths["/sessions/{session_id}/approvals/{approval_id}"]["post"]["responses"][200]["content"]["application/json"];
    type SnapshotResponse =
      paths["/sessions/{session_id}"]["get"]["responses"][200]["content"]["application/json"];

    const approvalBody: components["schemas"]["ResolveApprovalRequest"] = {
      decision: "approved",
    };
    const accepted: ApprovalResponse = { status: "ok" };
    const snapshotId: keyof SnapshotResponse = "session_id";

    expect(approvalBody.decision).toBe("approved");
    expect(accepted.status).toBe("ok");
    expect(snapshotId).toBe("session_id");
  });
});
