import { describe, expect, it } from "vitest";

import { GlassboxApiError, type GlassboxApiClient } from "../api/client";
import type { SessionEventStreamOptions, SessionStreamState, SseEventEnvelope } from "../api/sse";
import type { components } from "@/generated/api-types";
import {
  createBranchSearchStore,
  createConsoleStore,
  createKnowledgeStore,
  createSessionStore,
  createTaskStore,
} from "../stores/dashboard-stores";
import {
  makeEnvelope,
  makeSessionAggregate,
  makeSessionSnapshot,
  makeSessionSummary,
} from "./fixtures/session-state";

const projectionHealth = {
  canonical_last_sequence: 0,
  degraded: false,
  detail: null,
  estimated_rebuild_event_count: 0,
  lag: 0,
  projected_last_sequence: null,
  projected_progress_ratio: 1,
  state: "ok",
} as const;

const toolAttempt = {
  completed_at: null,
  completed_units: null,
  heartbeat_expires_at: null,
  last_heartbeat_at: null,
  last_sequence: 7,
  message: "retry posture retained",
  output_artifact_id: null,
  retry_classification: "retryable",
  retry_policy_reason: null,
  retry_reason: "read-only tools do not mutate workspace state",
  retry_requires_approval: false,
  safe_to_retry: true,
  session_id: "session-1",
  started_at: null,
  status: "failed",
  task_id: null,
  tool_attempt_id: "attempt-1",
  tool_call_id: "tool-call-1",
  tool_name: "read_file",
  total_units: null,
  turn_id: "turn-1",
} satisfies components["schemas"]["ToolAttemptResponse"];

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
}

function createApiClient(overrides: Partial<GlassboxApiClient> = {}): GlassboxApiClient {
  return {
    forkSession: async () => ({
      branch_label: null,
      child_session_id: "child-1",
      forked_from_sequence: 1,
      forked_from_turn_id: "turn-1",
      inherited_message_count: 1,
      last_sequence: 1,
      parent_session_id: "session-1",
    }),
    getCompareSessionSnapshot: async (sessionId) => makeSessionSnapshot(sessionId),
    getHealth: async () => ({
      event_transport: {
        degraded: false,
        dropped_events: 0,
        last_published_sequence: null,
        max_queue_depth: 0,
        next_actions: [],
        queue_capacity: 64,
        queue_pressure: 0,
        reconnect_hint: "use the client's last observed sequence as the after cursor",
        reconnect_mode: "resume with /sessions/{session_id}/events?after=SEQUENCE",
        state: "healthy",
        subscriber_count: 0,
      },
      status: "ok",
    }),
    getSessionAggregate: async () => makeSessionAggregate([]),
    getSessionArtifactPage: async (sessionId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    getSessionEventLogPage: async (sessionId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    getSessionSnapshot: async (sessionId) => makeSessionSnapshot(sessionId),
    getSessionToolCallPage: async (sessionId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    getSessionTranscriptPage: async (sessionId) => ({
      items: makeSessionSnapshot(sessionId).transcript,
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 1 },
      session_id: sessionId,
    }),
    getSessionTurnMetricsPage: async (sessionId) => ({
      items: makeSessionSnapshot(sessionId).turn_metrics,
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    getTaskDetail: async (taskId) => ({
      projection_health: projectionHealth,
      steps: [],
      task: {
        goal: "Inspect task state",
        next_action_summary: "inspect task",
        session_id: "session-1",
        status: "proposed",
        step_count: 0,
        task_id: taskId,
        title: "Task",
        updated_at: "2025-01-01T00:00:00Z",
      },
      verification_ledger: [],
      verification_drift: makeVerificationDrift(taskId),
      verification_summary: makeVerificationSummary(taskId),
      verifications: [],
    }),
    getTaskEventPage: async (taskId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      projection_health: projectionHealth,
      task_id: taskId,
    }),
    getTaskPage: async () => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      projection_health: null,
      session_id: null,
    }),
    getTaskStepPage: async (taskId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      projection_health: projectionHealth,
      task_id: taskId,
    }),
    getBranchSearchDetail: async (searchId) => makeBranchSearchDetail(searchId),
    getBranchSearchPage: async () => ({ items: [makeBranchSearchSummary("search-1")] }),
    getRepositoryIndexEntryDetail: async (entryId) => ({ entry: makeRepositoryEntry(entryId) }),
    getRepositoryIndexStatus: async () => ({
      built_at: "2026-04-23T00:00:00Z",
      builder_version: "v1",
      detail: null,
      entry_count: 1,
      path: "/tmp/.glassbox/repository-index.json",
      schema_version: 1,
      source_digest: "digest",
      status: "fresh",
    }),
    getWorkspaceMemoryDetail: async (memoryId) => ({ entry: makeMemoryEntry(memoryId) }),
    listWorkspaceMemory: async () => ({
      items: [makeMemoryEntry("memory-1")],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 1 },
    }),
    searchRepositoryIndex: async () => ({
      items: [makeRepositoryEntry("entry-1")],
      page: { cursor: 0, has_more: false, limit: 50, next_cursor: null, returned_count: 1 },
      query: "glassbox",
    }),
    adjustTaskBudget: async () => ({ status: "ok" }),
    approveTaskPlan: async () => ({ status: "ok" }),
    cancelBackgroundJob: async () => ({
      job: {
        job_id: "job-1",
        job_type: "task-continuation-step",
        kind: "mutating_continuation",
        requested_by: "operator",
        retryable: false,
        session_id: "session-1",
        state: "cancellation_requested",
        task_id: "task-1",
        title: "Continue task",
      },
    }),
    cancelTask: async () => ({ status: "ok" }),
    cancelTaskPauseWindow: async () => ({
      pause_window_id: "pause-window-1",
      policy: null,
      reason: "operator override",
      status: "cancelled",
    }),
    markBranchCandidate: async (input) => ({
      candidate: makeBranchCandidate(input.candidateId, { selection_state: input.action }),
      status: input.action,
    }),
    confirmWorkspaceMemory: async (input) => ({ entry: makeMemoryEntry(input.memoryId) }),
    continueTask: async () => ({
      job: {
        job_id: "job-1",
        job_type: "task-continuation-step",
        kind: "mutating_continuation",
        requested_by: "operator",
        retryable: false,
        session_id: "session-1",
        state: "queued",
        task_id: "task-1",
        title: "Continue task",
      },
    }),
    resolveTaskContinuationWindow: async () => ({
      continuation_window: {
        approval_id: "approval-1",
        approved_until: "2026-04-30T12:15:00Z",
        decision: "approved",
        requested_minutes: 15,
      },
      job: {
        job_id: "job-1",
        job_type: "task-continuation-step",
        kind: "mutating_continuation",
        requested_by: "operator",
        retryable: false,
        session_id: "session-1",
        state: "queued",
        task_id: "task-1",
        title: "Continue task",
      },
      status: "approved",
    }),
    scheduleTaskPauseWindow: async () => ({
      pause_window_id: "pause-window-1",
      policy: "before_risky_action",
      reason: "review before mutation",
      status: "scheduled",
    }),
    pauseTask: async () => ({ status: "ok" }),
    previewWorkspaceMemoryPrune: async (input) => ({
      entry: makeMemoryEntry(input.memoryId),
      reason: input.reason ?? null,
      would_prune: true,
    }),
    pruneWorkspaceMemory: async (input) => ({
      entry: makeMemoryEntry(input.memoryId, { state: "pruned" }),
    }),
    rebuildRepositoryIndex: async () => ({
      detail: null,
      index: null,
      job: null,
      mode: "synchronous",
      status: "fresh",
    }),
    resumeTask: async () => ({ status: "ok" }),
    invalidateWorkspaceMemory: async (input) => ({
      entry: makeMemoryEntry(input.memoryId, {
        invalidated_by: "operator",
        invalidated_at: timestamp(2),
        invalidation_reason: input.reason,
        state: "invalidated",
      }),
    }),
    listSessions: async () => [],
    abandonToolAttempt: async () => ({
      message: "abandoned attempt",
      original_attempt: toolAttempt,
      retry_attempt: null,
    }),
    cancelTurn: async () => ({ status: "ok" }),
    resolveApproval: async () => ({ status: "ok" }),
    retryToolAttempt: async () => ({
      message: "retried attempt",
      original_attempt: toolAttempt,
      retry_attempt: { ...toolAttempt, status: "succeeded", tool_attempt_id: "attempt-2" },
    }),
    submitAnswer: async () => ({ status: "ok" }),
    submitMessage: async () => ({ status: "ok" }),
    ...overrides,
  };
}

