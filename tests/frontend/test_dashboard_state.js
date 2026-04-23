import test from "node:test";
import assert from "node:assert/strict";

import {
  applyEvent,
  beginApprovalResolution,
  beginInteractionSubmission,
  confirmApprovalResolution,
  confirmInteractionSubmission,
  createState,
  failApprovalResolution,
  failInteractionSubmission,
  hydrateFromSnapshot,
} from "../../src/glassbox/web/static/state.js";

test("hydrateFromSnapshot copies snapshot fields into dashboard state", () => {
  const state = hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    dashboard_url: "http://127.0.0.1:8765",
    last_sequence: 17,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    turn_metrics: [
      {
        turn_id: "turn-1",
        model_call_count: 1,
        model_duration_ms_total: 800,
        model_input_tokens_total: 12,
        model_output_tokens_total: 7,
        tool_call_count: 1,
        tool_duration_ms_total: 20,
        succeeded_tool_call_count: 1,
        failed_tool_call_count: 0,
      },
    ],
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
  assert.equal(state.dashboardUrl, "http://127.0.0.1:8765");
  assert.equal(state.pendingQuestionText, null);
  assert.equal(state.currentTurn?.turn_id, "turn-1");
  assert.equal(state.turnMetrics.length, 1);
  assert.equal(state.turnMetrics[0].model_duration_ms_total, 800);
  assert.equal(state.transcript.length, 1);
  assert.equal(state.activeToolCalls.length, 1);
  assert.deepEqual(state.liveOutput, []);
  assert.equal(state.pendingApprovals.length, 1);
  assert.deepEqual(state.eventLog, []);
});

test("hydrateFromSnapshot reconstructs awaiting-user-input turns", () => {
  const state = hydrateFromSnapshot({
    session_id: "session-123",
    status: "awaiting_user_input",
    current_turn_id: "turn-ask-1",
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    dashboard_url: "http://127.0.0.1:8765",
    last_sequence: 9,
    pending_approval_id: null,
    pending_question_id: "question-1",
    pending_question_text: "Which branch should I inspect?",
    session_failure_message: null,
    session_failure_retryable: null,
    turn_metrics: [],
    transcript: [],
    active_tool_calls: [],
    pending_approvals: [],
  });

  assert.equal(state.status, "awaiting_user_input");
  assert.equal(state.pendingQuestionId, "question-1");
  assert.equal(state.pendingQuestionText, "Which branch should I inspect?");
  assert.equal(state.currentTurn?.turn_id, "turn-ask-1");
  assert.equal(state.currentTurn?.status, "awaiting_user_input");
});

test("applyEvent tracks current turn lifecycle and failure details", () => {
  const started = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "TurnStarted",
    payload: {
      turn_id: "turn-1",
      trigger_message_id: "message-1",
    },
  });
  const failed = applyEvent(started, {
    session_id: "session-123",
    sequence: 2,
    event_type: "TurnFailed",
    payload: {
      turn_id: "turn-1",
      error_message: "tool exploded",
    },
  });

  assert.equal(started.currentTurn?.turn_id, "turn-1");
  assert.equal(started.currentTurn?.status, "running");
  assert.equal(failed.status, "failed");
  assert.equal(failed.currentTurn?.status, "failed");
  assert.equal(failed.currentTurn?.error_message, "tool exploded");
});

test("applyEvent tracks session-level failure details", () => {
  const withTurn = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 0,
    event_type: "TurnStarted",
    payload: {
      turn_id: "turn-1",
      trigger_message_id: "message-1",
    },
  });
  const failed = applyEvent(withTurn, {
    session_id: "session-123",
    sequence: 1,
    event_type: "SessionFailed",
    payload: {
      error_message: "runtime wiring failed",
      retryable: true,
    },
  });

  assert.equal(failed.status, "failed");
  assert.equal(failed.sessionFailureMessage, "runtime wiring failed");
  assert.equal(failed.sessionFailureRetryable, true);
  assert.equal(failed.currentTurn, null);
  assert.equal(failed.pendingApprovalId, null);
  assert.equal(failed.pendingQuestionId, null);
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

