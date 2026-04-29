import type { Page, Route } from "@playwright/test";

import type { components } from "@/generated/api-types";
import {
  defaultChildSessionId,
  defaultSessionId,
  makeV4ForkResponse,
  makeV4ScenarioAggregate,
  makeV4ScenarioSnapshot,
  makeV4ScenarioSseEnvelopes,
  v4ConsoleScenarioFixtures,
  type V4ConsoleScenarioId,
  v4FixtureSessionIds,
} from "../../tests/fixtures/session-state";

type ActionRequest = {
  body: unknown;
  method: string;
  url: string;
};

type BranchCandidate = components["schemas"]["BranchCandidateResponse"];
type BranchSearchSummary = components["schemas"]["BranchSearchSummaryResponse"];
type RepositoryEntry = components["schemas"]["RepositoryIndexEntryResponse"];
type TaskEvent = components["schemas"]["TaskEventResponse"];
type TaskSummary = components["schemas"]["TaskSummaryResponse"];
type WorkspaceMemoryEntry = components["schemas"]["WorkspaceMemoryEntryResponse"];

export type GlassboxApiFixtureState = {
  actions: ActionRequest[];
};

export { defaultChildSessionId, defaultSessionId };

export const scenarioFixtures = v4ConsoleScenarioFixtures;