class FakeStreamHandle {
  closed = false;
  started = false;

  constructor(readonly options: SessionEventStreamOptions) {}

  close(): void {
    this.closed = true;
  }

  start(): void {
    this.started = true;
    this.options.onStateChange?.({
      deliveryMode: "live",
      droppedEvents: 0,
      error: null,
      lastSequence: this.options.afterSequence ?? 0,
      projectionLag: 0,
      replayedCount: 0,
      retryCount: 0,
      status: "live",
    });
  }

  getState(): SessionStreamState {
    return {
      deliveryMode: "live",
      droppedEvents: 0,
      error: null,
      lastSequence: this.options.afterSequence ?? 0,
      projectionLag: 0,
      replayedCount: 0,
      retryCount: 0,
      status: "live",
    };
  }

  emit(envelope: SseEventEnvelope): void {
    this.options.onEnvelope?.(envelope);
  }
}

describe("console store", () => {
  it("loads aggregate session rows and queue filters", async () => {
    const session = makeSessionSummary("session-1", {
      action_needed: true,
      queue_memberships: ["questions", "action-needed"],
    });
    const calls: unknown[] = [];
    const store = createConsoleStore(
      createApiClient({
        getSessionAggregate: async (query) => {
          calls.push(query);
          return makeSessionAggregate([session], { queue: "questions" });
        },
      }),
    );

    await store.getState().selectQueue("questions");

    expect(calls).toEqual([{ queue: "questions", sort: "priority", status: null }]);
    expect(store.getState()).toMatchObject({ loadState: "loaded" });
    expect(store.getState().data.selectedQueue).toBe("questions");
    expect(store.getState().data.sessionIndex[0]?.session_id).toBe("session-1");
    expect(store.getState().data.workspaceAttention).toMatchObject({
      kind: "question",
      target: { kind: "session", queue: "questions", sessionId: "session-1" },
      title: "Answer needed",
    });
  });

  it("derives the highest priority workspace attention summary from aggregate state", async () => {
    const store = createConsoleStore(
      createApiClient({
        getSessionAggregate: async () =>
          makeSessionAggregate(
            [
              makeSessionSummary("failed-session", {
                priority_rank: 3,
                queue_memberships: ["failures", "action-needed"],
                session_failure_message: "pytest failed",
                session_failure_retryable: true,
                status: "failed",
              }),
              makeSessionSummary("approval-session", {
                action_needed: true,
                next_action_summary: "Approve command execution",
                pending_approval_id: "approval-1",
                priority_rank: 1,
                queue_memberships: ["approvals", "action-needed"],
              }),
            ],
            {
              projection_health_counts: { degraded: 1, ok: 1, stale: 1, unavailable: 0 },
              runtime: {
                background_job_abandoned_count: 0,
                background_job_failed_count: 1,
                background_job_retryable_count: 1,
                dashboard_url: null,
                health: "degraded",
                health_url: null,
                pid: 1234,
                session_index_url: null,
                started_at: "2026-04-23T00:00:00Z",
                state: "degraded",
                workspace_root: "/tmp/glassbox",
              },
            },
          ),
      }),
    );

    await store.getState().loadAggregate();

    expect(store.getState().data.workspaceAttention).toEqual({
      actionLabel: "Open session",
      detail: "Approve command execution",
      kind: "approval",
      level: "action",
      target: { kind: "session", queue: "approvals", sessionId: "approval-session" },
      title: "Approval needed",
    });
  });

  it("ignores stale aggregate responses", async () => {
    const first = deferred<ReturnType<typeof makeSessionAggregate>>();
    const second = deferred<ReturnType<typeof makeSessionAggregate>>();
    let callCount = 0;
    const store = createConsoleStore(
      createApiClient({
        getSessionAggregate: async () => (++callCount === 1 ? first.promise : second.promise),
      }),
    );

    const firstLoad = store.getState().loadAggregate({ queue: "active" });
    const secondLoad = store.getState().loadAggregate({ queue: "failures" });
    first.resolve(makeSessionAggregate([makeSessionSummary("stale")], { queue: "active" }));
    second.resolve(makeSessionAggregate([makeSessionSummary("fresh")], { queue: "failures" }));
    await Promise.all([firstLoad, secondLoad]);

    expect(store.getState().data.sessionIndex[0]?.session_id).toBe("fresh");
    expect(store.getState().data.selectedQueue).toBe("failures");
  });
});

