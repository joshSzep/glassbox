import { describe, expect, it } from "vitest";

import { GlassboxApiError, type GlassboxApiClient } from "../api/client";
import type { SessionEventStreamOptions, SessionStreamState, SseEventEnvelope } from "../api/sse";
import { createConsoleStore, createSessionStore } from "../stores/dashboard-stores";
import {
  makeEnvelope,
  makeSessionAggregate,
  makeSessionSnapshot,
  makeSessionSummary,
} from "./fixtures/session-state";

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
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    getSessionTurnMetricsPage: async (sessionId) => ({
      items: [],
      page: { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 },
      session_id: sessionId,
    }),
    listSessions: async () => [],
    cancelTurn: async () => ({ status: "ok" }),
    resolveApproval: async () => ({ status: "ok" }),
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
      error: null,
      lastSequence: this.options.afterSequence ?? 0,
      retryCount: 0,
      status: "live",
    });
  }

  getState(): SessionStreamState {
    return {
      error: null,
      lastSequence: this.options.afterSequence ?? 0,
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

  it("calls typed action helpers without mutating canonical session data", async () => {
    const calls: string[] = [];
    const store = createSessionStore({
      apiClient: createApiClient({
        resolveApproval: async () => {
          calls.push("approval");
          return { status: "ok" };
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
    const childSessionId = await store.getState().forkSession({ turnId: "turn-1" });

    expect(calls).toEqual(["prompt", "answer", "approval"]);
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
