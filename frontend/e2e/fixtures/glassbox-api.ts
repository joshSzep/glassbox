import type { Page, Route } from "@playwright/test";

type ActionRequest = {
  body: unknown;
  method: string;
  url: string;
};

export type GlassboxApiFixtureState = {
  actions: ActionRequest[];
};

type ProjectionHealthFixture = {
  canonical_last_sequence: number;
  degraded: boolean;
  detail: string | null;
  lag: number;
  projected_last_sequence: number;
  state: string;
};

type ScenarioId =
  | "empty-workspace"
  | "all-queues"
  | "live-session"
  | "historical-session"
  | "failed-session"
  | "pending-approval"
  | "pending-question"
  | "branched-session"
  | "compare-view"
  | "projection-degraded"
  | "artifact-drift";

type ScenarioFixture = {
  childSessionId?: string;
  compareSessionId?: string;
  route: string;
  sessionId?: string;
  summary: string;
};

export const defaultSessionId = "session-1";
export const defaultChildSessionId = "child-1";

export const scenarioFixtures = {
  "empty-workspace": {
    route: "/app",
    summary: "Empty workspace with no current operator work.",
  },
  "all-queues": {
    route: "/app",
    sessionId: defaultSessionId,
    summary: "Workspace overview with mixed action queues and recent sessions.",
  },
  "live-session": {
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Live running session with stream output and active tool context.",
  },
  "historical-session": {
    route: "/app?session=historical-session&queue=historical",
    sessionId: "historical-session",
    summary: "Completed historical snapshot with no expected live stream.",
  },
  "failed-session": {
    route: "/app?session=failed-session&queue=failures",
    sessionId: "failed-session",
    summary: "Failed session with retryable failure summary visible.",
  },
  "pending-approval": {
    route: "/app?session=approval-session&queue=approvals",
    sessionId: "approval-session",
    summary: "Session awaiting explicit tool approval.",
  },
  "pending-question": {
    route: "/app?session=question-session&queue=questions",
    sessionId: "question-session",
    summary: "Session awaiting an ask_user answer.",
  },
  "branched-session": {
    childSessionId: defaultChildSessionId,
    route: `/app?session=${defaultSessionId}&queue=active`,
    sessionId: defaultSessionId,
    summary: "Session with parent and child lineage plus forkable turn evidence.",
  },
  "compare-view": {
    compareSessionId: "parent-session",
    route: `/app?session=${defaultSessionId}&queue=active&compare=parent-session&tab=compare`,
    sessionId: defaultSessionId,
    summary: "Selected session with a parent compare target loaded.",
  },
  "projection-degraded": {
    route: "/app?session=degraded-session&queue=degraded",
    sessionId: "degraded-session",
    summary: "Projection-degraded session whose canonical events remain inspectable.",
  },
  "artifact-drift": {
    route: "/app?session=artifact-session&queue=active",
    sessionId: "artifact-session",
    summary: "Runtime-context snapshot with artifact-backed verification and drift cues.",
  },
} satisfies Record<ScenarioId, ScenarioFixture>;

export type ScreenshotScenarioId = keyof typeof scenarioFixtures;

export async function installGlassboxApiFixture(
  page: Page,
  scenarioId: ScreenshotScenarioId = "live-session",
): Promise<GlassboxApiFixtureState> {
  const state: GlassboxApiFixtureState = { actions: [] };
  const scenario = scenarioFixtures[scenarioId];
  const selectedSessionId = "sessionId" in scenario ? scenario.sessionId : undefined;
  let emittedLiveUpdate = false;

  await page.route("**/healthz", (route) =>
    route.fulfill({
      json: {
        event_transport: {
          degraded: scenarioId === "projection-degraded",
          dropped_events: 0,
          next_actions: [],
          reconnect_mode: "resume with /sessions/{session_id}/events?after=SEQUENCE",
          subscriber_count: selectedSessionId === undefined ? 0 : 1,
        },
        status: "ok",
      },
    }),
  );

  await page.route("**/sessions/aggregate**", (route) => {
    const url = new URL(route.request().url());
    route.fulfill({ json: aggregateFixture(scenarioId, url.searchParams.get("queue")) });
  });

  await page.route("**/sessions/*/events**", (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const isSelectedStream =
      selectedSessionId !== undefined && pathname.endsWith(`/sessions/${selectedSessionId}/events`);
    const shouldEmitLiveUpdate = scenarioId === "live-session" || scenarioId === "pending-question";
    const body =
      isSelectedStream && shouldEmitLiveUpdate && !emittedLiveUpdate
        ? toSseMessage({
            created_at: "2026-04-23T00:00:05Z",
            event_id: "event-5",
            event_type: "AssistantMessageCompleted",
            payload: {
              event_type: "AssistantMessageCompleted",
              message_id: "message-live",
              parts: [{ kind: "text", text: "Live SSE update received by the browser." }],
            },
            sequence: 5,
            session_id: selectedSessionId,
          })
        : "";
    emittedLiveUpdate = emittedLiveUpdate || body.length > 0;

    route.fulfill({
      body,
      headers: {
        "cache-control": "no-cache",
        "content-type": "text/event-stream",
      },
      status: 200,
    });
  });

  for (const sessionId of allFixtureSessionIds()) {
    await page.route(`**/sessions/${sessionId}`, (route) =>
      route.fulfill({ json: sessionSnapshotFixture(sessionId, scenarioId) }),
    );
  }

  await page.route(`**/sessions/${defaultSessionId}/messages`, (route) =>
    recordAction(route, state),
  );
  await page.route(`**/sessions/${defaultSessionId}/questions/question-1`, (route) =>
    recordAction(route, state),
  );
  await page.route(`**/sessions/${defaultSessionId}/approvals/approval-1`, (route) =>
    recordAction(route, state),
  );
  await page.route(`**/sessions/${defaultSessionId}/fork`, (route) =>
    recordAction(route, state, forkResponseFixture()),
  );

  await page.route("**/sessions/*/messages", (route) => recordAction(route, state));
  await page.route("**/sessions/*/questions/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/approvals/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/fork", (route) =>
    recordAction(route, state, forkResponseFixture()),
  );

  return state;
}