describe("task store", () => {
  it("loads task pages and selected task details", async () => {
    const calls: string[] = [];
    const store = createTaskStore(
      createApiClient({
        getTaskDetail: async (taskId) => {
          calls.push(`detail:${taskId}`);
          return {
            projection_health: projectionHealth,
            steps: [
              {
                blocked_reason: null,
                description: "Implement task queue",
                order: 0,
                status: "running",
                step_id: "step-1",
                title: "Build UI",
              },
            ],
            task: makeTaskSummary(taskId),
            verification_ledger: [],
            verification_drift: makeVerificationDrift(taskId),
            verification_summary: makeVerificationSummary(taskId),
            verifications: [],
          };
        },
        getTaskEventPage: async (taskId) => {
          calls.push(`events:${taskId}`);
          return {
            items: [
              {
                created_at: timestamp(1),
                event_id: "event-1",
                event_type: "TaskPlanProposed",
                payload: { summary: "Plan captured" },
                sequence: 1,
                session_id: "session-1",
                task_id: taskId,
                turn_id: null,
              },
            ],
            page: { cursor: 0, has_more: false, limit: 80, next_cursor: null, returned_count: 1 },
            projection_health: projectionHealth,
            task_id: taskId,
          };
        },
        getTaskPage: async () => {
          calls.push("page");
          return {
            items: [makeTaskSummary("task-1")],
            page: { cursor: 0, has_more: false, limit: 200, next_cursor: null, returned_count: 1 },
            projection_health: null,
            session_id: null,
          };
        },
      }),
    );

    await store.getState().loadTaskPage({ queue: "active" });
    await store.getState().selectTask("task-1");

    expect(calls).toEqual(["page", "detail:task-1", "events:task-1"]);
    expect(store.getState().queue.items).toHaveLength(1);
    expect(store.getState().detail.detail?.steps[0]?.title).toBe("Build UI");
    expect(store.getState().detail.events[0]?.event_type).toBe("TaskPlanProposed");
  });

  it("loads additional task events and applies task refresh updates", async () => {
    const store = createTaskStore(
      createApiClient({
        getTaskDetail: async (taskId) => ({
          projection_health: projectionHealth,
          steps: [],
          task: makeTaskSummary(taskId, { status: "active" }),
          verification_ledger: [],
          verification_drift: makeVerificationDrift(taskId),
          verification_summary: makeVerificationSummary(taskId),
          verifications: [],
        }),
        getTaskEventPage: async (taskId, query = {}) => {
          const cursor = query.cursor ?? 0;
          return {
            items: [
              {
                created_at: timestamp(cursor),
                event_id: `event-${cursor}`,
                event_type: "TaskStatusChanged",
                payload: { status: cursor === 0 ? "active" : "completed" },
                sequence: cursor + 1,
                session_id: "session-1",
                task_id: taskId,
                turn_id: null,
              },
            ],
            page: {
              cursor,
              has_more: cursor === 0,
              limit: query.limit ?? 80,
              next_cursor: cursor === 0 ? 1 : null,
              returned_count: 1,
            },
            projection_health: projectionHealth,
            task_id: taskId,
          };
        },
        getTaskPage: async () => ({
          items: [makeTaskSummary("task-1")],
          page: { cursor: 0, has_more: false, limit: 200, next_cursor: null, returned_count: 1 },
          projection_health: null,
          session_id: null,
        }),
      }),
    );

    await store.getState().selectTask("task-1");
    expect(store.getState().detail.eventPage?.has_more).toBe(true);

    await store.getState().loadMoreTaskEvents();
    expect(store.getState().detail.events.map((event) => event.sequence)).toEqual([1, 2]);

    await store.getState().applyTaskUpdate("task-1");
    expect(store.getState().queue.loadState).toBe("loaded");
    expect(store.getState().detail.selectedTaskId).toBe("task-1");
  });

  it("calls task action APIs and refreshes selected task evidence", async () => {
    const calls: string[] = [];
    const store = createTaskStore(
      createApiClient({
        adjustTaskBudget: async () => {
          calls.push("budget");
          return { status: "ok" };
        },
        approveTaskPlan: async () => {
          calls.push("approve");
          return { status: "ok" };
        },
        cancelBackgroundJob: async () => {
          calls.push("cancel-job");
          return {
            job: {
              job_id: "job-1",
              job_type: "task-continuation-step",
              kind: "mutating_continuation",
              requested_by: "operator",
              retryable: false,
              session_id: "session-1",
              state: "cancellation_requested",
              task_id: "task-1",
              title: "Continue task",
            },
          };
        },
        cancelTask: async () => {
          calls.push("cancel-task");
          return { status: "ok" };
        },
        continueTask: async () => {
          calls.push("continue");
          return {
            job: {
              job_id: "job-1",
              job_type: "task-continuation-step",
              kind: "mutating_continuation",
              requested_by: "operator",
              retryable: false,
              session_id: "session-1",
              state: "queued",
              task_id: "task-1",
              title: "Continue task",
            },
          };
        },
        getTaskDetail: async (taskId) => ({
          projection_health: projectionHealth,
          steps: [],
          task: makeTaskSummary(taskId),
          verification_ledger: [],
          verification_drift: makeVerificationDrift(taskId),
          verification_summary: makeVerificationSummary(taskId),
          verifications: [],
        }),
        getTaskEventPage: async (taskId) => ({
          items: [],
          page: { cursor: 0, has_more: false, limit: 80, next_cursor: null, returned_count: 0 },
          projection_health: projectionHealth,
          task_id: taskId,
        }),
        getTaskPage: async () => ({
          items: [makeTaskSummary("task-1")],
          page: { cursor: 0, has_more: false, limit: 200, next_cursor: null, returned_count: 1 },
          projection_health: null,
          session_id: null,
        }),
        pauseTask: async () => {
          calls.push("pause");
          return { status: "ok" };
        },
        resumeTask: async () => {
          calls.push("resume");
          return { status: "ok" };
        },
      }),
    );
    await store.getState().selectTask("task-1");

    await store.getState().approvePlan();
    await store.getState().continueTask();
    await store.getState().pauseTask();
    await store.getState().resumeTask();
    await store.getState().adjustTaskBudget({
      budget: {
        allowed_risk_buckets: ["read_only"],
        checkpoint_approval_required: false,
        checkpoint_interval_seconds: 60,
        max_artifact_bytes: 1000,
        max_branch_attempts: 0,
        max_command_operations: 0,
        max_retry_delay_seconds: 30,
        max_steps: 1,
        max_tool_calls: 1,
        max_unattended_seconds: 60,
        max_verification_attempts: 1,
        max_wall_clock_seconds: 60,
        max_write_operations: 0,
        quiet_window_policy: "allow",
      },
      mode: "inspect",
    });
    await store.getState().cancelBackgroundJob({ jobId: "job-1" });
    await store.getState().cancelTask();

    expect(calls).toEqual([
      "approve",
      "continue",
      "pause",
      "resume",
      "budget",
      "cancel-job",
      "cancel-task",
    ]);
    expect(store.getState().action).toMatchObject({
      kind: "cancel-task",
      state: "succeeded",
    });
    expect(store.getState().queue.loadState).toBe("loaded");
  });

  it("surfaces task page and detail failures", async () => {
    const store = createTaskStore(
      createApiClient({
        getTaskDetail: async () => {
          throw new GlassboxApiError({ kind: "not_found", message: "task missing" });
        },
        getTaskPage: async () => {
          throw new GlassboxApiError({ kind: "network", message: "task API down" });
        },
      }),
    );

    await store.getState().loadTaskPage({ queue: "failed" });
    expect(store.getState().queue).toMatchObject({
      error: "task API down",
      loadState: "failed",
      queue: "failed",
    });

    await store.getState().selectTask("missing");
    expect(store.getState().detail).toMatchObject({
      error: "task missing",
      loadState: "failed",
      selectedTaskId: "missing",
    });
  });
});

