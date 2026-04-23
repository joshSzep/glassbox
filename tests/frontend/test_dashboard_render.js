import test from "node:test";
import assert from "node:assert/strict";

import {
  applyEvent,
  createState,
  hydrateFromSnapshot,
} from "../../src/glassbox/web/static/state.js";
import {
  renderDashboardPanes,
  renderApprovalsPane,
  renderComposerPane,
  renderLiveOutputPane,
  renderMetricsPane,
  renderToolCallsPane,
  renderTurnPane,
} from "../../src/glassbox/web/static/render.js";

test("renderTurnPane shows realistic current-turn details", () => {
  const state = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    dashboard_url: "http://127.0.0.1:8765",
    last_sequence: 1,
    pending_approval_id: null,
    pending_question_id: null,
    session_failure_message: null,
    session_failure_retryable: null,
    turn_metrics: [
      {
        turn_id: "turn-1",
        model_call_count: 1,
        model_duration_ms_total: 800,
        model_input_tokens_total: 15,
        model_output_tokens_total: 10,
        tool_call_count: 1,
        tool_duration_ms_total: 120,
        succeeded_tool_call_count: 1,
        failed_tool_call_count: 0,
      },
    ],
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
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    dashboard_url: "http://127.0.0.1:8765",
    last_sequence: 5,
    pending_approval_id: null,
    pending_question_id: null,
    session_failure_message: null,
    session_failure_retryable: null,
    turn_metrics: [],
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
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    dashboard_url: "http://127.0.0.1:8765",
    last_sequence: 0,
    pending_approval_id: null,
    pending_question_id: null,
    session_failure_message: null,
    session_failure_retryable: null,
    turn_metrics: [],
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
  assert.match(panes.metrics, /Model latency|Input tokens|Tool runtime/);
  assert.match(panes.toolCalls, /apply_patch/);
  assert.match(panes.liveOutput, /patched file/);
  assert.match(panes.approvals, /needs sign-off|Approve/);
  assert.match(panes.eventLog, /ApprovalRequested|ToolOutputChunk/);
});

test("renderApprovalsPane shows submitted and failed resolution states", () => {
  const state = {
    pendingApprovals: [
      {
        approval_id: "approval-1",
        subject: "apply_patch",
        reason: "needs sign-off",
        resolution_state: "submitted",
        resolution_decision: "approved",
        resolution_error: null,
      },
      {
        approval_id: "approval-2",
        subject: "read_file",
        reason: "conflict",
        resolution_state: "failed",
        resolution_decision: "denied",
        resolution_error: "Request failed (409)",
      },
    ],
  };

  const html = renderApprovalsPane(state);
  assert.match(html, /Decision sent\. Waiting for session update/);
  assert.match(html, /Request failed \(409\)/);
  assert.match(html, /disabled/);
});

test("renderComposerPane shows next-prompt composer while session is running", () => {
  const html = renderComposerPane({
    status: "running",
    pendingQuestionId: null,
    pendingQuestionText: null,
    interactionSubmission: { kind: null, state: "idle", error: null },
  });

  assert.match(html, /Continue Session/);
  assert.match(html, /Send Prompt/);
  assert.match(html, /Type the next prompt/);
});

test("renderComposerPane shows pending-question answer state and errors", () => {
  const html = renderComposerPane({
    status: "awaiting_user_input",
    pendingQuestionId: "question-1",
    pendingQuestionText: "What colour should I use?",
    interactionSubmission: {
      kind: "answer",
      state: "failed",
      error: "unknown question_id: question-1",
    },
  });

  assert.match(html, /Answer Pending Question/);
  assert.match(html, /What colour should I use\?/);
  assert.match(html, /question-1/);
  assert.match(html, /unknown question_id/);
  assert.match(html, /Send Answer/);
});

test("renderComposerPane blocks actions while awaiting approval", () => {
  const html = renderComposerPane({
    status: "awaiting_approval",
    pendingQuestionId: null,
    pendingQuestionText: null,
    interactionSubmission: { kind: null, state: "idle", error: null },
  });

  assert.match(html, /Next Action Unavailable/);
  assert.match(html, /Resolve the pending approval/);
});

test("renderMetricsPane shows aggregated turn metrics", () => {
  const state = {
    turnMetrics: [
      {
        turn_id: "turn-1",
        turn_duration_ms: 2200,
        model_call_count: 2,
        model_duration_ms_total: 1000,
        model_input_tokens_total: 150,
        model_output_tokens_total: 60,
        tool_call_count: 1,
        tool_duration_ms_total: 400,
        succeeded_tool_call_count: 1,
        failed_tool_call_count: 0,
      },
    ],
  };

  const html = renderMetricsPane(state);
  assert.match(html, /Turn duration|2200 ms/);
  assert.match(html, /Model calls|2/);
  assert.match(html, /Input tokens|150/);
  assert.match(html, /Tool runtime|400 ms/);
});

test("renderTurnPane shows session failure details when no current turn exists", () => {
  const html = renderTurnPane({
    status: "failed",
    currentTurn: null,
    sessionFailureMessage: "dashboard wiring failed",
    sessionFailureRetryable: true,
    activeToolCalls: [],
  });

  assert.match(html, /dashboard wiring failed/);
  assert.match(html, /Retryable: yes/);
});

test("live SessionFailed event replaces failed turn details with session failure pane", () => {
  const started = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "TurnStarted",
    payload: {
      turn_id: "turn-1",
      trigger_message_id: "message-1",
    },
  });
  const turnFailed = applyEvent(started, {
    session_id: "session-123",
    sequence: 2,
    event_type: "TurnFailed",
    payload: {
      turn_id: "turn-1",
      error_message: "tool exploded",
    },
  });
  const sessionFailed = applyEvent(turnFailed, {
    session_id: "session-123",
    sequence: 3,
    event_type: "SessionFailed",
    payload: {
      error_message: "runtime wiring failed",
      retryable: false,
    },
  });

  const html = renderTurnPane(sessionFailed);
  assert.doesNotMatch(html, /tool exploded/);
  assert.match(html, /runtime wiring failed/);
  assert.match(html, /Status/);
});
