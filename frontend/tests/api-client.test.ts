import { describe, expect, it } from "vitest";

import {
  GlassboxApiError,
  buildApiUrl,
  createGlassboxApiClient,
  type FetchLike,
} from "../api/client";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
    ...init,
  });
}

function createMockFetch(responses: Response[]): {
  calls: { input: RequestInfo | URL; init?: RequestInit }[];
  fetch: FetchLike;
} {
  const calls: { input: RequestInfo | URL; init?: RequestInit }[] = [];
  const fetch: FetchLike = async (input, init) => {
    calls.push({ input, init });
    const response = responses.shift();
    if (response === undefined) {
      throw new Error("unexpected fetch call");
    }
    return response;
  };
  return { calls, fetch };
}

describe("buildApiUrl", () => {
  it("builds same-origin and absolute API URLs while omitting empty query values", () => {
    expect(buildApiUrl(undefined, "/healthz")).toBe("/healthz");
    expect(
      buildApiUrl("http://127.0.0.1:8765/", "/sessions/aggregate", {
        limit: 25,
        queue: "approvals",
        status: null,
      }),
    ).toBe("http://127.0.0.1:8765/sessions/aggregate?limit=25&queue=approvals");
  });
});

describe("createGlassboxApiClient", () => {
  it("fetches health and aggregate data with typed request shaping", async () => {
    const abortController = new AbortController();
    const { calls, fetch } = createMockFetch([
      jsonResponse({
        status: "ok",
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
      }),
      jsonResponse({ sessions: [] }),
    ]);
    const client = createGlassboxApiClient({ baseUrl: "http://api.test/", fetch });

    await expect(client.getHealth({ signal: abortController.signal })).resolves.toMatchObject({
      status: "ok",
    });
    await expect(
      client.getSessionAggregate({ limit: 10, queue: "action-needed" }),
    ).resolves.toMatchObject({ sessions: [] });

    expect(calls[0]).toMatchObject({
      input: "http://api.test/healthz",
      init: { method: "GET", signal: abortController.signal },
    });
    expect(calls[1]).toMatchObject({
      input: "http://api.test/sessions/aggregate?limit=10&queue=action-needed",
      init: { method: "GET" },
    });
  });

  it("shapes operator action requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ child_session_id: "child" }),
      jsonResponse({ session_id: "compare" }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.resolveApproval({
      approvalId: "approval/1",
      decision: "approved",
      sessionId: "session/1",
    });
    await client.submitMessage({ sessionId: "session/1", text: "Continue" });
    await client.submitAnswer({ answer: "blue", questionId: "question/1", sessionId: "session/1" });
    await client.cancelTurn({ reason: "stop", sessionId: "session/1", turnId: "turn/1" });
    await client.forkSession({ branchLabel: "alt", sessionId: "session/1", turnId: "turn/1" });
    await client.getCompareSessionSnapshot("compare/1");

    expect(calls.map((call) => call.input)).toEqual([
      "/sessions/session%2F1/approvals/approval%2F1",
      "/sessions/session%2F1/messages",
      "/sessions/session%2F1/questions/question%2F1",
      "/sessions/session%2F1/cancel",
      "/sessions/session%2F1/fork",
      "/sessions/compare%2F1",
    ]);
    expect(calls[0].init?.body).toBe(JSON.stringify({ decision: "approved" }));
    expect(calls[1].init?.body).toBe(JSON.stringify({ text: "Continue" }));
    expect(calls[2].init?.body).toBe(JSON.stringify({ answer: "blue" }));
    expect(calls[3].init?.body).toBe(JSON.stringify({ reason: "stop", turn_id: "turn/1" }));
    expect(calls[4].init?.body).toBe(JSON.stringify({ branch_label: "alt", turn_id: "turn/1" }));
  });

  it("shapes paginated session detail requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 20, next_cursor: null, returned_count: 0 },
        session_id: "session/1",
      }),
      jsonResponse({
        items: [],
        page: { cursor: 20, has_more: false, limit: 20, next_cursor: null, returned_count: 0 },
        session_id: "session/1",
      }),
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 10, next_cursor: null, returned_count: 0 },
        session_id: "session/1",
      }),
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 5, next_cursor: null, returned_count: 0 },
        session_id: "session/1",
      }),
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 12, next_cursor: null, returned_count: 0 },
        session_id: "session/1",
      }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.getSessionTranscriptPage("session/1", { limit: 20 });
    await client.getSessionEventLogPage("session/1", { cursor: 20, limit: 20 });
    await client.getSessionToolCallPage("session/1", { limit: 10 });
    await client.getSessionTurnMetricsPage("session/1", { limit: 5 });
    await client.getSessionArtifactPage("session/1", { limit: 12 });

    expect(calls.map((call) => call.input)).toEqual([
      "/sessions/session%2F1/transcript?limit=20",
      "/sessions/session%2F1/event-log?cursor=20&limit=20",
      "/sessions/session%2F1/tool-calls?limit=10",
      "/sessions/session%2F1/turn-metrics?limit=5",
      "/sessions/session%2F1/artifacts?limit=12",
    ]);
  });

  it("shapes task read requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 20, next_cursor: null, returned_count: 0 },
        projection_health: null,
        session_id: "session/1",
      }),
      jsonResponse({
        projection_health: { state: "ok" },
        steps: [],
        task: { task_id: "task/1" },
        verifications: [],
      }),
      jsonResponse({
        items: [],
        page: { cursor: 0, has_more: false, limit: 1, next_cursor: null, returned_count: 0 },
        projection_health: { state: "ok" },
        task_id: "task/1",
      }),
      jsonResponse({
        items: [],
        page: { cursor: 2, has_more: false, limit: 2, next_cursor: null, returned_count: 0 },
        projection_health: { state: "ok" },
        task_id: "task/1",
      }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.getTaskPage({ limit: 20, session_id: "session/1" });
    await client.getTaskDetail("task/1");
    await client.getTaskStepPage("task/1", { limit: 1 });
    await client.getTaskEventPage("task/1", { cursor: 2, limit: 2 });

    expect(calls.map((call) => call.input)).toEqual([
      "/tasks?limit=20&session_id=session%2F1",
      "/tasks/task%2F1",
      "/tasks/task%2F1/steps?limit=1",
      "/tasks/task%2F1/events?cursor=2&limit=2",
    ]);
  });

  it("shapes task and background job action requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ status: "ok" }),
      jsonResponse({ job: { job_id: "job/1" } }),
      jsonResponse({ status: "approved", continuation_window: {}, job: { job_id: "job/2" } }),
      jsonResponse({ pause_window_id: "pause/1", status: "scheduled" }),
      jsonResponse({ pause_window_id: "pause/1", status: "cancelled" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ status: "ok" }),
      jsonResponse({ job: { job_id: "job/1" } }),
    ]);
    const client = createGlassboxApiClient({ fetch });
    const budget: Parameters<typeof client.adjustTaskBudget>[0]["budget"] = {
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
    };

    await client.approveTaskPlan({ reason: "ok", taskId: "task/1" });
    await client.continueTask({ reason: "go", taskId: "task/1", verifyRepair: false });
    await client.resolveTaskContinuationWindow({
      reason: "go longer",
      requestedMinutes: 15,
      taskId: "task/1",
    });
    await client.scheduleTaskPauseWindow({
      policy: "before_risky_action",
      reason: "pause",
      taskId: "task/1",
    });
    await client.cancelTaskPauseWindow({
      pauseWindowId: "pause/1",
      reason: "override",
      taskId: "task/1",
    });
    await client.pauseTask({ detail: "hold", taskId: "task/1" });
    await client.resumeTask({ reason: "ready", taskId: "task/1" });
    await client.cancelTask({ reason: "stop", taskId: "task/1" });
    await client.adjustTaskBudget({ budget, mode: "inspect", taskId: "task/1" });
    await client.cancelBackgroundJob({ jobId: "job/1", reason: "stop job" });

    expect(calls.map((call) => call.input)).toEqual([
      "/tasks/task%2F1/approve-plan",
      "/tasks/task%2F1/continue",
      "/tasks/task%2F1/continuation-window",
      "/tasks/task%2F1/pause-window",
      "/tasks/task%2F1/pause-window/pause%2F1/cancel",
      "/tasks/task%2F1/pause",
      "/tasks/task%2F1/resume",
      "/tasks/task%2F1/cancel",
      "/tasks/task%2F1/budget",
      "/jobs/job%2F1/cancel",
    ]);
    expect(calls[1].init?.body).toBe(
      JSON.stringify({
        checkpoint_id: null,
        continue_for_minutes: null,
        reason: "go",
        requested_by: "operator",
        verify_repair: false,
      }),
    );
    expect(calls[2].init?.body).toBe(
      JSON.stringify({
        checkpoint_id: null,
        decided_by: "operator",
        decision: "approved",
        reason: "go longer",
        requested_by: "operator",
        requested_minutes: 15,
        verify_repair: true,
      }),
    );
    expect(calls[3].init?.body).toBe(
      JSON.stringify({
        actor: "operator",
        checkpoint_id: null,
        pause_before: null,
        policy: "before_risky_action",
        reason: "pause",
      }),
    );
    expect(calls[4].init?.body).toBe(
      JSON.stringify({
        actor: "operator",
        reason: "override",
      }),
    );
    expect(calls[8].init?.body).toBe(
      JSON.stringify({
        actor: "operator",
        budget,
        detail: null,
        mode: "inspect",
        reason: null,
      }),
    );
    expect(calls[9].init?.body).toBe(JSON.stringify({ actor: "operator", reason: "stop job" }));
  });

  it("shapes memory and repository index requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ items: [], page: {} }),
      jsonResponse({ entry: { memory_id: "memory/1" } }),
      jsonResponse({ entry: { memory_id: "memory/1" } }),
      jsonResponse({ entry: { memory_id: "memory/1" } }),
      jsonResponse({ entry: { memory_id: "memory/1" }, would_prune: true }),
      jsonResponse({ entry: { memory_id: "memory/1" } }),
      jsonResponse({ status: "fresh" }),
      jsonResponse({ items: [], page: {}, query: "UsefulThing" }),
      jsonResponse({ entry: { entry_id: "entry/1" } }),
      jsonResponse({ mode: "background", status: "queued" }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.listWorkspaceMemory({ include_pruned: true, query: "pytest", state: "active" });
    await client.getWorkspaceMemoryDetail("memory/1");
    await client.confirmWorkspaceMemory({ memoryId: "memory/1", reason: "fresh" });
    await client.invalidateWorkspaceMemory({ memoryId: "memory/1", reason: "stale" });
    await client.previewWorkspaceMemoryPrune({ memoryId: "memory/1", reason: "cleanup" });
    await client.pruneWorkspaceMemory({ memoryId: "memory/1", reason: "cleanup" });
    await client.getRepositoryIndexStatus();
    await client.searchRepositoryIndex({ limit: 5, query: "UsefulThing" });
    await client.getRepositoryIndexEntryDetail("entry/1");
    await client.rebuildRepositoryIndex({ sessionId: "session/1" });

    expect(calls.map((call) => call.input)).toEqual([
      "/memory?include_pruned=true&query=pytest&state=active",
      "/memory/memory%2F1",
      "/memory/memory%2F1/confirm",
      "/memory/memory%2F1/invalidate",
      "/memory/memory%2F1/prune-preview",
      "/memory/memory%2F1/prune",
      "/repo/index/status",
      "/repo/index/search?limit=5&query=UsefulThing",
      "/repo/index/entries/entry%2F1",
      "/repo/index/rebuild",
    ]);
    expect(calls[2].init?.body).toBe(JSON.stringify({ actor: "operator", reason: "fresh" }));
    expect(calls[3].init?.body).toBe(JSON.stringify({ actor: "operator", reason: "stale" }));
    expect(calls[9].init?.body).toBe(
      JSON.stringify({
        background: true,
        requested_by: "operator",
        session_id: "session/1",
      }),
    );
  });

  it("shapes branch-search read and selection requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ items: [] }),
      jsonResponse({ candidates: [], search: { search_id: "search/1" } }),
      jsonResponse({ candidate: { candidate_id: "candidate/1" }, status: "select" }),
      jsonResponse({ candidate: { candidate_id: "candidate/1" }, status: "reject" }),
      jsonResponse({ candidate: { candidate_id: "candidate/1" }, status: "needs-review" }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.getBranchSearchPage({ limit: 10, session_id: "session/1" });
    await client.getBranchSearchDetail("search/1");
    await client.markBranchCandidate({
      action: "select",
      candidateId: "candidate/1",
      reason: "best",
      searchId: "search/1",
    });
    await client.markBranchCandidate({
      action: "reject",
      candidateId: "candidate/1",
      reason: "too broad",
      searchId: "search/1",
    });
    await client.markBranchCandidate({
      action: "needs-review",
      candidateId: "candidate/1",
      reason: "inspect artifacts",
      searchId: "search/1",
    });

    expect(calls.map((call) => call.input)).toEqual([
      "/branch-searches?limit=10&session_id=session%2F1",
      "/branch-searches/search%2F1",
      "/branch-searches/search%2F1/candidates/candidate%2F1/select",
      "/branch-searches/search%2F1/candidates/candidate%2F1/reject",
      "/branch-searches/search%2F1/candidates/candidate%2F1/needs-review",
    ]);
    expect(calls[2].init?.body).toBe(JSON.stringify({ actor: "operator", reason: "best" }));
    expect(calls[4].init?.body).toBe(
      JSON.stringify({ actor: "operator", reason: "inspect artifacts" }),
    );
  });

  it("shapes changeset review requests", async () => {
    const { calls, fetch } = createMockFetch([
      jsonResponse({ items: [] }),
      jsonResponse({ changeset: { changeset_id: "changeset/1" } }),
      jsonResponse({ readiness: { state: "missing" } }),
      jsonResponse({ state: "needs_verification" }),
      jsonResponse({ suggestion_label: "suggestion_only_not_committed" }),
      jsonResponse({ detail: { changeset: { changeset_id: "changeset/1" } } }),
      jsonResponse({ detail: { changeset: { changeset_id: "changeset/1" } } }),
      jsonResponse({ evidence: { evidence_id: "evidence/1" } }),
      jsonResponse({ artifact_id: "fixup/1" }),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await client.getChangesetPage({ limit: 10, session_id: "session/1" });
    await client.getChangesetDetail("changeset/1");
    await client.getChangesetVerificationPlan("changeset/1");
    await client.getChangesetCommitReadiness("changeset/1");
    await client.getChangesetCommitMessage("changeset/1");
    await client.generateChangesetReviewBrief({
      changesetId: "changeset/1",
      includeMarkdown: true,
    });
    await client.refreshChangeset({ changesetId: "changeset/1" });
    await client.attachManualEvidence({
      changesetId: "changeset/1",
      note: "external check output summarized",
      sourceLabel: "operator note",
      summary: "manual note",
    });
    await client.recordReviewFeedbackFixupInventory({
      feedbackId: "feedback/1",
      paths: ["src/app.py"],
      fromWorkspace: false,
    });

    expect(calls.map((call) => call.input)).toEqual([
      "/changesets?limit=10&session_id=session%2F1",
      "/changesets/changeset%2F1",
      "/changesets/changeset%2F1/verification-plan",
      "/changesets/changeset%2F1/commit-readiness",
      "/changesets/changeset%2F1/commit-message",
      "/changesets/changeset%2F1/brief",
      "/changesets/changeset%2F1/refresh",
      "/changesets/changeset%2F1/manual-evidence",
      "/changesets/feedback/feedback%2F1/fixup",
    ]);
    expect(calls[5].init?.body).toBe(JSON.stringify({ actor: "operator", include_markdown: true }));
    expect(calls[6].init?.body).toBe(JSON.stringify({ actor: "operator" }));
    expect(calls[7].init?.body).toBe(
      JSON.stringify({
        actor: "operator",
        command_text: null,
        evidence_kind: "operator_assertion",
        freshness: "needs_inspection",
        note: "external check output summarized",
        source_label: "operator note",
        summary: "manual note",
        target_id: "changeset/1",
        target_kind: "changeset",
      }),
    );
    expect(calls[8].init?.body).toBe(
      JSON.stringify({
        actor: "operator",
        from_workspace: false,
        paths: ["src/app.py"],
        source_summary: "dashboard recorded response-linked workspace inventory",
      }),
    );
  });

  it("normalizes FastAPI validation errors", async () => {
    const { fetch } = createMockFetch([
      jsonResponse(
        { detail: [{ loc: ["body", "text"], msg: "Field required", type: "missing" }] },
        { status: 422 },
      ),
    ]);
    const client = createGlassboxApiClient({ fetch });

    await expect(client.submitMessage({ sessionId: "session-1", text: "" })).rejects.toMatchObject({
      issues: [{ msg: "Field required" }],
      kind: "validation",
      message: "Field required",
      status: 422,
    });
  });

  it("normalizes conflict, unavailable, network, and cancelled failures", async () => {
    const conflictClient = createGlassboxApiClient({
      fetch: async () => jsonResponse({ detail: "approval already resolved" }, { status: 409 }),
    });
    await expect(
      conflictClient.resolveApproval({
        approvalId: "approval-1",
        decision: "denied",
        sessionId: "session-1",
      }),
    ).rejects.toMatchObject({ kind: "conflict", message: "approval already resolved" });

    const unavailableClient = createGlassboxApiClient({
      fetch: async () => jsonResponse({ detail: "runtime unavailable" }, { status: 503 }),
    });
    await expect(unavailableClient.getHealth()).rejects.toMatchObject({
      kind: "unavailable",
      message: "runtime unavailable",
    });

    const networkClient = createGlassboxApiClient({
      fetch: async () => {
        throw new TypeError("failed to fetch");
      },
    });
    await expect(networkClient.getHealth()).rejects.toMatchObject({
      kind: "network",
      message: "failed to fetch",
    });

    const cancelledClient = createGlassboxApiClient({
      fetch: async () => {
        throw new DOMException("aborted", "AbortError");
      },
    });
    await expect(cancelledClient.getHealth()).rejects.toBeInstanceOf(GlassboxApiError);
    await expect(cancelledClient.getHealth()).rejects.toMatchObject({ kind: "cancelled" });
  });
});