describe("branch search store", () => {
  it("loads branch searches, detail, and candidate selection actions", async () => {
    const calls: string[] = [];
    const store = createBranchSearchStore(
      createApiClient({
        getBranchSearchDetail: async (searchId) => {
          calls.push(`detail:${searchId}`);
          return makeBranchSearchDetail(searchId);
        },
        getBranchSearchPage: async () => {
          calls.push("list");
          return { items: [makeBranchSearchSummary("search-1")] };
        },
        markBranchCandidate: async (input) => {
          calls.push(`${input.action}:${input.candidateId}`);
          return {
            candidate: makeBranchCandidate(input.candidateId, {
              selection_state:
                input.action === "select"
                  ? "selected"
                  : input.action === "reject"
                    ? "rejected"
                    : "needs_review",
            }),
            status: input.action,
          };
        },
      }),
    );

    await store.getState().loadBranchSearchPage();
    await store.getState().selectBranchSearch("search-1");
    await store.getState().markCandidate({
      action: "select",
      candidateId: "candidate-1",
      reason: "best verification",
    });

    expect(calls).toEqual([
      "list",
      "detail:search-1",
      "select:candidate-1",
      "detail:search-1",
      "list",
    ]);
    expect(store.getState().page.items[0]?.objective).toBe("Compare repair options");
    expect(store.getState().detail.detail?.candidates[0]?.strategy_label).toBe("Try minimal fix");
    expect(store.getState().action).toMatchObject({
      kind: "select-candidate",
      state: "succeeded",
    });
  });
});

