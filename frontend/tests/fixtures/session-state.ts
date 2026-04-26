import type { components } from "@/generated/api-types";
import type { SseEventEnvelope } from "../../api/sse";

export const defaultSessionId = "session-1";
export const defaultChildSessionId = "child-1";
export const largeTranscriptSessionId = "large-transcript-session";

type CriticalViewport = "desktop" | "narrow-desktop" | "tablet" | "mobile";

type V4ConsoleScenarioFixture = {
  childSessionId?: string;
  compareSessionId?: string;
  criticalViewports: CriticalViewport[];
  expectedOperatorDecision: string;
  mobileOverflowExpectations: string[];
  route: string;
  sessionId?: string;
  summary: string;
};

export const v4ConsoleScenarioFixtures = {
  "empty-workspace": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision: "Confirm there is no current operator work.",
    mobileOverflowExpectations: ["workspace status and empty queue copy wrap without clipping"],
    route: "/app",
    summary: "Empty workspace with no current operator work.",
  },
  "all-queues": {
    criticalViewports: ["desktop", "narrow-desktop", "mobile"],
    expectedOperatorDecision: "Pick the highest-priority pending approval before lower queues.",
    mobileOverflowExpectations: [
      "queue rows expose next action and pending subject as stacked text",
      "no session summary requires horizontal scrolling",
    ],
    route: "/app",
    sessionId: defaultSessionId,
    summary: "Workspace overview with mixed action queues and recent sessions.",
  },
  "live-session": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Continue or answer the live session while preserving stream context.",
    mobileOverflowExpectations: [
      "composer and answer controls remain reachable before passive diagnostics",
      "live output wraps inside the selected-session flow",
    ],
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Live running session with stream output and active tool context.",
  },
  "historical-session": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Inspect a completed session without mistaking it for broken live work.",
    mobileOverflowExpectations: ["historical status and unavailable live actions wrap clearly"],
    route: "/app?session=historical-session&queue=historical",
    sessionId: "historical-session",
    summary: "Completed historical snapshot with no expected live stream.",
  },
  "failed-session": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision: "Decide whether the retryable failure needs inspection or recovery.",
    mobileOverflowExpectations: [
      "failure summary appears before generic evidence",
      "retry guidance wraps without covering queue rows",
    ],
    route: "/app?session=failed-session&queue=failures",
    sessionId: "failed-session",
    summary: "Failed session with retryable failure summary visible.",
  },
  "pending-approval": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Approve or deny the requested workspace write with risk context visible.",
    mobileOverflowExpectations: [
      "approve and deny buttons stay in the primary action area",
      "approval subject, reason, and risk label wrap without clipping",
    ],
    route: "/app?session=approval-session&queue=approvals",
    sessionId: "approval-session",
    summary: "Session awaiting explicit tool approval.",
  },
  "pending-question": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision: "Answer the pending ask_user question before sending new prompts.",
    mobileOverflowExpectations: [
      "question text and answer control stay above transcript/evidence detail",
      "answer copy wraps inside the action card",
    ],
    route: "/app?session=question-session&queue=questions",
    sessionId: "question-session",
    summary: "Session awaiting an ask_user answer.",
  },
  "branched-session": {
    childSessionId: defaultChildSessionId,
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Inspect child lineage and decide whether to fork from the latest boundary.",
    mobileOverflowExpectations: [
      "lineage rows and fork controls wrap without hiding branch labels",
    ],
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Session with parent and child lineage plus forkable turn evidence.",
  },
  "compare-view": {
    compareSessionId: "parent-session",
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Compare the selected session against its parent before branch triage.",
    mobileOverflowExpectations: [
      "compare target and compared transcript remain readable in a stacked layout",
      "long branch labels wrap without pushing actions off screen",
    ],
    route: `/app?session=${defaultSessionId}&queue=active&compare=parent-session&tab=compare`,
    sessionId: defaultSessionId,
    summary: "Selected session with a parent compare target loaded.",
  },
  "projection-degraded": {
    criticalViewports: ["desktop", "mobile"],
    expectedOperatorDecision:
      "Check projection health while preserving confidence in canonical events.",
    mobileOverflowExpectations: [
      "projection detail and repair guidance wrap as advisory health copy",
    ],
    route: "/app?session=degraded-session&queue=degraded",
    sessionId: "degraded-session",
    summary: "Projection-degraded session whose canonical events remain inspectable.",
  },
  "artifact-drift": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Inspect artifact-backed drift cues without treating them as runtime failure.",
    mobileOverflowExpectations: [
      "artifact labels and summaries have visible separation",
      "long artifact and target paths wrap within evidence panels",
    ],
    route: "/app?session=artifact-session&queue=active",
    sessionId: "artifact-session",
    summary: "Runtime-context snapshot with artifact-backed verification and drift cues.",
  },
  "large-transcript": {
    criticalViewports: ["desktop", "tablet", "mobile"],
    expectedOperatorDecision:
      "Keep the current action visible while scanning a noisy live session.",
    mobileOverflowExpectations: [
      "long transcript entries wrap without widening the viewport",
      "active tool output and artifact cues do not bury the pending approval",
    ],
    route: `/app?session=${largeTranscriptSessionId}&queue=active&tab=transcript`,
    sessionId: largeTranscriptSessionId,
    summary:
      "Noisy live session with long transcript, tool output, runtime notes, approvals, and artifacts.",
  },
} satisfies Record<string, V4ConsoleScenarioFixture>;