export type ScreenshotScenarioId = V4ConsoleScenarioId;

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
          last_published_sequence: null,
          max_queue_depth: selectedSessionId === undefined ? 0 : 1,
          next_actions: [],
          queue_capacity: 64,
          queue_pressure: selectedSessionId === undefined ? 0 : 0.016,
          reconnect_hint: "use the client's last observed sequence as the after cursor",
          reconnect_mode: "resume with /sessions/{session_id}/events?after=SEQUENCE",
          state: scenarioId === "projection-degraded" ? "degraded" : "healthy",
          subscriber_count: selectedSessionId === undefined ? 0 : 1,
        },
        status: "ok",
      },
    }),
  );

  await page.route("**/sessions/aggregate**", (route) => {
    const url = new URL(route.request().url());
    route.fulfill({ json: makeV4ScenarioAggregate(scenarioId, url.searchParams.get("queue")) });
  });

  await page.route("**/sessions/*/events**", (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const isSelectedStream =
      selectedSessionId !== undefined && pathname.endsWith(`/sessions/${selectedSessionId}/events`);
    const envelopes =
      isSelectedStream && !emittedLiveUpdate
        ? makeV4ScenarioSseEnvelopes(scenarioId, selectedSessionId)
        : [];
    const body = envelopes.map(toSseMessage).join("");
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

  for (const sessionId of v4FixtureSessionIds()) {
    await page.route(`**/sessions/${sessionId}`, (route) =>
      route.fulfill({ json: makeV4ScenarioSnapshot(sessionId, scenarioId) }),
    );
    await page.route(`**/sessions/${sessionId}/transcript**`, (route) => {
      const snapshot = makeV4ScenarioSnapshot(sessionId, scenarioId);
      route.fulfill({
        json: {
          items: snapshot.transcript,
          page: makeFixturePage(snapshot.transcript.length),
          session_id: sessionId,
        },
      });
    });
    await page.route(`**/sessions/${sessionId}/event-log**`, (route) => {
      route.fulfill({
        json: {
          items: makeFixtureEventLog(sessionId, scenarioId),
          page: makeFixturePage(3),
          session_id: sessionId,
        },
      });
    });
    await page.route(`**/sessions/${sessionId}/turn-metrics**`, (route) => {
      const snapshot = makeV4ScenarioSnapshot(sessionId, scenarioId);
      route.fulfill({
        json: {
          items: snapshot.turn_metrics,
          page: makeFixturePage(snapshot.turn_metrics.length),
          session_id: sessionId,
        },
      });
    });
  }

  await installAutonomyConsoleRoutes(page, state);

  await page.route("**/sessions/*/messages", (route) => recordAction(route, state));
  await page.route("**/sessions/*/questions/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/approvals/*", (route) => recordAction(route, state));
  await page.route("**/sessions/*/fork", (route) =>
    recordAction(route, state, makeV4ForkResponse()),
  );

  return state;
}

async function installAutonomyConsoleRoutes(page: Page, state: GlassboxApiFixtureState) {
  const task = makeTask("task-1");
  const taskEvents = [
    makeTaskEvent("task-event-1", "TaskStepStarted", { summary: "Started edit step" }, 2),
    makeTaskEvent(
      "task-event-2",
      "BudgetDecisionRecorded",
      { decision: "allowed", detail: "one step remains" },
      3,
    ),
    makeTaskEvent(
      "task-event-3",
      "BackgroundJobCreated",
      { job_id: "job-1234567890", summary: "Continuation queued" },
      4,
    ),
  ];
  const memory = makeMemoryEntry("memory-1");
  const repositoryEntry = makeRepositoryEntry("repo-entry-1");
  const branchSearch = makeBranchSearchSummary("search-1");
  const branchCandidate = makeBranchCandidate("candidate-1");

  await page.route("**/tasks**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (!path.startsWith("/tasks")) {
      await route.fallback();
      return;
    }
    if (request.method() === "POST") {
      if (path.endsWith("/continue")) {
        await recordAction(route, state, {
          job: {
            failure_kind: null,
            failure_message: null,
            job_id: "job-1234567890",
            job_type: "task_continuation",
            kind: "background_job",
            progress_message: "queued",
            requested_by: "operator",
            retryable: false,
            session_id: task.session_id,
            state: "queued",
            task_id: task.task_id,
            title: "Continue task-1",
          },
        });
        return;
      }
      await recordAction(route, state, { status: "accepted" });
      return;
    }

    if (path === "/tasks") {
      await route.fulfill({
        json: {
          items: [task],
          page: makeFixturePage(1),
          projection_health: makeProjectionHealth(),
          session_id: null,
        },
      });
      return;
    }
    if (path === `/tasks/${task.task_id}`) {
      await route.fulfill({ json: makeTaskDetail(task) });
      return;
    }
    if (path === `/tasks/${task.task_id}/steps`) {
      await route.fulfill({
        json: {
          items: makeTaskDetail(task).steps,
          page: makeFixturePage(2),
          projection_health: makeProjectionHealth(),
          task_id: task.task_id,
        },
      });
      return;
    }
    if (path === `/tasks/${task.task_id}/events`) {
      await route.fulfill({
        json: {
          items: taskEvents,
          page: makeFixturePage(taskEvents.length),
          projection_health: makeProjectionHealth(),
          task_id: task.task_id,
        },
      });
      return;
    }

    await route.fulfill({ json: { detail: "not found" }, status: 404 });
  });

  await page.route("**/jobs/*/cancel", (route) => recordAction(route, state, { job: null }));

  await page.route("**/memory**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (!path.startsWith("/memory")) {
      await route.fallback();
      return;
    }
    if (request.method() === "POST") {
      if (path.endsWith("/prune-preview")) {
        await recordAction(route, state, {
          entry: memory,
          reason: "dashboard prune preview",
          would_prune: true,
        });
        return;
      }
      await recordAction(route, state, { entry: memory });
      return;
    }
    if (path === "/memory") {
      await route.fulfill({ json: { items: [memory], page: makeFixturePage(1) } });
      return;
    }
    if (path === `/memory/${memory.memory_id}`) {
      await route.fulfill({ json: { entry: memory } });
      return;
    }
    await route.fulfill({ json: { detail: "not found" }, status: 404 });
  });

  await page.route("**/repo/index/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith("/repo/index")) {
      await route.fallback();
      return;
    }
    if (request.method() === "POST" && path === "/repo/index/rebuild") {
      await recordAction(route, state, {
        detail: "queued",
        index: makeRepositoryStatus(),
        job: null,
        mode: "background",
        status: "accepted",
      });
      return;
    }
    if (path === "/repo/index/status") {
      await route.fulfill({ json: makeRepositoryStatus() });
      return;
    }
    if (path === "/repo/index/search") {
      await route.fulfill({
        json: { items: [repositoryEntry], page: makeFixturePage(1), query: "glassbox" },
      });
      return;
    }
    if (path === `/repo/index/entries/${repositoryEntry.entry_id}`) {
      await route.fulfill({ json: { entry: repositoryEntry } });
      return;
    }
    await route.fulfill({ json: { detail: "not found" }, status: 404 });
  });

  await page.route("**/branch-searches**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith("/branch-searches")) {
      await route.fallback();
      return;
    }
    if (request.method() === "POST") {
      await recordAction(route, state, { candidate: branchCandidate, status: "accepted" });
      return;
    }
    if (path === "/branch-searches") {
      await route.fulfill({ json: { items: [branchSearch] } });
      return;
    }
    if (path === `/branch-searches/${branchSearch.search_id}`) {
      await route.fulfill({ json: { candidates: [branchCandidate], search: branchSearch } });
      return;
    }
    await route.fulfill({ json: { detail: "not found" }, status: 404 });
  });
}

function makeFixturePage(returnedCount: number) {
  return {
    cursor: 0,
    has_more: false,
    limit: 80,
    next_cursor: null,
    returned_count: returnedCount,
  };
}

function makeFixtureEventLog(sessionId: string, scenarioId: ScreenshotScenarioId) {
  return makeV4ScenarioSseEnvelopes(scenarioId, sessionId).map((event) => ({
    created_at: "2026-04-23T00:00:00Z",
    event_id: `event-${event.sequence}`,
    event_type: event.event_type,
    event_version: 1,
    payload: event.payload,
    sequence: event.sequence,
    session_id: sessionId,
  }));
}

function makeProjectionHealth() {
  return {
    canonical_last_sequence: 4,
    degraded: false,
    detail: null,
    estimated_rebuild_event_count: 0,
    lag: 0,
    projected_last_sequence: 4,
    projected_progress_ratio: 1,
    state: "ok",
  };
}

function makeTask(taskId: string): TaskSummary {
  return {
    blocked_detail: "Verification failed on the current step.",
    blocked_reason: "verification_failed",
    current_step_id: "step-2",
    goal: "Make dashboard autonomy visible",
    next_action_summary: "continue from current step",
    session_id: defaultSessionId,
    status: "paused",
    step_count: 2,
    task_id: taskId,
    title: `Task ${taskId}`,
    updated_at: timestamp(2),
  };
}