test("approval resolution helpers track submitted and failed browser states", () => {
  const initial = applyEvent(createState(), {
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

  const submitting = beginApprovalResolution(initial, "approval-1", "approved");
  const submitted = confirmApprovalResolution(submitting, "approval-1", "approved");
  const failed = failApprovalResolution(submitting, "approval-1", "conflict");

  assert.equal(submitting.pendingApprovals[0].resolution_state, "submitting");
  assert.equal(submitting.pendingApprovals[0].resolution_decision, "approved");
  assert.equal(submitted.pendingApprovals[0].resolution_state, "submitted");
  assert.equal(failed.pendingApprovals[0].resolution_state, "failed");
  assert.equal(failed.pendingApprovals[0].resolution_error, "conflict");
});

test("interaction submission helpers track submitted and failed browser states", () => {
  const initial = createState();

  const submitting = beginInteractionSubmission(initial, "message");
  const submitted = confirmInteractionSubmission(submitting, "message");
  const failed = failInteractionSubmission(submitting, "answer", "conflict");

  assert.equal(submitting.interactionSubmission.kind, "message");
  assert.equal(submitting.interactionSubmission.state, "submitting");
  assert.equal(submitted.interactionSubmission.state, "submitted");
  assert.equal(failed.interactionSubmission.kind, "answer");
  assert.equal(failed.interactionSubmission.state, "failed");
  assert.equal(failed.interactionSubmission.error, "conflict");
});

test("applyEvent tracks pending question text and clears it on answer", () => {
  const asked = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "UserQuestionAsked",
    payload: {
      question_id: "question-1",
      question: "What colour should I use?",
    },
  });
  const answered = applyEvent(asked, {
    session_id: "session-123",
    sequence: 2,
    event_type: "UserAnswerProvided",
    payload: {
      question_id: "question-1",
      answer: "blue",
    },
  });

  assert.equal(asked.pendingQuestionId, "question-1");
  assert.equal(asked.pendingQuestionText, "What colour should I use?");
  assert.equal(answered.pendingQuestionId, null);
  assert.equal(answered.pendingQuestionText, null);
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
  assert.equal(completed.turnMetrics[0].tool_call_count, 1);
  assert.equal(completed.turnMetrics[0].succeeded_tool_call_count, 1);
});

test("applyEvent aggregates model metrics by turn", () => {
  const started = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 1,
    event_type: "TurnStarted",
    created_at: "2026-04-21T12:00:01Z",
    payload: {
      turn_id: "turn-1",
      trigger_message_id: "message-1",
    },
  });
  const completed = applyEvent(started, {
    session_id: "session-123",
    sequence: 2,
    event_type: "ModelCallCompleted",
    created_at: "2026-04-21T12:00:02Z",
    payload: {
      turn_id: "turn-1",
      input_tokens: 40,
      output_tokens: 18,
      duration_ms: 950,
    },
  });

  assert.equal(completed.turnMetrics.length, 1);
  assert.equal(completed.turnMetrics[0].model_call_count, 1);
  assert.equal(completed.turnMetrics[0].model_duration_ms_total, 950);
  assert.equal(completed.turnMetrics[0].model_input_tokens_total, 40);
  assert.equal(completed.turnMetrics[0].model_output_tokens_total, 18);
});

test("applyEvent buffers live tool output chunks", () => {
  const withOutput = applyEvent(createState(), {
    session_id: "session-123",
    sequence: 9,
    event_type: "ToolOutputChunk",
    payload: {
      turn_id: "turn-1",
      tool_call_id: "tool-1",
      stream: "stdout",
      chunk: "hello\n",
    },
  });

  assert.equal(withOutput.liveOutput.length, 1);
  assert.equal(withOutput.liveOutput[0].stream, "stdout");
  assert.equal(withOutput.liveOutput[0].chunk, "hello\n");
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
