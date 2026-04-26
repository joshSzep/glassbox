import { expect, type Page, type Route, test } from "@playwright/test";

type ActionRequest = {
  body: unknown;
  method: string;
  url: string;
};

type FixtureState = {
  actions: ActionRequest[];
};

const sessionId = "session-1";
const childSessionId = "child-1";

test("operator can browse queues, open a session, stream updates, and resolve actions", async ({
  page,
}) => {
  const fixture = await installGlassboxApiFixture(page);

  await page.goto("/app");

  await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
  await expect(page.getByRole("link", { name: sessionId })).toBeVisible();

  await page.getByRole("link", { name: /Questions/ }).click();
  await expect(page).toHaveURL(/\/app\/queues\/questions$/);
  await expect(page.getByRole("heading", { name: "Questions sessions" })).toBeVisible();

  await page.getByRole("link", { name: sessionId }).click();
  await expect(page).toHaveURL(/\/app\/sessions\/session-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();
  await expect(page.getByText("Live SSE update received by the browser.")).toBeVisible();

  await page.getByLabel("Continue session").fill("Please continue with the next check");
  await page.getByRole("button", { name: "Send prompt" }).click();

  await page.getByLabel("Answer pending question").fill("Use the main branch");
  await page.getByRole("button", { name: "Submit answer" }).click();

  await page.getByRole("button", { name: "Approve" }).click();
  await page.getByRole("button", { name: "Deny" }).click();

  await page.getByLabel("Create fork").fill("retry with narrower context");
  await page.getByRole("button", { name: "Fork Continue from tool result" }).click();

  await expect(page).toHaveURL(/\/app\/sessions\/child-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: childSessionId })).toBeVisible();

  expect(fixture.actions.map((action) => action.url)).toEqual([
    `/sessions/${sessionId}/messages`,
    `/sessions/${sessionId}/questions/question-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/fork`,
  ]);
  expect(fixture.actions[0]?.body).toEqual({ text: "Please continue with the next check" });
  expect(fixture.actions[1]?.body).toEqual({ answer: "Use the main branch" });
  expect(fixture.actions[2]?.body).toEqual({ decision: "approved" });
  expect(fixture.actions[3]?.body).toEqual({ decision: "denied" });
  expect(fixture.actions[4]?.body).toEqual({
    branch_label: "retry with narrower context",
    turn_id: "turn-1",
  });
});

test("operator console remains reachable in a narrow viewport", async ({ page }) => {
  await installGlassboxApiFixture(page);
  await page.setViewportSize({ height: 844, width: 390 });

  await page.goto("/app");

  await expect(page.getByRole("navigation", { name: "Action queues" })).toBeVisible();
  await expect(page.getByRole("link", { name: sessionId })).toBeVisible();
});

