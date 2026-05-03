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
type BranchCandidateDecisionSupport =
  components["schemas"]["BranchCandidateDecisionSupportResponse"];
type BranchSearchDecisionSupport = components["schemas"]["BranchSearchDecisionSupportResponse"];
type BranchSearchSummary = components["schemas"]["BranchSearchSummaryResponse"];
type ChangesetDetail = components["schemas"]["ChangesetDetailResponse"];
type ChangesetSummary = components["schemas"]["ChangesetSummaryResponse"];
type ChangesetVerificationPlan = components["schemas"]["ChangesetVerificationPlanPreviewResponse"];
type CommitMessageSuggestion = components["schemas"]["CommitMessageSuggestionResponse"];
type CommitReadiness = components["schemas"]["CommitReadinessResponse"];
type RepositoryEntry = components["schemas"]["RepositoryIndexEntryResponse"];
type TaskDetail = components["schemas"]["TaskDetailResponse"];
type TaskEvent = components["schemas"]["TaskEventResponse"];
type TaskSummary = components["schemas"]["TaskSummaryResponse"];
type WorkspaceMemoryEntry = components["schemas"]["WorkspaceMemoryEntryResponse"];

export type GlassboxApiFixtureState = {
  actions: ActionRequest[];
  eventStreamRequests: string[];
};

export { defaultChildSessionId, defaultSessionId };

export const scenarioFixtures = v4ConsoleScenarioFixtures;

export type ScreenshotScenarioId = V4ConsoleScenarioId;

