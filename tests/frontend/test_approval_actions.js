import test from "node:test";
import assert from "node:assert/strict";

import { resolvePendingApproval } from "../../src/glassbox/web/static/approval-actions.js";
import { applyEvent, createState } from "../../src/glassbox/web/static/state.js";

function withPendingApproval() {
  return applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "ApprovalRequested",
    payload: {
      approval_id: "approval-1",
      turn_id: "turn-1",
      subject: "apply_patch",
      reason: "needs sign-off",
    },
  });
}

test("resolvePendingApproval keeps approval visible until SSE confirmation", async () => {
  let state = withPendingApproval();

  const result = await resolvePendingApproval({
    sessionId: "session-123",
    approvalId: "approval-1",
    decision: "approved",
    fetchImpl: async (url, init) => {
      assert.equal(url, "/sessions/session-123/approvals/approval-1");
      assert.equal(init.method, "POST");
      assert.equal(init.body, JSON.stringify({ decision: "approved" }));
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({ status: "ok" }),
      };
    },
    syncState: updater => {
      state = updater(state);
    },
  });

  assert.deepEqual(result, { ok: true });
  assert.equal(state.pendingApprovals.length, 1);
  assert.equal(state.pendingApprovals[0].resolution_state, "submitted");

  state = applyEvent(state, {
    session_id: "session-123",
    sequence: 2,
    event_type: "ApprovalResolved",
    payload: {
      approval_id: "approval-1",
      decision: "approved",
      decided_by: "user",
    },
  });

  assert.equal(state.pendingApprovals.length, 0);
  assert.equal(state.status, "running");
});

test("resolvePendingApproval surfaces server errors and allows retry", async () => {
  let state = withPendingApproval();

  const result = await resolvePendingApproval({
    sessionId: "session-123",
    approvalId: "approval-1",
    decision: "denied",
    fetchImpl: async () => ({
      ok: false,
      status: 409,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "approval approval-1 has already been resolved" }),
    }),
    syncState: updater => {
      state = updater(state);
    },
  });

  assert.deepEqual(result, {
    ok: false,
    error: "approval approval-1 has already been resolved",
  });
  assert.equal(state.pendingApprovals[0].resolution_state, "failed");
  assert.equal(
    state.pendingApprovals[0].resolution_error,
    "approval approval-1 has already been resolved",
  );
});