async function installGlassboxApiFixture(page: Page): Promise<FixtureState> {
  const state: FixtureState = { actions: [] };
  let emittedLiveUpdate = false;

  await page.route("**/healthz", (route) =>
    route.fulfill({
      json: {
        event_transport: {
          degraded: false,
          dropped_events: 0,
          next_actions: [],
          reconnect_mode: "resume with /sessions/{session_id}/events?after=SEQUENCE",
          subscriber_count: 1,
        },
        status: "ok",
      },
    }),
  );

  await page.route("**/sessions/aggregate**", (route) => {
    const url = new URL(route.request().url());
    route.fulfill({ json: aggregateFixture(url.searchParams.get("queue")) });
  });

  await page.route("**/sessions/*/events**", (route) => {
    const isSelectedSessionStream = new URL(route.request().url()).pathname.endsWith(
      `/sessions/${sessionId}/events`,
    );
    const body =
      isSelectedSessionStream && !emittedLiveUpdate
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
            session_id: sessionId,
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

  await page.route(`**/sessions/${sessionId}`, (route) =>
    route.fulfill({ json: sessionSnapshotFixture(sessionId) }),
  );
  await page.route(`**/sessions/${childSessionId}`, (route) =>
    route.fulfill({
      json: sessionSnapshotFixture(childSessionId, { parent_session_id: sessionId }),
    }),
  );

  await page.route(`**/sessions/${sessionId}/messages`, (route) => recordAction(route, state));
  await page.route(`**/sessions/${sessionId}/questions/question-1`, (route) =>
    recordAction(route, state),
  );
  await page.route(`**/sessions/${sessionId}/approvals/approval-1`, (route) =>
    recordAction(route, state),
  );
  await page.route(`**/sessions/${sessionId}/fork`, (route) =>
    recordAction(route, state, {
      branch_label: "retry with narrower context",
      child_session_id: childSessionId,
      forked_from_sequence: 8,
      forked_from_turn_id: "turn-1",
      inherited_message_count: 2,
      last_sequence: 8,
      parent_session_id: sessionId,
    }),
  );

  return state;
}

async function recordAction(
  route: Route,
  state: FixtureState,
  response: unknown = { status: "ok" },
) {
  state.actions.push({
    body: route.request().postDataJSON(),
    method: route.request().method(),
    url: new URL(route.request().url()).pathname,
  });
  await route.fulfill({ json: response });
}

function toSseMessage(envelope: Record<string, unknown>): string {
  return `event: ${String(envelope.event_type)}\ndata: ${JSON.stringify(envelope)}\n\n`;
}

function aggregateFixture(queue: string | null) {
  const session = sessionSummaryFixture(sessionId);
  const sessions = queue === null || queue === "questions" ? [session] : [];

  return {
    limit: null,
    projection_health_counts: { degraded: 0, ok: sessions.length, stale: 0, unavailable: 0 },
    queue,
    queue_counts: {
      action_needed: 1,
      active: 1,
      approvals: 1,
      degraded: 0,
      failures: 0,
      historical: 0,
      questions: 1,
      total: 1,
    },
    runtime: {
      dashboard_url: "http://127.0.0.1:3210/app",
      health: "ok",
      health_url: "/healthz",
      pid: 1234,
      session_index_url: "/sessions/aggregate",
      started_at: "2026-04-23T00:00:00Z",
      state: "running",
      workspace_root: "/tmp/glassbox-e2e",
    },
    sessions,
    sort: "priority",
    status: null,
  };
}

function sessionSummaryFixture(id: string) {
  return {
    action_needed: true,
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
    has_active_turn: false,
    historical_only: false,
    last_sequence: 4,
    latest_fork_point_sequence: 8,
    latest_fork_point_turn_id: "turn-1",
    latest_message_summary: "user: inspect the operator workflow",
    live_actionable: true,
    model_name: "openai:gpt-5.4",
    next_action_summary: "Answer pending question",
    parent_session_id: null,
    pending_approval_id: "approval-1",
    pending_question_id: "question-1",
    pending_question_text: "Which branch should be inspected?",
    priority_bucket: "action_needed",
    priority_rank: 1,
    projection_health: projectionHealthFixture(),
    queue_memberships: ["active", "questions", "approvals", "action-needed"],
    session_failure_message: null,
    session_failure_retryable: null,
    session_id: id,
    status: "running",
    updated_at: "2026-04-23T00:00:01Z",
  };
}

function sessionSnapshotFixture(id: string, overrides: Record<string, unknown> = {}) {
  return {
    active_tool_calls: [],
    approval_mode: "confirm",
    branch_label: id === childSessionId ? "retry with narrower context" : null,
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
    transcript: [
      {
        created_at: "2026-04-23T00:00:00Z",
        message_id: "message-1",
        parts: [{ kind: "text", text: "Inspect the operator workflow" }],
        role: "user",
      },
    ],
    turn_metrics: [],
    updated_at: "2026-04-23T00:00:01Z",
    ...overrides,
  };
}

function projectionHealthFixture() {
  return {
    canonical_last_sequence: 4,
    degraded: false,
    detail: null,
    lag: 0,
    projected_last_sequence: 4,
    state: "ok",
  };
}

function runtimeContextFixture() {
  return {
    additional_runtime_note_count: 0,
    artifact_context: { additional_summary_count: 0, summaries: [] },
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
    working_set: { additional_item_count: 0, items: [] },
  };
}