describe("knowledge store", () => {
  it("loads memory filters, detail, and curation actions", async () => {
    const calls: string[] = [];
    const store = createKnowledgeStore(
      createApiClient({
        confirmWorkspaceMemory: async (input) => {
          calls.push(`confirm:${input.memoryId}`);
          return { entry: makeMemoryEntry(input.memoryId) };
        },
        getWorkspaceMemoryDetail: async (memoryId) => {
          calls.push(`detail:${memoryId}`);
          return { entry: makeMemoryEntry(memoryId) };
        },
        invalidateWorkspaceMemory: async (input) => {
          calls.push(`invalidate:${input.reason}`);
          return { entry: makeMemoryEntry(input.memoryId, { state: "invalidated" }) };
        },
        listWorkspaceMemory: async (query = {}) => {
          calls.push(`list:${query.state ?? "all"}:${query.query ?? ""}`);
          return {
            items: [makeMemoryEntry("memory-1", { state: query.state ?? "active" })],
            page: {
              cursor: 0,
              has_more: false,
              limit: query.limit ?? 200,
              next_cursor: null,
              returned_count: 1,
            },
          };
        },
        previewWorkspaceMemoryPrune: async (input) => {
          calls.push("preview");
          return {
            entry: makeMemoryEntry(input.memoryId),
            reason: input.reason ?? null,
            would_prune: true,
          };
        },
        pruneWorkspaceMemory: async (input) => {
          calls.push("prune");
          return { entry: makeMemoryEntry(input.memoryId, { state: "pruned" }) };
        },
      }),
    );

    await store.getState().loadMemoryPage({ filter: "stale", query: "pytest" });
    await store.getState().selectMemory("memory-1");
    await store.getState().confirmMemory();
    await store.getState().invalidateMemory({ reason: "outdated" });
    await store.getState().previewPruneMemory({ reason: "cleanup" });
    expect(store.getState().memory.preview?.would_prune).toBe(true);
    await store.getState().pruneMemory({ reason: "cleanup" });

    expect(calls).toContain("list:stale:pytest");
    expect(calls).toContain("detail:memory-1");
    expect(calls).toContain("confirm:memory-1");
    expect(calls).toContain("invalidate:outdated");
    expect(calls).toContain("preview");
    expect(calls).toContain("prune");
    expect(store.getState().action).toMatchObject({ kind: "prune-memory", state: "succeeded" });
  });

  it("loads repository status, search results, details, and rebuild actions", async () => {
    const calls: string[] = [];
    const store = createKnowledgeStore(
      createApiClient({
        getRepositoryIndexEntryDetail: async (entryId) => {
          calls.push(`detail:${entryId}`);
          return { entry: makeRepositoryEntry(entryId) };
        },
        getRepositoryIndexStatus: async () => {
          calls.push("status");
          return {
            built_at: timestamp(0),
            builder_version: "v1",
            detail: null,
            entry_count: 2,
            path: "/tmp/.glassbox/repository-index.json",
            schema_version: 1,
            source_digest: "digest",
            status: "fresh",
          };
        },
        rebuildRepositoryIndex: async (input = {}) => {
          calls.push(`rebuild:${input.sessionId ?? "sync"}`);
          return {
            detail: null,
            index: null,
            job: null,
            mode: "background",
            status: "queued",
          };
        },
        searchRepositoryIndex: async (query) => {
          calls.push(`search:${query.query}`);
          return {
            items: [makeRepositoryEntry("entry-1")],
            page: { cursor: 0, has_more: false, limit: 50, next_cursor: null, returned_count: 1 },
            query: query.query,
          };
        },
      }),
    );

    await store.getState().loadRepositoryStatus();
    await store.getState().searchRepositoryIndex("UsefulThing");
    await store.getState().selectRepositoryEntry("entry-1");
    await store.getState().rebuildRepositoryIndex({ sessionId: "session-1" });

    expect(calls).toEqual([
      "status",
      "search:UsefulThing",
      "detail:entry-1",
      "rebuild:session-1",
      "status",
      "search:UsefulThing",
    ]);
    expect(store.getState().repository.status?.status).toBe("fresh");
    expect(store.getState().repository.rebuild?.status).toBe("queued");
    expect(store.getState().repository.selectedEntry?.name).toBe("UsefulThing");
  });
});