export type V4ConsoleScenarioId = keyof typeof v4ConsoleScenarioFixtures;

export function makeProjectionHealth(
  overrides: Partial<components["schemas"]["ProjectionHealthResponse"]> = {},
): components["schemas"]["ProjectionHealthResponse"] {
  return {
    canonical_last_sequence: 4,
    degraded: false,
    detail: null,
    lag: 0,
    projected_last_sequence: 4,
    state: "ok",
    ...overrides,
  };
}

export function makeRuntimeContext(
  overrides: Partial<components["schemas"]["RuntimeContextSnapshot"]> = {},
): components["schemas"]["RuntimeContextSnapshot"] {
  return {
    additional_runtime_note_count: 0,
    artifact_context: {
      additional_summary_count: 0,
      summaries: [],
    },
    repository_context: {
      additional_directory_count: 0,
      additional_file_count: 0,
      high_signal_paths: ["src/glassbox"],
      project_markers: ["pyproject.toml"],
      top_level_directories: ["src", "tests"],
      top_level_files: ["README.md"],
      workspace_name: "glassbox",
    },
    runtime_notes: [],
    working_set: {
      additional_item_count: 0,
      items: [],
    },
    ...overrides,
  };
}

export function makeSessionSummary(
  sessionId: string,
  overrides: Partial<components["schemas"]["OperatorSessionSummaryResponse"]> = {},
): components["schemas"]["OperatorSessionSummaryResponse"] {
  return {
    action_needed: false,
    approval_mode: "confirm",
    branch_label: null,
    can_fork: false,
    child_session_count: 0,
    created_at: "2026-04-23T00:00:00Z",
    cwd: `/tmp/${sessionId}`,
    dashboard_url: null,
    fork_blocked_reason: "This session has no completed fork point.",
    forked_from_sequence: null,
    forked_from_turn_id: null,
    has_active_turn: true,
    historical_only: false,
    last_sequence: 4,
    latest_fork_point_sequence: null,
    latest_fork_point_turn_id: null,
    latest_message_summary: "user: Inspect the repository",
    live_actionable: true,
    model_name: "openai:gpt-5.4",
    next_action_summary: "Send the next prompt",
    parent_session_id: null,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    priority_bucket: "active",
    priority_rank: 10,
    projection_health: makeProjectionHealth(),
    queue_memberships: ["active"],
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: sessionId,
    status: "running",
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

export function makeSessionAggregate(
  sessions: components["schemas"]["OperatorSessionSummaryResponse"][] = [],
  overrides: Partial<components["schemas"]["SessionAggregateResponse"]> = {},
): components["schemas"]["SessionAggregateResponse"] {
  return {
    limit: null,
    projection_health_counts: {
      degraded: 0,
      ok: sessions.length,
      stale: 0,
      unavailable: 0,
    },
    queue: "all",
    queue_counts: {
      action_needed: sessions.filter((session) => session.action_needed).length,
      active: sessions.filter((session) => session.queue_memberships.includes("active")).length,
      approvals: sessions.filter((session) => session.queue_memberships.includes("approvals"))
        .length,
      degraded: 0,
      failures: sessions.filter((session) => session.queue_memberships.includes("failures")).length,
      historical: sessions.filter((session) => session.historical_only).length,
      questions: sessions.filter((session) => session.queue_memberships.includes("questions"))
        .length,
      total: sessions.length,
    },
    runtime: {
      dashboard_url: null,
      health: null,
      health_url: null,
      pid: null,
      session_index_url: null,
      started_at: null,
      state: "not_running",
      workspace_root: "/tmp/workspace",
    },
    sessions,
    sort: "priority",
    status: null,
    ...overrides,
  };
}

export function makeSessionSnapshot(
  sessionId: string,
  overrides: Partial<components["schemas"]["SessionSnapshotResponse"]> = {},
): components["schemas"]["SessionSnapshotResponse"] {
  return {
    active_tool_calls: [],
    approval_mode: "confirm",
    branch_label: null,
    branchable_turns: [],
    can_fork: false,
    child_sessions: [],
    created_at: "2026-04-23T00:00:00Z",
    current_turn_id: null,
    current_turn_policy_summary: null,
    cwd: `/tmp/${sessionId}`,
    dashboard_url: null,
    fork_blocked_reason: "This session has no completed fork point.",
    forked_from_sequence: null,
    forked_from_turn_id: null,
    last_sequence: 4,
    latest_fork_point_sequence: null,
    latest_fork_point_turn_id: null,
    model_name: "openai:gpt-5.4",
    parent_session_id: null,
    pending_approval_id: null,
    pending_approvals: [],
    pending_question_id: null,
    pending_question_text: null,
    projection_health: makeProjectionHealth(),
    runtime_context: makeRuntimeContext(),
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: sessionId,
    session_policy_summary: {
      allow_count: 0,
      approve_count: 0,
      blocked_count: 0,
      command_count: 0,
      deny_count: 0,
      highest_risk_level: null,
      read_only_count: 0,
      total_decisions: 0,
      workspace_write_count: 0,
    },
    status: "running",
    transcript: [
      {
        created_at: "2026-04-23T00:00:00Z",
        message_id: "message-1",
        parts: [{ kind: "text", text: "Inspect the repository" }],
        role: "user",
      },
    ],
    turn_metrics: [],
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

export function makeOperatorActionSessionSnapshot(
  sessionId = "session-1",
  overrides: Partial<components["schemas"]["SessionSnapshotResponse"]> = {},
): components["schemas"]["SessionSnapshotResponse"] {
  return makeSessionSnapshot(sessionId, {
    branchable_turns: [
      {
        created_at: "2026-04-23T00:00:03Z",
        label: "Continue from tool result",
        sequence: 8,
        turn_id: "turn-1",
      },
    ],
    can_fork: true,
    fork_blocked_reason: null,
    pending_approval_id: "approval-1",
    pending_approvals: [
      {
        approval_id: "approval-1",
        policy_outcome: "approve",
        policy_risk_level: "medium",
        policy_source_kind: "tool_policy",
        policy_source_label: "workspace-write",
        reason: "writes to the workspace",
        requested_at: "2026-04-23T00:00:05Z",
        subject: "apply patch",
        turn_id: "turn-1",
      },
    ],
    pending_question_id: "question-1",
    pending_question_text: "Which branch should be inspected?",
    ...overrides,
  });
}

export function makeV4ScenarioAggregate(
  scenarioId: V4ConsoleScenarioId,
  queue: string | null = null,
): components["schemas"]["SessionAggregateResponse"] {
  const sessions = scenarioId === "empty-workspace" ? [] : makeV4ScenarioSummaries();
  const filteredSessions =
    queue === null || queue === "all"
      ? sessions
      : sessions.filter((session) => session.queue_memberships.includes(queue));
  const degradedCount = sessions.filter((session) => session.projection_health.degraded).length;

  return makeSessionAggregate(filteredSessions, {
    projection_health_counts: {
      degraded: degradedCount,
      ok: Math.max(sessions.length - degradedCount, 0),
      stale: degradedCount,
      unavailable: 0,
    },
    queue,
    queue_counts: {
      action_needed: sessions.filter((session) => session.action_needed).length,
      active: sessions.filter((session) => session.queue_memberships.includes("active")).length,
      approvals: sessions.filter((session) => session.queue_memberships.includes("approvals"))
        .length,
      degraded: sessions.filter((session) => session.queue_memberships.includes("degraded")).length,
      failures: sessions.filter((session) => session.queue_memberships.includes("failures")).length,
      historical: sessions.filter((session) => session.historical_only).length,
      questions: sessions.filter((session) => session.queue_memberships.includes("questions"))
        .length,
      total: sessions.length,
    },
    runtime: {
      dashboard_url: "http://127.0.0.1:3210/app",
      health: sessions.length === 0 ? null : "ok",
      health_url: "/healthz",
      pid: sessions.length === 0 ? null : 1234,
      session_index_url: "/sessions/aggregate",
      started_at: sessions.length === 0 ? null : "2026-04-23T00:00:00Z",
      state: sessions.length === 0 ? "not_running" : "running",
      workspace_root: "/tmp/glassbox-v4-audit",
    },
  });
}

export function makeV4ScenarioSnapshot(
  sessionId: string,
  scenarioId: V4ConsoleScenarioId = "live-session",
): components["schemas"]["SessionSnapshotResponse"] {
  const base = makeSessionSnapshot(sessionId, {
    branchable_turns: [
      {
        created_at: "2026-04-23T00:00:03Z",
        label: "Continue from tool result",
        sequence: 8,
        turn_id: "turn-1",
      },
    ],
    can_fork: true,
    fork_blocked_reason: null,
    latest_fork_point_sequence: 8,
    latest_fork_point_turn_id: "turn-1",
    runtime_context: makeRuntimeContext({
      repository_context: {
        additional_directory_count: 0,
        additional_file_count: 0,
        high_signal_paths: ["src/glassbox", "frontend/components/console"],
        project_markers: ["pyproject.toml", "frontend/package.json"],
        top_level_directories: ["src", "tests", "frontend"],
        top_level_files: ["README.md"],
        workspace_name: "glassbox",
      },
      runtime_notes: [
        { category: "runtime", inherited: false, message: "Fixture runtime is stable." },
      ],
    }),
    session_policy_summary: {
      allow_count: 0,
      approve_count: 1,
      blocked_count: 0,
      command_count: 1,
      deny_count: 0,
      highest_risk_level: "medium",
      read_only_count: 0,
      total_decisions: 1,
      workspace_write_count: 1,
    },
    transcript: makeV4Transcript(sessionId),
    turn_metrics: [makeV4TurnMetrics(sessionId === "failed-session")],
  });

  if (sessionId === "approval-session") {
    return {
      ...base,
      pending_approval_id: "approval-1",
      pending_approvals: [makeV4Approval()],
    };
  }

  if (sessionId === "question-session" || sessionId === defaultSessionId) {
    return {
      ...base,
      child_sessions:
        sessionId === defaultSessionId &&
        (scenarioId === "branched-session" || scenarioId === "compare-view")
          ? [makeV4ChildSessionSummary()]
          : base.child_sessions,
      pending_approval_id: sessionId === defaultSessionId ? "approval-1" : null,
      pending_approvals: sessionId === defaultSessionId ? [makeV4Approval()] : [],
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
    };
  }

  if (sessionId === "failed-session") {
    return {
      ...base,
      session_failure_message: "frontend e2e workflow failed after action submit",
      session_failure_retryable: true,
      status: "failed",
    };
  }

  if (sessionId === "historical-session") {
    return {
      ...base,
      can_fork: false,
      current_turn_id: null,
      fork_blocked_reason: "Historical snapshot has no live fork point.",
      status: "completed",
    };
  }

  if (sessionId === "degraded-session") {
    return {
      ...base,
      projection_health: makeProjectionHealth({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
    };
  }

  if (sessionId === "artifact-session") {
    return {
      ...base,
      runtime_context: makeRuntimeContext(makeV4ArtifactRuntimeContext()),
    };
  }

  if (sessionId === largeTranscriptSessionId) {
    return {
      ...base,
      active_tool_calls: [makeV4ActiveToolCall()],
      pending_approval_id: "approval-1",
      pending_approvals: [makeV4Approval()],
      runtime_context: makeRuntimeContext({
        ...makeV4ArtifactRuntimeContext(),
        additional_runtime_note_count: 1,
        runtime_notes: [
          { category: "runtime", inherited: false, message: "Tool output is still streaming." },
          {
            category: "artifact",
            inherited: true,
            message: "Inherited eval context may be stale for this branch.",
            source_session_id: "parent-session",
          },
        ],
      }),
      transcript: makeV4LargeTranscript(sessionId),
    };
  }

  if (sessionId === "parent-session") {
    return {
      ...base,
      branch_label: "mainline",
      parent_session_id: null,
      session_id: "parent-session",
      status: "completed",
      transcript: makeV4Transcript("parent-session", "Original parent prompt"),
    };
  }

  if (sessionId === defaultChildSessionId) {
    return {
      ...base,
      branch_label: "retry with narrower context",
      parent_session_id: defaultSessionId,
      session_id: defaultChildSessionId,
    };
  }

  return {
    ...base,
    child_sessions:
      scenarioId === "branched-session" || scenarioId === "compare-view"
        ? [makeV4ChildSessionSummary()]
        : [],
    parent_session_id: scenarioId === "compare-view" ? "parent-session" : null,
  };
}

function makeV4ChildSessionSummary(): components["schemas"]["ChildSessionSummaryResponse"] {
  return {
    branch_label: "retry with narrower context",
    latest_message_summary: "assistant: retrying from fork point",
    session_id: defaultChildSessionId,
    status: "running",
    updated_at: "2026-04-23T00:00:04Z",
  };
}

export function makeV4ScenarioSseEnvelopes(
  scenarioId: V4ConsoleScenarioId,
  sessionId: string,
): SseEventEnvelope[] {
  if (scenarioId === "large-transcript") {
    return [
      makeEnvelope(
        5,
        "ToolOutputChunk",
        {
          chunk: "pnpm test -- --runInBand produced a long validation line that should wrap.",
          stream: "stdout",
          tool_call_id: "tool-1",
          turn_id: "turn-1",
        },
        sessionId,
      ),
      makeEnvelope(
        6,
        "AssistantMessageCompleted",
        {
          message_id: "message-live-large",
          parts: [{ kind: "text", text: "Live output is still arriving while approval waits." }],
        },
        sessionId,
      ),
    ];
  }

  if (scenarioId === "live-session" || scenarioId === "pending-question") {
    return [
      makeEnvelope(
        5,
        "AssistantMessageCompleted",
        {
          message_id: "message-live",
          parts: [{ kind: "text", text: "Live SSE update received by the browser." }],
        },
        sessionId,
      ),
    ];
  }

  return [];
}

export function makeV4ForkResponse(): components["schemas"]["ForkSessionResponse"] {
  return {
    branch_label: "retry with narrower context",
    child_session_id: defaultChildSessionId,
    forked_from_sequence: 8,
    forked_from_turn_id: "turn-1",
    inherited_message_count: 2,
    last_sequence: 8,
    parent_session_id: defaultSessionId,
  };
}

export function v4FixtureSessionIds(): string[] {
  return [
    defaultSessionId,
    defaultChildSessionId,
    "approval-session",
    "question-session",
    "failed-session",
    "historical-session",
    "degraded-session",
    "artifact-session",
    largeTranscriptSessionId,
    "parent-session",
  ];
}

function makeV4ScenarioSummaries(): components["schemas"]["OperatorSessionSummaryResponse"][] {
  return [
    makeSessionSummary("approval-session", {
      action_needed: true,
      latest_message_summary: "assistant: requested workspace write approval",
      next_action_summary: "Review pending approval",
      pending_approval_id: "approval-1",
      priority_bucket: "approval",
      priority_rank: 1,
      queue_memberships: ["approvals", "action-needed"],
    }),
    makeSessionSummary("question-session", {
      action_needed: true,
      latest_message_summary: "assistant: needs branch selection",
      next_action_summary: "Answer pending question",
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
      priority_bucket: "question",
      priority_rank: 2,
      queue_memberships: ["questions", "action-needed"],
    }),
    makeSessionSummary("failed-session", {
      action_needed: true,
      latest_message_summary: "tool: pytest failed",
      next_action_summary: "Inspect retryable failure",
      priority_bucket: "failure",
      priority_rank: 3,
      queue_memberships: ["failures", "action-needed"],
      session_failure_message: "frontend e2e workflow failed after action submit",
      session_failure_retryable: true,
      status: "failed",
    }),
    makeSessionSummary("degraded-session", {
      latest_message_summary: "projection health is stale",
      next_action_summary: "Check projection health",
      priority_bucket: "degraded",
      priority_rank: 4,
      projection_health: makeProjectionHealth({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
      queue_memberships: ["degraded"],
    }),
    makeSessionSummary(defaultSessionId, {
      action_needed: true,
      branch_label: "mainline",
      child_session_count: 1,
      latest_message_summary: "assistant: running frontend validation",
      next_action_summary: "Answer pending question",
      pending_approval_id: "approval-1",
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
      priority_bucket: "action_needed",
      priority_rank: 5,
      queue_memberships: ["active", "questions", "approvals", "action-needed"],
    }),
    makeSessionSummary("artifact-session", {
      latest_message_summary: "artifact summary indicates drift",
      next_action_summary: "Inspect artifact-backed drift evidence",
      priority_bucket: "active",
      priority_rank: 6,
      queue_memberships: ["active"],
    }),
    makeSessionSummary(largeTranscriptSessionId, {
      action_needed: true,
      latest_message_summary: "tool output and transcript are noisy",
      next_action_summary: "Review approval without losing live output context",
      pending_approval_id: "approval-1",
      priority_bucket: "approval",
      priority_rank: 7,
      queue_memberships: ["active", "approvals", "action-needed"],
    }),
    makeSessionSummary("historical-session", {
      has_active_turn: false,
      historical_only: true,
      latest_message_summary: "assistant: completed dashboard migration",
      live_actionable: false,
      next_action_summary: "Review historical snapshot",
      priority_bucket: "historical",
      priority_rank: 9,
      queue_memberships: ["historical"],
      status: "completed",
    }),
  ];
}

function makeV4ActiveToolCall(): components["schemas"]["ActiveToolCallResponse"] {
  return {
    completed_at: null,
    policy_outcome: "approve",
    policy_reason: "writes files during noisy validation",
    policy_risk_level: "workspace_write",
    policy_source_kind: "tool_policy",
    policy_source_label: "workspace-write",
    started_at: "2026-04-23T00:00:02Z",
    status: "running",
    summary: "Run frontend validation with verbose output",
    tool_call_id: "tool-1",
    tool_name: "pnpm test",
    turn_id: "turn-1",
  };
}

function makeV4Approval(): components["schemas"]["PendingApprovalResponse"] {
  return {
    approval_id: "approval-1",
    policy_outcome: "approve",
    policy_risk_level: "medium",
    policy_source_kind: "tool_policy",
    policy_source_label: "workspace-write",
    reason: "writes to the workspace",
    requested_at: "2026-04-23T00:00:05Z",
    subject: "apply patch",
    turn_id: "turn-1",
  };
}

function makeV4ArtifactRuntimeContext(): Partial<components["schemas"]["RuntimeContextSnapshot"]> {
  return {
    artifact_context: {
      additional_summary_count: 0,
      summaries: [
        {
          artifact_kind: "eval",
          artifact_path: "evals/impact.json",
          error_count: 0,
          failing_tests: ["frontend operator workflow"],
          failure_count: 1,
          freshness: "fresh",
          inherited: false,
          provenance_class: "artifact_backed_summary",
          source_tool_name: "glassbox eval run",
          summary: "One browser workflow regressed after dashboard shell changes.",
          summary_kind: "eval-impact",
          target_paths: ["frontend/components/console/workspace-overview.tsx"],
          timed_out: false,
        },
        {
          artifact_kind: "replay",
          artifact_path: "evals/bundles/context.branch-inherited.json",
          error_count: 0,
          failing_tests: [],
          failure_count: 0,
          freshness: "stale",
          inherited: true,
          provenance_class: "artifact_backed_summary",
          source_tool_name: "glassbox replay run",
          summary: "Replay context was inherited from the parent branch.",
          summary_kind: "context-drift",
          target_paths: ["docs/tasks-v4.md"],
          timed_out: false,
        },
        {
          artifact_kind: "eval",
          artifact_path: "evals/coverage.json",
          error_count: 0,
          failing_tests: [],
          failure_count: 0,
          freshness: "fresh",
          inherited: false,
          provenance_class: "artifact_backed_summary",
          source_tool_name: "glassbox eval run",
          summary: "Coverage artifact is current for this branch.",
          summary_kind: "verified-coverage",
          target_paths: ["frontend/components/console/verification-cues.tsx"],
          timed_out: false,
        },
      ],
    },
    working_set: {
      additional_item_count: 0,
      items: [
        {
          inherited: true,
          reasons: ["branch parent"],
          signal_types: ["file"],
          subject: "frontend/components/console/session-inspector.tsx",
          subject_kind: "file",
          summary: "Inherited inspector work from the compared branch.",
        },
      ],
    },
  };
}

function makeV4Transcript(
  sessionId: string,
  firstText = "Inspect the operator workflow",
): components["schemas"]["TranscriptMessageResponse"][] {
  return [
    {
      created_at: "2026-04-23T00:00:00Z",
      message_id: `${sessionId}-message-1`,
      parts: [{ kind: "text", text: firstText }],
      role: "user",
    },
    {
      created_at: "2026-04-23T00:00:01Z",
      message_id: `${sessionId}-message-2`,
      parts: [{ kind: "text", text: "I will inspect the current dashboard state." }],
      role: "assistant",
    },
  ];
}

function makeV4LargeTranscript(
  sessionId: string,
): components["schemas"]["TranscriptMessageResponse"][] {
  return Array.from({ length: 18 }, (_, index) => ({
    created_at: `2026-04-23T00:00:${String(index).padStart(2, "0")}Z`,
    message_id: `${sessionId}-message-${index + 1}`,
    parts: [
      {
        kind: "text",
        text:
          index % 2 === 0
            ? `Operator turn ${index + 1}: keep the approval visible while reading a long transcript entry with file paths like frontend/components/console/session-inspector.tsx.`
            : `Assistant turn ${index + 1}: validation is still streaming, artifact evidence is advisory, and the action rail should not be pushed below diagnostics.`,
      },
    ],
    role: index % 2 === 0 ? "user" : "assistant",
  }));
}

function makeV4TurnMetrics(failedToolCall = false): components["schemas"]["TurnMetricsResponse"] {
  return {
    completed_at: "2026-04-23T00:00:08Z",
    failed_tool_call_count: failedToolCall ? 1 : 0,
    model_call_count: 1,
    model_duration_ms_total: 2000,
    model_input_tokens_total: 100,
    model_output_tokens_total: 50,
    started_at: "2026-04-23T00:00:02Z",
    succeeded_tool_call_count: failedToolCall ? 0 : 1,
    tool_call_count: 1,
    tool_duration_ms_total: 500,
    turn_duration_ms: 6500,
    turn_id: "turn-1",
  };
}

export function makeEnvelope(
  sequence: number,
  eventType: SseEventEnvelope["event_type"],
  payload: Record<string, unknown>,
  sessionId = defaultSessionId,
): SseEventEnvelope {
  return {
    created_at: `2026-04-23T00:00:${String(sequence).padStart(2, "0")}Z`,
    event_id: `event-${sequence}`,
    event_type: eventType,
    payload: { event_type: eventType, ...payload },
    sequence,
    session_id: sessionId,
  };
}