export function scenarioRoute(scenarioId: ScreenshotScenarioId): string {
  return scenarioFixtures[scenarioId].route;
}

async function recordAction(
  route: Route,
  state: GlassboxApiFixtureState,
  response: unknown = { status: "ok" },
) {
  state.actions.push({
    body: route.request().postDataJSON(),
    method: route.request().method(),
    url: new URL(route.request().url()).pathname,
  });
  await route.fulfill({ json: response });
}

function aggregateFixture(scenarioId: ScreenshotScenarioId, queue: string | null) {
  const sessions = scenarioId === "empty-workspace" ? [] : aggregateSessions();
  const filteredSessions =
    queue === null
      ? sessions
      : sessions.filter((session) => {
          if (queue === "all") {
            return true;
          }
          return session.queue_memberships.includes(queue);
        });
  const degradedCount = sessions.filter((session) => session.projection_health?.degraded).length;

  return {
    limit: null,
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
      health: "ok",
      health_url: "/healthz",
      pid: 1234,
      session_index_url: "/sessions/aggregate",
      started_at: "2026-04-23T00:00:00Z",
      state: sessions.length === 0 ? "not_running" : "running",
      workspace_root: "/tmp/glassbox-v4-audit",
    },
    sessions: filteredSessions,
    sort: "priority",
    status: null,
  };
}