describe("session store", () => {
  it("loads selected sessions while preserving local drafts", async () => {
    const store = createSessionStore({ apiClient: createApiClient() });
    store.getState().setComposerText("draft prompt");
    store.getState().setAnswerText("question-1", "draft answer");

    await store.getState().loadSession("session-1");

    expect(store.getState().loadState).toBe("loaded");
    expect(store.getState().data.sessionId).toBe("session-1");
    expect(store.getState().drafts.composerText).toBe("draft prompt");
    expect(store.getState().drafts.answerTextByQuestionId["question-1"]).toBe("draft answer");
  });

  it("loads additional session detail pages on demand", async () => {
    const store = createSessionStore({
      apiClient: createApiClient({
        getSessionTranscriptPage: async (sessionId, query = {}) => ({
          items: makeSessionSnapshot(sessionId).transcript.map((message) => ({
            ...message,
            message_id: `message-${query.cursor ?? 0}`,
          })),
          page: {
            cursor: query.cursor ?? 0,
            has_more: query.cursor === undefined,
            limit: query.limit ?? 80,
            next_cursor: query.cursor === undefined ? 1 : null,
            returned_count: 1,
          },
          session_id: sessionId,
        }),
      }),
    });

    await store.getState().loadSession("session-1");
    expect(store.getState().detailPages.transcript.hasMore).toBe(true);

    await store.getState().loadMoreTranscript();

    expect(store.getState().data.transcript.map((message) => message.message_id)).toEqual([
      "message-0",
      "message-1",
    ]);
    expect(store.getState().detailPages.transcript.hasMore).toBe(false);
  });

  it("keeps large-session detail hydration bounded to page windows", async () => {
    const sessionId = "large-session";
    const transcript = makeLargeTranscript(sessionId, 240);
    const events = makeLargeEvents(sessionId, 681);
    const metrics = makeLargeMetrics(120);
    const calls: Array<{ cursor: number | undefined; kind: string; limit: number | undefined }> =
      [];
    const store = createSessionStore({
      apiClient: createApiClient({
        getSessionEventLogPage: async (requestedSessionId, query = {}) => {
          calls.push({ cursor: query.cursor, kind: "events", limit: query.limit });
          return makeDetailPage(requestedSessionId, events, query);
        },
        getSessionSnapshot: async (requestedSessionId) =>
          makeSessionSnapshot(requestedSessionId, {
            last_sequence: events.length,
            transcript,
            turn_metrics: metrics,
          }),
        getSessionTranscriptPage: async (requestedSessionId, query = {}) => {
          calls.push({ cursor: query.cursor, kind: "transcript", limit: query.limit });
          return makeDetailPage(requestedSessionId, transcript, query);
        },
        getSessionTurnMetricsPage: async (requestedSessionId, query = {}) => {
          calls.push({ cursor: query.cursor, kind: "metrics", limit: query.limit });
          return makeDetailPage(requestedSessionId, metrics, query);
        },
      }),
    });

    await store.getState().loadSession(sessionId);

    expect(store.getState().data.transcript).toHaveLength(80);
    expect(store.getState().data.eventLog).toHaveLength(80);
    expect(store.getState().data.turnMetrics).toHaveLength(80);
    expect(store.getState().detailPages.transcript).toMatchObject({
      hasMore: true,
      nextCursor: 80,
      state: "loaded",
    });
    expect(calls).toEqual([
      { cursor: undefined, kind: "transcript", limit: 80 },
      { cursor: undefined, kind: "events", limit: 80 },
      { cursor: undefined, kind: "metrics", limit: 80 },
    ]);

    await store.getState().loadMoreTranscript();
    await store.getState().loadMoreEvents();
    await store.getState().loadMoreMetrics();

    expect(store.getState().data.transcript).toHaveLength(160);
    expect(store.getState().data.eventLog).toHaveLength(160);
    expect(store.getState().data.turnMetrics).toHaveLength(120);
    expect(store.getState().detailPages.metrics.hasMore).toBe(false);
    expect(calls.slice(3)).toEqual([
      { cursor: 80, kind: "transcript", limit: 80 },
      { cursor: 80, kind: "events", limit: 80 },
      { cursor: 80, kind: "metrics", limit: 80 },
    ]);
  });

  it("ignores stale selected-session responses", async () => {
    const first = deferred<ReturnType<typeof makeSessionSnapshot>>();
    const second = deferred<ReturnType<typeof makeSessionSnapshot>>();
    let callCount = 0;
    const store = createSessionStore({
      apiClient: createApiClient({
        getSessionSnapshot: async () => (++callCount === 1 ? first.promise : second.promise),
      }),
    });

    const firstLoad = store.getState().loadSession("stale");
    const secondLoad = store.getState().loadSession("fresh");
    first.resolve(makeSessionSnapshot("stale"));
    second.resolve(makeSessionSnapshot("fresh"));
    await Promise.all([firstLoad, secondLoad]);

    expect(store.getState().data.sessionId).toBe("fresh");
  });

  it("loads compare snapshots and clears compare targets", async () => {
    const store = createSessionStore({ apiClient: createApiClient() });
    await store.getState().loadSession("session-1");
    await store.getState().loadCompareSession("compare-1");

    expect(store.getState().data.compareSessionId).toBe("compare-1");
    expect(store.getState().data.compareSession?.sessionId).toBe("compare-1");
    expect(store.getState().drafts.selectedCompareTargetId).toBe("compare-1");

    store.getState().clearCompareSession();
    expect(store.getState().data.compareSession).toBeNull();
    expect(store.getState().drafts.selectedCompareTargetId).toBeNull();
  });

  it("resets invalid compare targets after load failures", async () => {
    const store = createSessionStore({
      apiClient: createApiClient({
        getCompareSessionSnapshot: async () => {
          throw new GlassboxApiError({ kind: "not_found", message: "compare target missing" });
        },
      }),
    });
    await store.getState().loadSession("session-1");
    await store.getState().loadCompareSession("missing-session");

    expect(store.getState().data.compareSession).toBeNull();
    expect(store.getState().data.compareSessionId).toBeNull();
    expect(store.getState().action).toMatchObject({
      error: "compare target missing",
      state: "failed",
    });
  });

  it("connects the stream slice and applies stream events", async () => {
    const streams: FakeStreamHandle[] = [];
    const store = createSessionStore({
      apiClient: createApiClient(),
      createEventStream: (options) => {
        const stream = new FakeStreamHandle(options);
        streams.push(stream);
        return stream;
      },
    });
    await store.getState().loadSession("session-1");

    store.getState().connectStream();
    streams[0]?.emit(
      makeEnvelope(8, "UserMessageReceived", { message_id: "message-2", text: "hello" }),
    );

    expect(streams[0]?.started).toBe(true);
    expect(streams[0]?.options.afterSequence).toBe(4);
    expect(store.getState().stream).toMatchObject<Partial<SessionStreamState>>({
      lastSequence: 8,
      status: "live",
    });
    expect(store.getState().data.transcript.at(-1)?.message_id).toBe("message-2");

    store.getState().disconnectStream();
    expect(streams[0]?.closed).toBe(true);
    expect(store.getState().stream.status).toBe("historical_snapshot");
  });

  it("keeps repeated session observers independent while sharing the same resume cursor", async () => {
    const streams: FakeStreamHandle[] = [];
    const createEventStream = (options: SessionEventStreamOptions) => {
      const stream = new FakeStreamHandle(options);
      streams.push(stream);
      return stream;
    };
    const firstStore = createSessionStore({
      apiClient: createApiClient(),
      createEventStream,
    });
    const secondStore = createSessionStore({
      apiClient: createApiClient(),
      createEventStream,
    });

    await firstStore.getState().loadSession("session-1");
    await secondStore.getState().loadSession("session-1");
    firstStore.getState().connectStream();
    secondStore.getState().connectStream();

    const liveEnvelope = makeEnvelope(9, "UserMessageReceived", {
      message_id: "message-observed",
      text: "seen by both observers",
    });
    streams[0]?.emit(liveEnvelope);
    streams[1]?.emit(liveEnvelope);

    expect(streams).toHaveLength(2);
    expect(streams.map((stream) => stream.options.afterSequence)).toEqual([4, 4]);
    expect(firstStore.getState().data.transcript.at(-1)?.message_id).toBe("message-observed");
    expect(secondStore.getState().data.transcript.at(-1)?.message_id).toBe("message-observed");

    firstStore.getState().disconnectStream();
    expect(streams[0]?.closed).toBe(true);
    expect(streams[1]?.closed).toBe(false);

    secondStore.getState().disconnectStream();
    expect(streams[1]?.closed).toBe(true);
  });

  it("calls typed action helpers without mutating canonical session data", async () => {
    const calls: string[] = [];
    const store = createSessionStore({
      apiClient: createApiClient({
        resolveApproval: async () => {
          calls.push("approval");
          return { status: "ok" };
        },
        retryToolAttempt: async () => {
          calls.push("tool-retry");
          return {
            message: "retried",
            original_attempt: toolAttempt,
            retry_attempt: { ...toolAttempt, status: "succeeded", tool_attempt_id: "attempt-2" },
          };
        },
        abandonToolAttempt: async () => {
          calls.push("tool-abandon");
          return {
            message: "abandoned",
            original_attempt: { ...toolAttempt, status: "abandoned" },
            retry_attempt: null,
          };
        },
        submitAnswer: async () => {
          calls.push("answer");
          return { status: "ok" };
        },
        submitMessage: async () => {
          calls.push("prompt");
          return { status: "ok" };
        },
      }),
    });
    await store.getState().loadSession("session-1");
    store.getState().setComposerText("Continue");
    store.getState().setAnswerText("question-1", "blue");

    await store.getState().submitPrompt();
    await store.getState().submitAnswer({ questionId: "question-1" });
    await store.getState().resolveApproval({ approvalId: "approval-1", decision: "approved" });
    await store.getState().retryToolAttempt({ toolAttemptId: "attempt-1" });
    await store.getState().abandonToolAttempt({ toolAttemptId: "attempt-1" });
    const childSessionId = await store.getState().forkSession({ turnId: "turn-1" });

    expect(calls).toEqual(["prompt", "answer", "approval", "tool-retry", "tool-abandon"]);
    expect(childSessionId).toBe("child-1");
    expect(store.getState().drafts.composerText).toBe("");
    expect(store.getState().drafts.answerTextByQuestionId).toEqual({});
    expect(store.getState().data.transcript).toHaveLength(1);
    expect(store.getState().action).toMatchObject({ kind: "fork", state: "succeeded" });
  });

  it("surfaces conflict, validation, and network failures from action helpers", async () => {
    const store = createSessionStore({
      apiClient: createApiClient({
        forkSession: async () => {
          throw new GlassboxApiError({ kind: "network", message: "network unavailable" });
        },
        resolveApproval: async () => {
          throw new GlassboxApiError({ kind: "conflict", message: "approval already resolved" });
        },
        submitMessage: async () => {
          throw new GlassboxApiError({ kind: "validation", message: "prompt is required" });
        },
      }),
    });
    await store.getState().loadSession("session-1");
    store.getState().setComposerText("Continue");

    await store.getState().submitPrompt();
    expect(store.getState().action).toMatchObject({
      error: "prompt is required",
      kind: "prompt",
      state: "failed",
    });

    await store.getState().resolveApproval({ approvalId: "approval-1", decision: "approved" });
    expect(store.getState().action).toMatchObject({
      error: "approval already resolved",
      kind: "approval",
      state: "failed",
    });

    await expect(store.getState().forkSession({ turnId: "turn-1" })).resolves.toBeNull();
    expect(store.getState().action).toMatchObject({
      error: "network unavailable",
      kind: "fork",
      state: "failed",
    });
  });

  it("resets server state for route changes while preserving drafts", async () => {
    const store = createSessionStore({ apiClient: createApiClient() });
    await store.getState().loadSession("session-1");
    store.getState().setComposerText("keep me");

    store.getState().resetForRoute("session-2");

    expect(store.getState().data.sessionId).toBeNull();
    expect(store.getState().data.selectedSessionId).toBe("session-2");
    expect(store.getState().drafts.composerText).toBe("keep me");
    expect(store.getState().loadState).toBe("loading");
  });
});

