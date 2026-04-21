import test from "node:test";
import assert from "node:assert/strict";

import {
  applyEvent,
  createState,
  hydrateFromSnapshot,
} from "../../src/glassbox/web/static/state.js";

test("hydrateFromSnapshot copies snapshot fields into dashboard state", () => {
  const state = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    last_sequence: 17,
    pending_approval_id: null,
    pending_question_id: null,
    transcript: [
      {
        message_id: "message-1",
        role: "user",
        parts: [{ kind: "text", text: "hello" }],
      },
    ],
    active_tool_calls: [
      {
        tool_call_id: "tool-1",
        turn_id: "turn-1",
        tool_name: "apply_patch",
        status: "running",
        started_at: null,
      },
    ],
    pending_approvals: [
      {
        approval_id: "approval-1",
        turn_id: "turn-1",
        subject: "apply_patch",
        reason: "needs sign-off",
      },
    ],
  });

  assert.equal(state.sessionId, "session-123");
  assert.equal(state.lastSequence, 17);
  assert.equal(state.modelName, "openai:gpt-5.4");
  assert.equal(state.transcript.length, 1);
  assert.equal(state.activeToolCalls.length, 1);
  assert.equal(state.pendingApprovals.length, 1);
  assert.deepEqual(state.eventLog, []);
});

test("applyEvent appends transcript messages deterministically", () => {
  const initial = createState();
  const withUser = applyEvent(initial, {
    session_id: "session-123",
    sequence: 1,
    event_type: "UserMessageReceived",
    payload: {
      message_id: "message-1",
      text: "hello",
    },
  });
  const withAssistant = applyEvent(withUser, {
    session_id: "session-123",
    sequence: 2,
    event_type: "AssistantMessageCompleted",
    payload: {
      message_id: "message-2",
      parts: [{ kind: "text", text: "hi there" }],
    },
  });

  assert.equal(initial.transcript.length, 0);
  assert.equal(withUser.transcript.length, 1);
  assert.equal(withAssistant.transcript.length, 2);
  assert.equal(withAssistant.transcript[0].role, "user");
  assert.equal(withAssistant.transcript[1].role, "assistant");
  assert.equal(withAssistant.lastSequence, 2);
});

test("applyEvent tracks approval request and resolution", () => {
  const awaitingApproval = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 3,
    event_type: "ApprovalRequested",
    payload: {
      approval_id: "approval-1",
      turn_id: "turn-1",
      subject: "apply_patch",
      reason: "needs sign-off",
    },
  });

  const resolved = applyEvent(awaitingApproval, {
    session_id: "session-123",
    sequence: 4,
    event_type: "ApprovalResolved",
    payload: {
      approval_id: "approval-1",
      decision: "approved",
      decided_by: "user",
    },
  });

  assert.equal(awaitingApproval.status, "awaiting_approval");
  assert.equal(awaitingApproval.pendingApprovalId, "approval-1");
  assert.equal(awaitingApproval.pendingApprovals.length, 1);
  assert.equal(resolved.status, "running");
  assert.equal(resolved.pendingApprovalId, null);
  assert.equal(resolved.pendingApprovals.length, 0);
});

test("applyEvent tracks active tool calls", () => {
  const started = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 5,
    event_type: "ToolExecutionStarted",
    payload: {
      tool_call_id: "tool-1",
      turn_id: "turn-1",
      tool_name: "read_file",
    },
  });
  const completed = applyEvent(started, {
    session_id: "session-123",
    sequence: 6,
    event_type: "ToolExecutionCompleted",
    payload: {
      tool_call_id: "tool-1",
      turn_id: "turn-1",
      success: true,
      summary: "done",
    },
  });

  assert.equal(started.activeToolCalls.length, 1);
  assert.equal(started.activeToolCalls[0].tool_name, "read_file");
  assert.equal(completed.activeToolCalls.length, 0);
});

test("applyEvent preserves event log order and terminal session states", () => {
  const failed = applyEvent(
    applyEvent(createState(), {
      session_id: "session-123",
      sequence: 7,
      event_type: "SessionStarted",
      payload: {
        cwd: "/tmp/workspace",
        model_name: "openai:gpt-5.4",
        approval_mode: "confirm",
      },
    }),
    {
      session_id: "session-123",
      sequence: 8,
      event_type: "SessionFailed",
      payload: {
        error_message: "boom",
      },
    },
  );

  assert.equal(failed.status, "failed");
  assert.deepEqual(failed.eventLog, [
    { sequence: 7, event_type: "SessionStarted" },
    { sequence: 8, event_type: "SessionFailed" },
  ]);
});
