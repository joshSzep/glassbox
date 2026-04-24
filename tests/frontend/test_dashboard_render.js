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
  renderLandingPane,
  renderLiveOutputPane,
  renderMetricsPane,
  renderSelectedSessionSummary,
  renderSessionBrowserPane,
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
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    runtime_context: null,
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
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    runtime_context: null,
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
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    runtime_context: null,
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

test("renderSelectedSessionSummary includes runtime context summary", () => {
  const html = renderSelectedSessionSummary(hydrateFromSnapshot({
    session_id: "session-123",
    status: "running",
    current_turn_id: null,
    model_name: "openai:gpt-5.4",
    cwd: "/tmp/workspace",
    approval_mode: "confirm",
    parent_session_id: null,
    forked_from_turn_id: null,
    forked_from_sequence: null,
    branch_label: null,
    child_sessions: [],
    branchable_turns: [],
    can_fork: false,
    latest_fork_point_turn_id: null,
    latest_fork_point_sequence: null,
    fork_blocked_reason: null,
    dashboard_url: null,
    last_sequence: 0,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    session_failure_message: null,
    session_failure_retryable: null,
    runtime_context: {
      repository_context: {
        workspace_name: "glassbox",
        high_signal_paths: ["README.md", "src/"],
        top_level_directories: ["docs/", "src/"],
        additional_directory_count: 0,
        top_level_files: ["README.md", "pyproject.toml"],
        additional_file_count: 0,
        project_markers: ["python_pyproject", "src_layout"],
      },
      runtime_notes: [
        {
          category: "repo",
          message: "README is the operator entrypoint",
          inherited: true,
          source_session_id: "session-parent",
        },
      ],
      additional_runtime_note_count: 0,
    },
    turn_metrics: [],
    transcript: [],
    active_tool_calls: [],
    pending_approvals: [],
  }));

  assert.match(html, /Runtime context/);
  assert.match(html, /High-signal paths/);
  assert.match(html, /README is the operator entrypoint/);
  assert.match(html, /inherited from session-/);
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
  assert.match(html, /Use this instead of answering a pending question/);
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
  assert.match(html, /It does not start a new prompt/);
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
  assert.match(html, /Resolve the pending approval below/);
  assert.match(html, /before sending a new prompt or answering the model's question/);
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

test("renderSessionBrowserPane shows recent sessions and selected status chips", () => {
  const html = renderSessionBrowserPane({
    sessionId: null,
    selectedSessionId: "session-123",
    sessionIndexState: "loaded",
    sessionIndex: [
      {
        session_id: "session-123",
        status: "awaiting_user_input",
        model_name: "openai:gpt-5.4",
        cwd: "/tmp/workspace",
        approval_mode: "confirm",
        latest_message_summary: "assistant: Which branch should I inspect?",
        pending_question_text: "Which branch should I inspect?",
        next_action_summary: "Answer pending question: Which branch should I inspect?",
        parent_session_id: null,
        branch_label: null,
        child_session_count: 2,
      },
    ],
  });

  assert.match(html, /session-card selected/);
  assert.match(html, /Next action/);
  assert.match(html, /Last activity/);
  assert.match(html, /awaiting user input/);
  assert.match(html, /Which branch should I inspect\?/);
  assert.match(html, /Browser action available/);
  assert.match(html, /2 child sessions/);
  assert.match(html, /openai:gpt-5\.4/);
});

test("renderComposerPane shows fork controls for branchable sessions", () => {
  const html = renderComposerPane({
    status: "completed",
    pendingQuestionId: null,
    pendingQuestionText: null,
    interactionSubmission: { kind: null, state: "idle", error: null },
    canFork: true,
    forkBlockedReason: null,
    latestForkPointTurnId: "turn-2",
    selectedForkTurnId: "turn-2",
    branchableTurns: [
      {
        turn_id: "turn-2",
        sequence: 8,
        created_at: "2026-04-23T00:00:02Z",
        label: "Inspect the repository",
      },
      {
        turn_id: "turn-1",
        sequence: 4,
        created_at: "2026-04-23T00:00:01Z",
        label: "Open the README",
      },
    ],
    forkSubmission: { state: "idle", error: null },
  });

  assert.match(html, /Next Action Unavailable/);
  assert.match(html, /Create Forked Session/);
  assert.match(html, /Inspect the repository \(latest stable\)/);
  assert.match(html, /Open the README/);
  assert.match(html, /Branch label/);
});

test("renderSelectedSessionSummary explains actionable and historical states", () => {
  const awaitingUserInputHtml = renderSelectedSessionSummary({
    sessionId: "session-123",
    status: "awaiting_user_input",
    approvalMode: "confirm",
    pendingQuestionText: "Which branch should I inspect?",
    pendingApprovals: [],
    currentTurn: { turn_id: "turn-1", status: "awaiting_user_input" },
    transcript: [
      {
        message_id: "message-1",
        role: "assistant",
        parts: [{ kind: "text", text: "Which branch should I inspect?" }],
      },
    ],
    sessionFailureMessage: null,
    streamState: "live",
    streamRetryCount: 0,
    streamError: null,
  });
  const awaitingApprovalHtml = renderSelectedSessionSummary({
    sessionId: "session-234",
    status: "awaiting_approval",
    approvalMode: "confirm",
    pendingQuestionText: null,
    pendingApprovals: [
      {
        approval_id: "approval-1",
        subject: "apply_patch",
        reason: "needs sign-off",
      },
    ],
    currentTurn: { turn_id: "turn-2", status: "awaiting_approval" },
    transcript: [
      {
        message_id: "message-1",
        role: "assistant",
        parts: [{ kind: "text", text: "Waiting for approval." }],
      },
    ],
    sessionFailureMessage: null,
    streamState: "reconnecting",
    streamRetryCount: 1,
    streamError: "Snapshot still available while the dashboard retries the live stream.",
  });
  const failedHtml = renderSelectedSessionSummary({
    sessionId: "session-456",
    status: "failed",
    approvalMode: "confirm",
    pendingQuestionText: null,
    pendingApprovals: [],
    currentTurn: null,
    transcript: [
      {
        message_id: "message-2",
        role: "user",
        parts: [{ kind: "text", text: "Inspect the repository" }],
      },
    ],
    sessionFailureMessage: "provider bootstrap failed",
    streamState: "unavailable",
    streamRetryCount: 2,
    streamError: "Showing the last persisted snapshot only. The live stream could not be re-established.",
  });
  const completedHtml = renderSelectedSessionSummary({
    sessionId: "session-789",
    status: "completed",
    approvalMode: "confirm",
    parentSessionId: "session-123",
    forkedFromTurnId: "turn-2",
    forkedFromSequence: 8,
    branchLabel: "alt-path",
    childSessions: [
      {
        session_id: "session-999",
        status: "completed",
        branch_label: "deeper",
        updated_at: "2026-04-23T00:00:03Z",
        latest_message_summary: "assistant: ready",
      },
    ],
    pendingQuestionText: null,
    pendingApprovals: [],
    currentTurn: null,
    transcript: [],
    sessionFailureMessage: null,
    streamState: "historical",
    streamRetryCount: 0,
    streamError: null,
  });

  assert.match(awaitingUserInputHtml, /Selected session/);
  assert.match(awaitingUserInputHtml, /Answer pending question: Which branch should I inspect\?/);
  assert.match(awaitingUserInputHtml, /Browser action available/);
  assert.match(awaitingUserInputHtml, /Live stream connected/);
  assert.match(awaitingUserInputHtml, /assistant: Which branch should I inspect\?/);

  assert.match(awaitingApprovalHtml, /Resolve pending approval/);
  assert.match(awaitingApprovalHtml, /Waiting on approval for apply_patch/);
  assert.match(awaitingApprovalHtml, /Browser action available/);
  assert.match(awaitingApprovalHtml, /Reconnecting live stream/);

  assert.match(failedHtml, /Review failure: provider bootstrap failed/);
  assert.match(failedHtml, /Historical inspection only/);
  assert.match(failedHtml, /Live stream unavailable/);
  assert.match(failedHtml, /persisted snapshot only/);

  assert.match(completedHtml, /Inspect completed session/);
  assert.match(completedHtml, /Historical inspection only/);
  assert.match(completedHtml, /Historical snapshot/);
  assert.match(completedHtml, /Parent session/);
  assert.match(completedHtml, /Open session-/);
  assert.match(completedHtml, /Child sessions/);
  assert.match(completedHtml, /Forked from turn turn-2/);
});

test("renderLandingPane shows no-session, loading, and failed selection states", () => {
  const noSessionHtml = renderLandingPane({
    sessionId: null,
    selectedSessionId: null,
    sessionLoadState: "idle",
    sessionLoadError: null,
    sessionIndex: [],
  });
  const loadingHtml = renderLandingPane({
    sessionId: null,
    selectedSessionId: "session-123",
    sessionLoadState: "loading",
    sessionLoadError: null,
    sessionIndex: [],
  });
  const failedHtml = renderLandingPane({
    sessionId: null,
    selectedSessionId: "missing-session",
    sessionLoadState: "failed",
    sessionLoadError: "Session not found (404)",
    sessionIndex: [],
  });

  assert.match(noSessionHtml, /Choose a recent session/);
  assert.match(loadingHtml, /Opening session-/);
  assert.match(failedHtml, /Session unavailable/);
  assert.match(failedHtml, /Session not found \(404\)/);
  assert.match(failedHtml, /recovered to the session index/);
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