type EventLogEntry = components["schemas"]["EventLogEntryResponse"];
type PageInfo = components["schemas"]["PageInfoResponse"];
type BranchCandidate = components["schemas"]["BranchCandidateResponse"];
type BranchCandidateDecisionSupport =
  components["schemas"]["BranchCandidateDecisionSupportResponse"];
type BranchSearchDetail = components["schemas"]["BranchSearchDetailResponse"];
type BranchSearchDecisionSupport = components["schemas"]["BranchSearchDecisionSupportResponse"];
type BranchSearchSummary = components["schemas"]["BranchSearchSummaryResponse"];
type RepositoryEntry = components["schemas"]["RepositoryIndexEntryResponse"];
type TaskDetail = components["schemas"]["TaskDetailResponse"];
type TaskSummary = components["schemas"]["TaskSummaryResponse"];
type TranscriptMessage = components["schemas"]["TranscriptMessageResponse"];
type TurnMetrics = components["schemas"]["TurnMetricsResponse"];
type WorkspaceMemoryEntry = components["schemas"]["WorkspaceMemoryEntryResponse"];

function makeTaskSummary(taskId: string, overrides: Partial<TaskSummary> = {}): TaskSummary {
  return {
    blocked_detail: null,
    blocked_reason: null,
    current_step_id: null,
    goal: "Inspect autonomous work",
    next_action_summary: "continue from current step",
    session_id: "session-1",
    status: "active",
    step_count: 1,
    task_id: taskId,
    title: "Task",
    updated_at: timestamp(0),
    ...overrides,
  };
}

function makeVerificationSummary(
  taskId: string,
  overrides: Partial<TaskDetail["verification_summary"]> = {},
): TaskDetail["verification_summary"] {
  return {
    accepted_risk_count: 0,
    current_posture: "missing",
    failed_count: 0,
    latest_failed_check_name: null,
    latest_failed_sequence: null,
    latest_failed_summary: null,
    latest_failed_verification_id: null,
    latest_success_check_name: null,
    latest_success_sequence: null,
    latest_success_verification_id: null,
    passed_count: 0,
    running_count: 0,
    skipped_count: 0,
    task_id: taskId,
    total_count: 0,
    ...overrides,
  };
}

function makeVerificationDrift(
  taskId: string,
  overrides: Partial<TaskDetail["verification_drift"]> = {},
): TaskDetail["verification_drift"] {
  return {
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
    task_id: taskId,
    workspace_clean: true,
    ...overrides,
  };
}

function makeBranchSearchSummary(
  searchId: string,
  overrides: Partial<BranchSearchSummary> = {},
): BranchSearchSummary {
  return {
    abandoned_reason: null,
    candidate_count: 1,
    created_at: timestamp(0),
    last_sequence: 3,
    objective: "Compare repair options",
    parent_session_id: "session-1",
    search_id: searchId,
    selected_candidate_id: null,
    session_id: "session-1",
    status: "completed",
    task_id: "task-1",
    updated_at: timestamp(2),
    ...overrides,
  };
}

