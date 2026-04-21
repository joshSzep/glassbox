import test from "node:test";
import assert from "node:assert/strict";

import { applyEvent, hydrateFromSnapshot } from "../../src/glassbox/web/static/state.js";
import {
  renderDashboardPanes,
  renderLiveOutputPane,
  renderToolCallsPane,
  renderTurnPane,
} from "../../src/glassbox/web/static/render.js";

test("renderTurnPane shows realistic current-turn details", () => {
  const state = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    last_sequence: 1,
    pending_approval_id: null,
    pending_question_id: null,
    transcript: [],
    active_tool_calls: [
      {
        tool_call_id: "tool-1",
        turn_id: "turn-1",
        tool_name: "apply_patch",
        status: "running",
      },
    ],
    pending_approvals: [],
  });

  const html = renderTurnPane(state);
  assert.match(html, /Current Turn|turn-1|running|Active tools/i);
});

test("renderToolCallsPane and renderLiveOutputPane show realistic entries", () => {
  const snapshotState = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    last_sequence: 5,
    pending_approval_id: null,
    pending_question_id: null,
    transcript: [],
    active_tool_calls: [
      {
        tool_call_id: "tool-1",
        turn_id: "turn-1",
        tool_name: "read_file",
        status: "running",
      },
    ],
    pending_approvals: [],
  });
  const withOutput = applyEvent(snapshotState, {
    session_id: "session-123",
    sequence: 6,
    event_type: "ToolOutputChunk",
    payload: {
      turn_id: "turn-1",
      tool_call_id: "tool-1",
      stream: "stdout",
      chunk: "README.md\n",
    },
  });

  assert.match(renderToolCallsPane(withOutput), /read_file|tool-1/i);
  assert.match(renderLiveOutputPane(withOutput), /stdout|README\.md/i);
});

test("synthetic event stream updates multiple panes together", () => {
  const snapshot = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    last_sequence: 0,
    pending_approval_id: null,
    pending_question_id: null,
    transcript: [],
    active_tool_calls: [],
    pending_approvals: [],
  });

  const events = [
    {
      sequence: 1,
      event_type: "TurnStarted",
      payload: { turn_id: "turn-1", trigger_message_id: "message-1" },
    },
    {
      sequence: 2,
      event_type: "UserMessageReceived",
      payload: { message_id: "message-1", text: "Patch the repo." },
    },
    {
      sequence: 3,
      event_type: "ToolExecutionStarted",
      payload: {
        turn_id: "turn-1",
        tool_call_id: "tool-1",
        tool_name: "apply_patch",
      },
    },
    {
      sequence: 4,
      event_type: "ToolOutputChunk",
      payload: {
        turn_id: "turn-1",
        tool_call_id: "tool-1",
        stream: "stdout",
        chunk: "patched file\n",
      },
    },
    {
      sequence: 5,
      event_type: "ApprovalRequested",
      payload: {
        approval_id: "approval-1",
        turn_id: "turn-1",
        subject: "apply_patch",
        reason: "needs sign-off",
      },
    },
    {
      sequence: 6,
      event_type: "AssistantMessageCompleted",
      payload: {
        message_id: "message-2",
        parts: [{ kind: "text", text: "Waiting for approval." }],
      },
    },
  ];

  const state = events.reduce(
    (current, event) => applyEvent(current, { session_id: "session-123", ...event }),
    snapshot,
  );

  const panes = renderDashboardPanes(state);
  assert.match(panes.transcript, /Patch the repo\.|Waiting for approval\./);
  assert.match(panes.turn, /awaiting_approval|turn-1/);
  assert.match(panes.toolCalls, /apply_patch/);
  assert.match(panes.liveOutput, /patched file/);
  assert.match(panes.approvals, /needs sign-off|Approve/);
  assert.match(panes.eventLog, /ApprovalRequested|ToolOutputChunk/);
});