function aggregateSessions() {
  return [
    sessionSummaryFixture("approval-session", {
      action_needed: true,
      latest_message_summary: "assistant: requested workspace write approval",
      next_action_summary: "Review pending approval",
      pending_approval_id: "approval-1",
      priority_bucket: "approval",
      priority_rank: 1,
      queue_memberships: ["approvals", "action-needed"],
    }),
    sessionSummaryFixture("question-session", {
      action_needed: true,
      latest_message_summary: "assistant: needs branch selection",
      next_action_summary: "Answer pending question",
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
      priority_bucket: "question",
      priority_rank: 2,
      queue_memberships: ["questions", "action-needed"],
    }),
    sessionSummaryFixture("failed-session", {
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
    sessionSummaryFixture("degraded-session", {
      latest_message_summary: "projection health is stale",
      next_action_summary: "Check projection health",
      priority_bucket: "degraded",
      priority_rank: 4,
      projection_health: projectionHealthFixture({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
      queue_memberships: ["degraded"],
    }),
    sessionSummaryFixture(defaultSessionId, {
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
    sessionSummaryFixture("historical-session", {
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

function sessionSummaryFixture(id: string, overrides: Record<string, unknown> = {}) {
  return {
    action_needed: false,
    approval_mode: "confirm",
    branch_label: null,
    can_fork: true,
    child_session_count: 0,
    created_at: "2026-04-23T00:00:00Z",
    cwd: `/tmp/${id}`,
    dashboard_url: null,
    fork_blocked_reason: null,
    forked_from_sequence: null,
    forked_from_turn_id: null,
    has_active_turn: true,
    historical_only: false,
    last_sequence: 4,
    latest_fork_point_sequence: 8,
    latest_fork_point_turn_id: "turn-1",
    latest_message_summary: "user: inspect the operator workflow",
    live_actionable: true,
    model_name: "openai:gpt-5.4",
    next_action_summary: "Send the next prompt",
    parent_session_id: null,
    pending_approval_id: null,
    pending_question_id: null,
    pending_question_text: null,
    priority_bucket: "active",
    priority_rank: 10,
    projection_health: projectionHealthFixture(),
    queue_memberships: ["active"],
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: id,
    status: "running",
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

function sessionSnapshotFixture(id: string, scenarioId: ScreenshotScenarioId) {
  const base = {
    active_tool_calls: [],
    approval_mode: "confirm",
    branch_label: null,
    branchable_turns: [
      {
        created_at: "2026-04-23T00:00:03Z",
        label: "Continue from tool result",
        sequence: 8,
        turn_id: "turn-1",
      },
    ],
    can_fork: true,
    child_sessions: [],
    created_at: "2026-04-23T00:00:00Z",
    current_turn_id: null,
    current_turn_policy_summary: null,
    cwd: `/tmp/${id}`,
    dashboard_url: null,
    fork_blocked_reason: null,
    forked_from_sequence: null,
    forked_from_turn_id: null,
    last_sequence: 4,
    latest_fork_point_sequence: 8,
    latest_fork_point_turn_id: "turn-1",
    model_name: "openai:gpt-5.4",
    parent_session_id: null,
    pending_approval_id: null,
    pending_approvals: [],
    pending_question_id: null,
    pending_question_text: null,
    projection_health: projectionHealthFixture(),
    runtime_context: runtimeContextFixture(),
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: id,
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
    status: "running",
    transcript: transcriptFixture(id),
    turn_metrics: [
      {
        completed_at: "2026-04-23T00:00:08Z",
        failed_tool_call_count: id === "failed-session" ? 1 : 0,
        model_call_count: 1,
        model_duration_ms_total: 2000,
        model_input_tokens_total: 100,
        model_output_tokens_total: 50,
        started_at: "2026-04-23T00:00:02Z",
        succeeded_tool_call_count: id === "failed-session" ? 0 : 1,
        tool_call_count: 1,
        tool_duration_ms_total: 500,
        turn_duration_ms: 6500,
        turn_id: "turn-1",
      },
    ],
    updated_at: "2026-04-23T00:00:01Z",
  };

  if (id === "approval-session") {
    return {
      ...base,
      pending_approval_id: "approval-1",
      pending_approvals: [approvalFixture()],
    };
  }
  if (id === "question-session" || id === defaultSessionId) {
    return {
      ...base,
      pending_approval_id: id === defaultSessionId ? "approval-1" : null,
      pending_approvals: id === defaultSessionId ? [approvalFixture()] : [],
      pending_question_id: "question-1",
      pending_question_text: "Which branch should be inspected?",
    };
  }
  if (id === "failed-session") {
    return {
      ...base,
      session_failure_message: "frontend e2e workflow failed after action submit",
      session_failure_retryable: true,
      status: "failed",
    };
  }
  if (id === "historical-session") {
    return {
      ...base,
      can_fork: false,
      current_turn_id: null,
      fork_blocked_reason: "Historical snapshot has no live fork point.",
      status: "completed",
    };
  }
  if (id === "degraded-session") {
    return {
      ...base,
      projection_health: projectionHealthFixture({
        degraded: true,
        detail: "projection lag",
        lag: 3,
        state: "stale",
      }),
    };
  }
  if (id === "artifact-session") {
    return {
      ...base,
      runtime_context: runtimeContextFixture({
        artifact_context: {
          additional_summary_count: 0,
          summaries: [
            {
              artifact_kind: "eval",
              artifact_path: "evals/impact.json",
              error_count: 0,
              failing_tests: ["frontend operator workflow"],
              failure_count: 1,
              freshness: "current",
              inherited: false,
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
              summary: "Replay context was inherited from the parent branch.",
              summary_kind: "context-drift",
              target_paths: ["docs/tasks-v4.md"],
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
      }),
    };
  }
  if (id === "parent-session") {
    return {
      ...base,
      branch_label: "mainline",
      parent_session_id: null,
      session_id: "parent-session",
      status: "completed",
      transcript: transcriptFixture("parent-session", "Original parent prompt"),
    };
  }
  if (id === defaultChildSessionId) {
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
        ? [
            {
              branch_label: "retry with narrower context",
              latest_message_summary: "assistant: retrying from fork point",
              session_id: defaultChildSessionId,
              status: "running",
              updated_at: "2026-04-23T00:00:04Z",
            },
          ]
        : [],
    parent_session_id: scenarioId === "compare-view" ? "parent-session" : null,
  };
}

function projectionHealthFixture(
  overrides: Partial<ProjectionHealthFixture> = {},
): ProjectionHealthFixture {
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

function runtimeContextFixture(overrides: Record<string, unknown> = {}) {
  return {
    additional_runtime_note_count: 0,
    artifact_context: { additional_summary_count: 0, summaries: [] },
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
    working_set: { additional_item_count: 0, items: [] },
    ...overrides,
  };
}

function transcriptFixture(id: string, firstText = "Inspect the operator workflow") {
  return [
    {
      created_at: "2026-04-23T00:00:00Z",
      message_id: `${id}-message-1`,
      parts: [{ kind: "text", text: firstText }],
      role: "user",
    },
    {
      created_at: "2026-04-23T00:00:01Z",
      message_id: `${id}-message-2`,
      parts: [{ kind: "text", text: "I will inspect the current dashboard state." }],
      role: "assistant",
    },
  ];
}

function approvalFixture() {
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

function forkResponseFixture() {
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

function allFixtureSessionIds(): string[] {
  return [
    defaultSessionId,
    defaultChildSessionId,
    "approval-session",
    "question-session",
    "failed-session",
    "historical-session",
    "degraded-session",
    "artifact-session",
    "parent-session",
  ];
}

function toSseMessage(envelope: Record<string, unknown>): string {
  return `event: ${String(envelope.event_type)}\ndata: ${JSON.stringify(envelope)}\n\n`;
}