function makeBranchCandidate(
  candidateId: string,
  overrides: Partial<BranchCandidate> = {},
): BranchCandidate {
  return {
    artifact_id: "artifact-1",
    candidate_id: candidateId,
    candidate_session_id: "session-child",
    changed_files: ["src/glassbox/runtime/example.py"],
    created_at: timestamp(0),
    last_sequence: 4,
    parent_session_id: "session-1",
    patch_summary: "Updated runtime branch search handling.",
    policy_budget_summary: "Used one branch attempt from the task budget.",
    residual_risks: ["Needs operator merge review."],
    search_id: "search-1",
    selection_state: null,
    status: "verified",
    strategy_label: "Try minimal fix",
    updated_at: timestamp(2),
    verification_id: "verification-1",
    verification_status: "passed",
    verification_summary: "Targeted tests passed.",
    ...overrides,
  };
}

function makeBranchSearchDetail(searchId: string): BranchSearchDetail {
  return {
    candidates: [makeBranchCandidate("candidate-1", { search_id: searchId })],
    decision_support: makeBranchSearchDecisionSupport(searchId),
    search: makeBranchSearchSummary(searchId),
  };
}

function makeBranchCandidateDecisionSupport(
  candidateId: string,
  overrides: Partial<BranchCandidateDecisionSupport> = {},
): BranchCandidateDecisionSupport {
  return {
    accepted_risks: [],
    candidate_id: candidateId,
    candidate_session_id: "session-child",
    changed_files: [],
    changed_files_summary:
      "Changed-file evidence is not captured in current branch-search projections.",
    cost_estimate: "low",
    evidence: [
      {
        kind: "session",
        session_id: "session-child",
        summary: "Candidate session is retained for inspection.",
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

function makeBranchSearchDecisionSupport(
  searchId: string,
  overrides: Partial<BranchSearchDecisionSupport> = {},
): BranchSearchDecisionSupport {
  return {
    automatic_merge: false,
    candidates: [makeBranchCandidateDecisionSupport("candidate-1", { search_id: searchId })],
    non_goal:
      "Branch search records candidate evidence and operator decisions; it does not automatically merge or mutate parent history.",
    objective: "Compare repair options",
    search_id: searchId,
    selected_candidate_id: null,
    ...overrides,
  };
}

function makeMemoryEntry(
  memoryId: string,
  overrides: Partial<WorkspaceMemoryEntry> = {},
): WorkspaceMemoryEntry {
  return {
    confirmed_at: timestamp(0),
    confirmed_by: "operator",
    content: "Use uv run pytest for backend tests.",
    created_at: timestamp(0),
    created_by: "operator",
    import_source: null,
    invalidated_at: null,
    invalidated_by: null,
    invalidation_reason: null,
    kind: "command",
    last_sequence: 2,
    last_used_at: timestamp(1),
    memory_id: memoryId,
    provenance: {
      artifact_id: null,
      note: null,
      session_id: "session-1",
      source_label: null,
      source_sequence: 1,
      source_type: "session_event",
      task_id: null,
      tool_call_id: null,
    },
    prune_reason: null,
    pruned_at: null,
    pruned_by: null,
    redacted: false,
    session_id: "session-1",
    state: "active",
    summary: "Backend tests use uv",
    tags: ["tests"],
    updated_at: timestamp(1),
    use_count: 1,
    ...overrides,
  };
}

function makeRepositoryEntry(
  entryId: string,
  overrides: Partial<RepositoryEntry> = {},
): RepositoryEntry {
  return {
    entry_id: entryId,
    kind: "symbol",
    language: "python",
    name: "UsefulThing",
    path: "src/sample.py",
    provenance: [
      {
        content_sha256: null,
        line_end: 1,
        line_start: 1,
        note: null,
        path: "src/sample.py",
        source_label: null,
        source_type: "static_analysis",
        tool_name: null,
      },
    ],
    summary: "Class UsefulThing",
    symbol: "UsefulThing",
    tags: ["source"],
    updated_at: timestamp(0),
    ...overrides,
  };
}

function makeDetailPage<T>(
  sessionId: string,
  items: T[],
  query: { cursor?: number; limit?: number },
): { items: T[]; page: PageInfo; session_id: string } {
  const cursor = query.cursor ?? 0;
  const limit = query.limit ?? 80;
  const pageItems = items.slice(cursor, cursor + limit);
  const nextCursor = cursor + pageItems.length;
  return {
    items: pageItems,
    page: {
      cursor,
      has_more: nextCursor < items.length,
      limit,
      next_cursor: nextCursor < items.length ? nextCursor : null,
      returned_count: pageItems.length,
    },
    session_id: sessionId,
  };
}

function makeLargeTranscript(sessionId: string, count: number): TranscriptMessage[] {
  return Array.from({ length: count }, (_, index) => ({
    created_at: timestamp(index),
    message_id: `${sessionId}-message-${index + 1}`,
    parts: [{ kind: "text", text: `large transcript message ${index}` }],
    role: index % 2 === 0 ? "user" : "assistant",
  }));
}

function makeLargeEvents(sessionId: string, count: number): EventLogEntry[] {
  return Array.from({ length: count }, (_, index) => ({
    created_at: timestamp(index),
    event_id: `${sessionId}-event-${index + 1}`,
    event_type: index % 2 === 0 ? "UserMessageReceived" : "AssistantMessageCompleted",
    event_version: 1,
    payload: { index },
    sequence: index + 1,
    session_id: sessionId,
  }));
}

function makeLargeMetrics(count: number): TurnMetrics[] {
  return Array.from({ length: count }, (_, index) => ({
    completed_at: timestamp(index + 1),
    failed_tool_call_count: 0,
    model_call_count: 1,
    model_duration_ms_total: 35 + (index % 8),
    model_input_tokens_total: 120 + index,
    model_output_tokens_total: 48 + index,
    started_at: timestamp(index),
    succeeded_tool_call_count: index < 80 ? 1 : 0,
    tool_call_count: index < 80 ? 1 : 0,
    tool_duration_ms_total: index < 80 ? 15 : 0,
    turn_duration_ms: 50 + (index % 8),
    turn_id: `turn-${index + 1}`,
  }));
}

function timestamp(index: number): string {
  const minutes = Math.floor(index / 60);
  const seconds = index % 60;
  return `2026-04-23T00:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}Z`;
}