export async function installGlassboxApiFixture(
  page: Page,
  scenarioId: ScreenshotScenarioId = "live-session",
): Promise<GlassboxApiFixtureState> {
  const state: GlassboxApiFixtureState = { actions: [], eventStreamRequests: [] };
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
    state.eventStreamRequests.push(route.request().url());
    const isSelectedStream =
      selectedSessionId !== undefined && pathname.endsWith(`/sessions/${selectedSessionId}/events`);
    const envelopes =
      isSelectedStream && !emittedLiveUpdate
        ? makeV4ScenarioSseEnvelopes(scenarioId, selectedSessionId)
        : [];
    const status = isSelectedStream && !emittedLiveUpdate ? makeStreamStatus(scenarioId) : null;
    const body = [status === null ? "" : toSseMessage(status), ...envelopes.map(toSseMessage)]
      .filter(Boolean)
      .join("");
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
  const rejectedBranchCandidate = makeBranchCandidate("candidate-2", {
    candidate_session_id: "session-child-2",
    patch_summary: "Refactored a wider dashboard review path.",
    residual_risks: ["Broader review surface."],
    selection_state: "rejected",
    strategy_label: "Try broader refactor",
    verification_id: null,
    verification_status: "not_run",
    verification_summary: "No retained verification.",
  });
  const branchDecisionSupport = makeBranchSearchDecisionSupport(branchSearch.search_id);
  const changeset = makeChangesetSummary("changeset-1");

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
      await route.fulfill({
        json: {
          candidates: [branchCandidate, rejectedBranchCandidate],
          decision_support: branchDecisionSupport,
          search: branchSearch,
        },
      });
      return;
    }
    await route.fulfill({ json: { detail: "not found" }, status: 404 });
  });

  await page.route("**/changesets**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith("/changesets")) {
      await route.fallback();
      return;
    }
    if (request.method() === "POST" && path === `/changesets/${changeset.changeset_id}/brief`) {
      await recordAction(route, state, {
        artifact_id: "brief-artifact-2",
        artifact_path: ".glassbox/sessions/session-1/artifacts/brief-artifact-2.json",
        brief: { artifact_kind: "changeset_review_brief" },
        changeset_id: changeset.changeset_id,
        detail: makeChangesetDetail(
          makeChangesetSummary(changeset.changeset_id, {
            latest_review_brief_artifact_id: "brief-artifact-2",
          }),
        ),
        event_sequence: 10,
        limitations: [],
        markdown: null,
        readiness_event_sequence: 11,
        session_id: defaultSessionId,
      });
      return;
    }
    if (request.method() === "POST" && path === `/changesets/${changeset.changeset_id}/refresh`) {
      await recordAction(route, state, {
        changeset_id: changeset.changeset_id,
        detail: makeChangesetDetail(changeset),
        event_sequence: 9,
        status: "refreshed",
      });
      return;
    }
    if (path === "/changesets") {
      await route.fulfill({ json: { items: [changeset] } });
      return;
    }
    if (path === `/changesets/${changeset.changeset_id}/verification-plan`) {
      await route.fulfill({ json: makeChangesetVerificationPlan(changeset.changeset_id) });
      return;
    }
    if (path === `/changesets/${changeset.changeset_id}/commit-readiness`) {
      await route.fulfill({ json: makeCommitReadiness(changeset.changeset_id) });
      return;
    }
    if (path === `/changesets/${changeset.changeset_id}/commit-message`) {
      await route.fulfill({ json: makeCommitMessageSuggestion(changeset.changeset_id) });
      return;
    }
    if (path === `/changesets/${changeset.changeset_id}`) {
      await route.fulfill({ json: makeChangesetDetail(changeset) });
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

function makeStreamStatus(scenarioId: ScreenshotScenarioId) {
  if (scenarioId !== "projection-degraded") {
    return null;
  }
  return {
    after_sequence: 4,
    canonical_last_sequence: 8,
    event_type: "glassbox.stream.status",
    history_truncated: false,
    last_delivered_sequence: 4,
    message: "Projection lag detected while replaying persisted events.",
    projection_health: {
      degraded: true,
      lag: 3,
      state: "stale",
    },
    replayed_count: 0,
    status: "degraded",
    transport: {
      dropped_events: 1,
      last_published_sequence: 8,
      max_queue_depth: 8,
      queue_capacity: 64,
      subscriber_count: 1,
    },
  };
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

function makeTaskDetail(task: TaskSummary): TaskDetail {
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
    verification_ledger: [],
    verification_drift: {
      changed_path_digest: null,
      changed_paths: [],
      diff_summary_command: null,
      docs_only_changed_paths: [],
      error: null,
      generated_changed_paths: [],
      material_changed_paths: [],
      posture: "fresh",
      reason: "workspace has no local drift from HEAD",
      stale_changed_paths: [],
      stale_verification_ids: [],
      task_id: task.task_id,
      workspace_clean: true,
    },
    verification_summary: {
      accepted_risk_count: 0,
      current_posture: "partial",
      failed_count: 1,
      latest_failed_check_name: "typecheck",
      latest_failed_sequence: 5,
      latest_failed_summary: "type gap",
      latest_failed_verification_id: "verification-2",
      latest_success_check_name: "frontend tests",
      latest_success_sequence: 4,
      latest_success_verification_id: "verification-1",
      passed_count: 1,
      running_count: 0,
      skipped_count: 0,
      task_id: task.task_id,
      total_count: 2,
    },
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
    candidate_count: 2,
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

function makeBranchCandidate(
  candidateId: string,
  overrides: Partial<BranchCandidate> = {},
): BranchCandidate {
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
    ...overrides,
  };
}

function makeBranchCandidateDecisionSupport(
  candidateId: string,
  overrides: Partial<BranchCandidateDecisionSupport> = {},
): BranchCandidateDecisionSupport {
  return {
    accepted_risks: [],
    candidate_id: candidateId,
    candidate_session_id: defaultChildSessionId,
    changed_files: [],
    changed_files_summary:
      "Changed-file evidence is not captured in current branch-search projections.",
    cost_estimate: "low",
    evidence: [
      {
        kind: "session",
        session_id: defaultChildSessionId,
        summary: "Candidate session is retained for inspection.",
      },
      {
        kind: "verification",
        summary: "Targeted checks passed.",
        verification_id: "verification-1",
      },
    ],
    objective: "Compare repair options",
    recommended_follow_up_action:
      "Candidate is eligible for operator review and explicit selection.",
    risk_posture: "strong",
    search_id: "search-1",
    selection_state: null,
    status: "verified",
    strategy_label: "Try minimal fix",
    verification_posture: "strong",
    verification_recommendations: [
      {
        commands: ["pnpm --dir frontend test"],
        rationale: "Candidate changed files matched repository verification recommendations.",
        recipe_ids: ["frontend-dashboard"],
        source: "changed-files",
      },
    ],
    ...overrides,
  };
}

function makeBranchSearchDecisionSupport(searchId: string): BranchSearchDecisionSupport {
  return {
    automatic_merge: false,
    candidates: [
      makeBranchCandidateDecisionSupport("candidate-1"),
      makeBranchCandidateDecisionSupport("candidate-2", {
        accepted_risks: ["Broader review surface."],
        candidate_session_id: "session-child-2",
        cost_estimate: "medium",
        recommended_follow_up_action: "Inspect the wider diff before reconsidering.",
        risk_posture: "review",
        selection_state: "rejected",
        strategy_label: "Try broader refactor",
        verification_posture: "missing",
        verification_recommendations: [],
      }),
    ],
    non_goal:
      "Branch search records candidate evidence and operator decisions; it does not automatically merge or mutate parent history.",
    objective: "Compare repair options",
    search_id: searchId,
    selected_candidate_id: null,
  };
}

function makeChangesetSummary(
  changesetId: string,
  overrides: Partial<ChangesetSummary> = {},
): ChangesetSummary {
  return {
    accepted_risk_count: 1,
    archived_by: null,
    archived_reason: null,
    branch_candidate_id: "candidate-1",
    branch_search_id: "search-1",
    changeset_id: changesetId,
    created_at: timestamp(0),
    created_by: "operator",
    last_sequence: 8,
    latest_inventory_artifact_id: "artifact-inventory",
    latest_review_brief_artifact_id: "brief-artifact-1",
    latest_verification_id: "verification-1",
    objective: "Review dashboard changeset evidence",
    replacement_changeset_id: null,
    risk_level: "medium",
    risk_summary: "Runtime, frontend, and tests changed.",
    session_id: defaultSessionId,
    status: "active",
    summary: "Reviewer evidence is assembled for dashboard inspection.",
    task_id: "task-1",
    turn_id: null,
    unresolved_risk_count: 1,
    updated_at: timestamp(4),
    ...overrides,
  };
}

function makeChangesetDetail(changeset: ChangesetSummary): ChangesetDetail {
  const latestBriefId = changeset.latest_review_brief_artifact_id ?? null;
  return {
    changeset,
    inventory: {
      accepted_risk_count: 1,
      artifact_id: "artifact-inventory",
      artifact_schema_version: 1,
      branch_candidate_id: changeset.branch_candidate_id,
      branch_search_id: changeset.branch_search_id,
      changed_path_count: 4,
      changeset_id: changeset.changeset_id,
      freshness: "fresh",
      last_sequence: 6,
      previous_artifact_id: null,
      refreshed_by: "operator",
      risk_level: "medium",
      risk_summary: "Runtime, frontend, and tests changed.",
      session_id: defaultSessionId,
      source_digest: "sha256:current",
      task_id: "task-1",
      turn_id: null,
      unresolved_risk_count: 1,
      updated_at: timestamp(3),
    },
    inventory_status: {
      current_source_digest: "sha256:current",
      freshness: "fresh",
      reason: null,
      recorded_source_digest: "sha256:current",
      safe_next_actions: [`glassbox changeset refresh ${changeset.changeset_id} --cwd .`],
      stale: false,
    },
    limitations: [],
    readiness: [
      {
        accepted_risk_count: 1,
        blockers: [],
        changeset_id: changeset.changeset_id,
        decided_by: "operator",
        inventory_artifact_id: "artifact-inventory",
        last_sequence: 8,
        readiness_kind: "review",
        reason: "deterministic changeset evidence is ready for reviewer inspection",
        review_brief_artifact_id: latestBriefId,
        safe_next_actions: [`glassbox changeset show ${changeset.changeset_id} --cwd .`],
        session_id: defaultSessionId,
        state: "ready",
        task_id: "task-1",
        turn_id: null,
        updated_at: timestamp(4),
        verification_id: "verification-1",
      },
    ],
    command_evidence: {
      artifact_count: 1,
      environment_captured_count: 1,
      failed_count: 0,
      items: [
        {
          environment_captured: true,
          local_only: true,
          output_artifact_id: "artifact-command-1",
          policy_summary: null,
          purpose: "test",
          redaction_notes: ["raw environment is not stored"],
          review_relevance: "verification",
          status: "succeeded",
          summary: "Targeted dashboard checks passed.",
          supports_verification: true,
          task_id: "task-1",
          tool_attempt_id: "attempt-1",
          tool_name: "run_command",
          toolchain_count: 2,
          turn_id: "turn-1",
        },
      ],
      limitations: [],
      risky_count: 0,
      safe_next_actions: [
        `glassbox session tool-attempt inspect attempt-1 --session ${defaultSessionId} --cwd .`,
      ],
      total_count: 1,
      verification_count: 1,
    },
    review_briefs:
      latestBriefId === null
        ? []
        : [
            {
              artifact_id: latestBriefId,
              artifact_schema_version: 1,
              changeset_id: changeset.changeset_id,
              created_at: timestamp(4),
              created_by: "operator",
              inventory_artifact_id: "artifact-inventory",
              last_sequence: 7,
              local_only: true,
              redacted: true,
              render_targets: ["markdown", "json"],
              session_id: defaultSessionId,
              task_id: "task-1",
              turn_id: null,
              verification_id: "verification-1",
            },
          ],
    review_feedback: [
      {
        acceptance_reason: null,
        accepted_by: null,
        archived_by: null,
        archived_reason: null,
        artifact_id: null,
        body: "Keep the dashboard language bounded.",
        changeset_id: changeset.changeset_id,
        created_at: timestamp(4),
        created_by: "operator",
        disposition: "open",
        feedback_id: "feedback-1",
        feedback_kind: "requested_change",
        last_sequence: 8,
        provenance: "reviewer",
        reopened_count: 0,
        replacement_feedback_id: null,
        residual_risk: null,
        resolution_summary: null,
        resolved_by: null,
        reviewer_label: "reviewer-1",
        risk_summary: null,
        session_id: defaultSessionId,
        source_label: "local-review",
        source_session_id: null,
        summary: "Clarify review feedback copy",
        task_id: "task-1",
        turn_id: null,
        updated_at: timestamp(4),
        updated_by: null,
        verification_id: null,
      },
    ],
    review_response_summary: {
      accepted_risk_count: 0,
      blocked_count: 0,
      blockers: [],
      changeset_id: changeset.changeset_id,
      items: [
        {
          blockers: [],
          changed_path_count: 1,
          changeset_id: changeset.changeset_id,
          disposition: "open",
          feedback_id: "feedback-1",
          fixup_inventory_count: 1,
          inventory_freshness: "fresh",
          latest_fixup_inventory_artifact_id: "fixup-artifact-1",
          latest_fixup_inventory_at: timestamp(4),
          latest_fixup_inventory_sequence: 9,
          latest_source_kind: "manual_workspace_edit",
          latest_source_summary: "operator recorded response inventory",
          matched_scope_path_count: 1,
          non_claims: ["review response status is local evidence, not reviewer acceptance"],
          path_summaries: [
            "frontend/components/console/changeset-console.tsx: matches feedback scope",
          ],
          response_state: "responded",
          safe_next_actions: [
            "glassbox changeset feedback show feedback-1 --cwd .",
            `glassbox changeset show ${changeset.changeset_id} --cwd .`,
          ],
          stale: false,
          stale_reason: null,
          summary: "Clarify review feedback copy",
        },
      ],
      non_claims: ["review response status is local evidence, not reviewer acceptance"],
      open_count: 1,
      responded_count: 1,
      safe_next_actions: [
        `glassbox changeset feedback list --changeset ${changeset.changeset_id} --cwd .`,
        `glassbox changeset show ${changeset.changeset_id} --cwd .`,
      ],
      stale_response_count: 0,
      total_feedback_count: 1,
      unresolved_count: 1,
    },
    safe_next_actions: [`glassbox changeset show ${changeset.changeset_id} --cwd .`],
    sources: [
      {
        artifact_id: null,
        branch_candidate_id: "candidate-1",
        branch_search_id: "search-1",
        changeset_id: changeset.changeset_id,
        created_at: timestamp(1),
        last_sequence: 2,
        limitation: null,
        reason: "created from selected branch-search candidate",
        session_id: defaultSessionId,
        source_kind: "branch_search_candidate",
        source_session_id: defaultChildSessionId,
        task_id: "task-1",
        turn_id: null,
        verification_id: "verification-1",
      },
    ],
    verification_posture: {
      accepted_risk_count: 1,
      artifact_id: "artifact-1",
      changeset_id: changeset.changeset_id,
      failed_count: 0,
      last_sequence: 7,
      missing_count: 0,
      session_id: defaultSessionId,
      stale_count: 0,
      state: "passed",
      summary: "Targeted dashboard checks passed.",
      task_id: "task-1",
      turn_id: null,
      updated_at: timestamp(4),
      verification_id: "verification-1",
    },
  };
}

function makeChangesetVerificationPlan(changesetId: string): ChangesetVerificationPlan {
  return {
    changed_paths: [
      "frontend/components/console/changeset-console.tsx",
      "frontend/stores/changeset-store.ts",
    ],
    changeset_id: changesetId,
    eval_profiles: ["commit-smoke"],
    expected_scope: ["frontend/components/console/changeset-console.tsx"],
    inventory_artifact_id: "artifact-inventory",
    inventory_freshness: "fresh",
    limitations: [],
    non_claims: ["verification plan preview does not run commands"],
    readiness: {
      accepted_risk_count: 1,
      failed_count: 0,
      missing_count: 0,
      non_claims: ["verification readiness is advisory review posture, not proof"],
      requirements: [
        {
          artifact_id: "artifact-1",
          blocking: true,
          changed_paths: ["frontend/components/console/changeset-console.tsx"],
          check_name: "frontend checks",
          command: ["pnpm", "run", "test"],
          evidence_summary: "component tests passed",
          kind: "test",
          reason: "retained verification passed",
          requirement_id: "frontend-tests",
          safe_next_actions: ["pnpm run test"],
          source: "changed_paths",
          state: "passed",
          verification_id: "verification-1",
        },
      ],
      safe_next_actions: ["pnpm run test"],
      stale_count: 0,
      state: "passed",
      summary: "verification readiness passed with accepted risk",
    },
    reason_groups: [],
    recommended_commands: ["pnpm run test"],
    recipes: [],
    topology_impacts: [
      {
        component_id: "app:frontend",
        dependency_hints: ["development dependency: vitest"],
        kind: "app",
        limitations: [],
        matched_paths: ["frontend/components/console/changeset-console.tsx"],
        name: "frontend",
        ownership_hints: [],
        recommendation_posture: "fresh",
        root_path: "frontend",
        test_roots: ["frontend/tests", "frontend/e2e"],
        topology_freshness: "fresh",
      },
    ],
    retained_artifact_ids: ["artifact-1"],
    safe_next_actions: ["pnpm run test"],
    session_id: defaultSessionId,
  };
}

function makeCommitReadiness(changesetId: string): CommitReadiness {
  return {
    accepted_risk_count: 1,
    blockers: [],
    changeset_id: changesetId,
    git: {
      ahead: 0,
      behind: 0,
      branch: "main",
      clean: false,
      error: null,
      generated_paths: ["frontend/generated/api-types.ts"],
      policy_sensitive_paths: [],
      staged_path_count: 2,
      staged_paths: [
        "frontend/components/console/changeset-console.tsx",
        "frontend/stores/changeset-store.ts",
      ],
      untracked_paths: [],
      unstaged_paths: [],
      workspace_path_count: 2,
    },
    inventory_artifact_id: "artifact-inventory",
    non_claims: ["this model does not stage files or run git commit"],
    readiness_kind: "commit",
    reason: "changeset has staged changes, fresh evidence, review, and verification",
    review_brief_artifact_id: "brief-artifact-1",
    safe_next_actions: ["git status --short"],
    session_id: defaultSessionId,
    signals: [],
    state: "accepted_with_risk",
    verification_id: "verification-1",
  };
}

function makeCommitMessageSuggestion(changesetId: string): CommitMessageSuggestion {
  return {
    body: [
      "Changeset: changeset-1",
      "Commit readiness: accepted_with_risk - changeset has staged changes",
    ],
    changeset_id: changesetId,
    commit_readiness_state: "accepted_with_risk",
    deterministic: true,
    evidence: [],
    limitations: [],
    message: "Review dashboard changeset evidence\n\n- Commit readiness: accepted_with_risk",
    non_claims: ["commit message is a deterministic suggestion, not a commit action"],
    schema_version: 1,
    session_id: defaultSessionId,
    style: "plain",
    subject: "Review dashboard changeset evidence",
    suggestion_kind: "changeset_commit_message_suggestion",
    suggestion_label: "suggestion_only_not_committed",
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