function makeTaskDetail(task: TaskSummary) {
  return {
    projection_health: makeProjectionHealth(),
    steps: [
      {
        blocked_reason: null,
        description: "Map current dashboard state",
        order: 0,
        status: "completed",
        step_id: "step-1",
        title: "Map state",
      },
      {
        blocked_reason: "verification_failed",
        description: "Add inspector evidence",
        order: 1,
        status: "failed",
        step_id: "step-2",
        title: "Write tests",
      },
    ],
    task,
    verifications: [
      {
        check_name: "frontend tests",
        status: "passed",
        step_id: "step-1",
        summary: "unit pass",
        verification_id: "verification-1",
      },
      {
        check_name: "typecheck",
        status: "failed",
        step_id: "step-2",
        summary: "type gap",
        verification_id: "verification-2",
      },
    ],
  };
}

function makeTaskEvent(
  eventId: string,
  eventType: string,
  payload: Record<string, unknown>,
  sequence: number,
): TaskEvent {
  return {
    created_at: timestamp(sequence),
    event_id: eventId,
    event_type: eventType,
    payload,
    sequence,
    session_id: defaultSessionId,
    task_id: "task-1",
    turn_id: null,
  };
}

function makeMemoryEntry(memoryId: string): WorkspaceMemoryEntry {
  return {
    confirmed_at: timestamp(1),
    confirmed_by: "operator",
    content: "Use pnpm --dir frontend test for frontend checks.",
    created_at: timestamp(0),
    created_by: "operator",
    import_source: null,
    invalidated_at: null,
    invalidated_by: null,
    invalidation_reason: null,
    kind: "command",
    last_sequence: 4,
    last_used_at: timestamp(2),
    memory_id: memoryId,
    provenance: {
      artifact_id: null,
      note: null,
      session_id: defaultSessionId,
      source_label: null,
      source_sequence: 2,
      source_type: "session_event",
      task_id: "task-1",
      tool_call_id: null,
    },
    prune_reason: null,
    pruned_at: null,
    pruned_by: null,
    redacted: false,
    session_id: defaultSessionId,
    state: "active",
    summary: "Frontend checks use pnpm",
    tags: ["frontend", "tests"],
    updated_at: timestamp(2),
    use_count: 3,
  };
}

function makeRepositoryStatus() {
  return {
    builder_version: "fixture",
    built_at: timestamp(1),
    detail: null,
    entry_count: 1,
    path: "/tmp/glassbox/repo-index.json",
    schema_version: 1,
    source_digest: "digest-fixture",
    status: "fresh",
  };
}

function makeRepositoryEntry(entryId: string): RepositoryEntry {
  return {
    entry_id: entryId,
    kind: "symbol",
    language: "typescript",
    name: "TaskAutonomyConsole",
    path: "frontend/components/console/task-autonomy-console.tsx",
    provenance: [
      {
        content_sha256: null,
        line_end: 120,
        line_start: 1,
        note: null,
        path: "frontend/components/console/task-autonomy-console.tsx",
        source_label: null,
        source_type: "static_analysis",
        tool_name: "fixture-indexer",
      },
    ],
    summary: "Autonomy task queue and plan inspector component.",
    symbol: "TaskAutonomyConsole",
    tags: ["frontend", "autonomy"],
    updated_at: timestamp(2),
  };
}

function makeBranchSearchSummary(searchId: string): BranchSearchSummary {
  return {
    abandoned_reason: null,
    candidate_count: 1,
    created_at: timestamp(0),
    last_sequence: 6,
    objective: "Compare repair options",
    parent_session_id: defaultSessionId,
    search_id: searchId,
    selected_candidate_id: null,
    session_id: defaultSessionId,
    status: "completed",
    task_id: "task-1",
    updated_at: timestamp(3),
  };
}

function makeBranchCandidate(candidateId: string): BranchCandidate {
  return {
    artifact_id: "artifact-1",
    candidate_id: candidateId,
    candidate_session_id: defaultChildSessionId,
    changed_files: ["frontend/components/console/task-autonomy-console.tsx"],
    created_at: timestamp(1),
    last_sequence: 6,
    parent_session_id: defaultSessionId,
    patch_summary: "Updated task controls and evidence labels.",
    policy_budget_summary: "Used one branch attempt from the task budget.",
    residual_risks: ["Needs operator merge review."],
    search_id: "search-1",
    selection_state: null,
    status: "verified",
    strategy_label: "Try minimal fix",
    updated_at: timestamp(3),
    verification_id: "verification-1",
    verification_status: "passed",
    verification_summary: "Targeted checks passed.",
  };
}

function timestamp(offsetSeconds: number): string {
  return new Date(Date.UTC(2026, 3, 23, 0, 0, offsetSeconds)).toISOString();
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

function toSseMessage(envelope: Record<string, unknown>): string {
  return `event: ${String(envelope.event_type)}\ndata: ${JSON.stringify(envelope)}\n\n`;
}
