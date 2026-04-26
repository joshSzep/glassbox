import { createStore, type StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient, SessionAggregateQuery } from "@/api/client";
import {
  createSessionEventStream,
  type SessionEventStreamOptions,
  type SessionStreamState,
  type SseEventEnvelope,
} from "@/api/sse";
import {
  applySessionEvent,
  clearCompareSession,
  createDashboardState,
  hydrateCompareSession,
  hydrateSelectedSession,
  hydrateSessionAggregate,
  type DashboardState,
} from "@/state/session-state";

export type LoadState = "failed" | "idle" | "loaded" | "loading";
export type ActionKind = "answer" | "approval" | "fork" | "prompt";

export type ActionStatus = {
  error: string | null;
  kind: ActionKind | null;
  state: "failed" | "idle" | "pending" | "succeeded";
};

export type DraftState = {
  answerTextByQuestionId: Record<string, string>;
  composerText: string;
  forkLabel: string;
  selectedCompareTargetId: string | null;
};

export type ConsoleFilters = {
  queue: NonNullable<SessionAggregateQuery["queue"]>;
  sort: NonNullable<SessionAggregateQuery["sort"]>;
  status: string | null;
};

export type ConsoleStoreState = {
  data: DashboardState;
  error: string | null;
  filters: ConsoleFilters;
  loadAggregate: (query?: Partial<ConsoleFilters>) => Promise<void>;
  loadState: LoadState;
  reset: () => void;
  selectQueue: (queue: ConsoleFilters["queue"]) => Promise<void>;
};

export type SessionEventStreamHandle = ReturnType<typeof createSessionEventStream>;
export type SessionEventStreamFactory = (
  options: SessionEventStreamOptions,
) => SessionEventStreamHandle;

export type SessionStoreState = {
  action: ActionStatus;
  applyStreamEnvelope: (envelope: SseEventEnvelope) => void;
  clearCompareSession: () => void;
  connectStream: () => void;
  data: DashboardState;
  disconnectStream: () => void;
  drafts: DraftState;
  error: string | null;
  forkSession: (input?: {
    branchLabel?: string | null;
    turnId?: string | null;
  }) => Promise<string | null>;
  loadCompareSession: (sessionId: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  loadState: LoadState;
  resetForRoute: (sessionId?: string | null) => void;
  resolveApproval: (input: {
    approvalId: string;
    decision: "approved" | "denied";
  }) => Promise<void>;
  setAnswerText: (questionId: string, text: string) => void;
  setComposerText: (text: string) => void;
  setForkLabel: (text: string) => void;
  setSelectedCompareTarget: (sessionId: string | null) => void;
  stream: SessionStreamState;
  submitAnswer: (input: { answer?: string; questionId: string }) => Promise<void>;
  submitPrompt: (text?: string) => Promise<void>;
};

export function createConsoleStore(apiClient: GlassboxApiClient): StoreApi<ConsoleStoreState> {
  let requestId = 0;

  return createStore<ConsoleStoreState>((set, get) => ({
    data: createDashboardState(),
    error: null,
    filters: createDefaultConsoleFilters(),
    loadAggregate: async (query = {}) => {
      const currentRequestId = ++requestId;
      const filters = { ...get().filters, ...query };
      set({ error: null, filters, loadState: "loading" });

      try {
        const aggregate = await apiClient.getSessionAggregate(toAggregateQuery(filters));
        if (currentRequestId !== requestId) {
          return;
        }
        set((state) => ({
          data: hydrateSessionAggregate(state.data, aggregate),
          error: null,
          loadState: "loaded",
        }));
      } catch (error) {
        if (currentRequestId !== requestId) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    reset: () => {
      requestId += 1;
      set({
        data: createDashboardState(),
        error: null,
        filters: createDefaultConsoleFilters(),
        loadState: "idle",
      });
    },
    selectQueue: async (queue) => {
      await get().loadAggregate({ queue });
    },
  }));
}

export function createSessionStore({
  apiClient,
  createEventStream = createSessionEventStream,
}: {
  apiClient: GlassboxApiClient;
  createEventStream?: SessionEventStreamFactory;
}): StoreApi<SessionStoreState> {
  let sessionRequestId = 0;
  let compareRequestId = 0;
  let actionRequestId = 0;
  let streamHandle: SessionEventStreamHandle | null = null;

  const closeStream = () => {
    streamHandle?.close();
    streamHandle = null;
  };

  return createStore<SessionStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    applyStreamEnvelope: (envelope) => {
      set((state) => ({
        data: applySessionEvent(state.data, envelope),
        stream: {
          ...state.stream,
          lastSequence: Math.max(state.stream.lastSequence, envelope.sequence),
        },
      }));
    },
    clearCompareSession: () => {
      compareRequestId += 1;
      set((state) => ({
        data: clearCompareSession(state.data),
        drafts: { ...state.drafts, selectedCompareTargetId: null },
      }));
    },
    connectStream: () => {
      const sessionId = get().data.sessionId;
      if (sessionId === null) {
        return;
      }
      closeStream();
      streamHandle = createEventStream({
        afterSequence: get().data.lastSequence,
        onEnvelope: (envelope) => get().applyStreamEnvelope(envelope),
        onStateChange: (stream) => set({ stream }),
        sessionId,
      });
      streamHandle.start();
    },
    data: createDashboardState(),
    disconnectStream: () => {
      closeStream();
      set({ stream: createIdleStreamState() });
    },
    drafts: createEmptyDraftState(),
    error: null,
    forkSession: async (input = {}) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      set({ action: { error: null, kind: "fork", state: "pending" } });
      try {
        const fork = await apiClient.forkSession({
          branchLabel: (input.branchLabel ?? get().drafts.forkLabel) || null,
          sessionId,
          turnId: input.turnId ?? get().data.selectedForkTurnId,
        });
        if (currentActionRequestId === actionRequestId) {
          set((state) => ({
            action: { error: null, kind: "fork", state: "succeeded" },
            drafts: { ...state.drafts, forkLabel: "" },
          }));
        }
        return fork.child_session_id;
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "fork", state: "failed" } });
        }
        return null;
      }
    },
    loadCompareSession: async (sessionId) => {
      const currentRequestId = ++compareRequestId;
      set((state) => ({
        data: { ...state.data, compareSession: null, compareSessionId: sessionId },
        drafts: { ...state.drafts, selectedCompareTargetId: sessionId },
      }));

      try {
        const snapshot = await apiClient.getCompareSessionSnapshot(sessionId);
        if (currentRequestId !== compareRequestId) {
          return;
        }
        set((state) => ({ data: hydrateCompareSession(state.data, snapshot) }));
      } catch (error) {
        if (currentRequestId !== compareRequestId) {
          return;
        }
        set((state) => ({
          action: { error: errorMessage(error), kind: null, state: "failed" },
          data: clearCompareSession(state.data),
        }));
      }
    },
    loadSession: async (sessionId) => {
      const currentRequestId = ++sessionRequestId;
      closeStream();
      set((state) => ({
        data: { ...state.data, selectedSessionId: sessionId },
        error: null,
        loadState: "loading",
        stream: createIdleStreamState(),
      }));

      try {
        const snapshot = await apiClient.getSessionSnapshot(sessionId);
        if (currentRequestId !== sessionRequestId) {
          return;
        }
        set((state) => ({
          data: hydrateSelectedSession(state.data, snapshot),
          error: null,
          loadState: "loaded",
          stream: { ...state.stream, lastSequence: snapshot.last_sequence },
        }));
      } catch (error) {
        if (currentRequestId !== sessionRequestId) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    resetForRoute: (sessionId = null) => {
      sessionRequestId += 1;
      compareRequestId += 1;
      actionRequestId += 1;
      closeStream();
      set((state) => ({
        action: createIdleActionStatus(),
        data: { ...createDashboardState(), selectedSessionId: sessionId },
        drafts: state.drafts,
        error: null,
        loadState: sessionId === null ? "idle" : "loading",
        stream: createIdleStreamState(),
      }));
    },
    resolveApproval: async ({ approvalId, decision }) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      set({ action: { error: null, kind: "approval", state: "pending" } });
      try {
        await apiClient.resolveApproval({ approvalId, decision, sessionId });
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: null, kind: "approval", state: "succeeded" } });
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "approval", state: "failed" } });
        }
      }
    },
    setAnswerText: (questionId, text) => {
      set((state) => ({
        drafts: {
          ...state.drafts,
          answerTextByQuestionId: {
            ...state.drafts.answerTextByQuestionId,
            [questionId]: text,
          },
        },
      }));
    },
    setComposerText: (text) => {
      set((state) => ({ drafts: { ...state.drafts, composerText: text } }));
    },
    setForkLabel: (text) => {
      set((state) => ({ drafts: { ...state.drafts, forkLabel: text } }));
    },
    setSelectedCompareTarget: (sessionId) => {
      set((state) => ({ drafts: { ...state.drafts, selectedCompareTargetId: sessionId } }));
    },
    stream: createIdleStreamState(),
    submitAnswer: async ({ answer, questionId }) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      const answerText = answer ?? get().drafts.answerTextByQuestionId[questionId] ?? "";
      set({ action: { error: null, kind: "answer", state: "pending" } });
      try {
        await apiClient.submitAnswer({ answer: answerText, questionId, sessionId });
        if (currentActionRequestId === actionRequestId) {
          set((state) => {
            const remainingAnswers = { ...state.drafts.answerTextByQuestionId };
            delete remainingAnswers[questionId];
            return {
              action: { error: null, kind: "answer", state: "succeeded" },
              drafts: { ...state.drafts, answerTextByQuestionId: remainingAnswers },
            };
          });
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "answer", state: "failed" } });
        }
      }
    },
    submitPrompt: async (text) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      const prompt = text ?? get().drafts.composerText;
      set({ action: { error: null, kind: "prompt", state: "pending" } });
      try {
        await apiClient.submitMessage({ sessionId, text: prompt });
        if (currentActionRequestId === actionRequestId) {
          set((state) => ({
            action: { error: null, kind: "prompt", state: "succeeded" },
            drafts: { ...state.drafts, composerText: "" },
          }));
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "prompt", state: "failed" } });
        }
      }
    },
  }));
}

function createDefaultConsoleFilters(): ConsoleFilters {
  return { queue: "all", sort: "priority", status: null };
}

function createEmptyDraftState(): DraftState {
  return {
    answerTextByQuestionId: {},
    composerText: "",
    forkLabel: "",
    selectedCompareTargetId: null,
  };
}

function createIdleActionStatus(): ActionStatus {
  return { error: null, kind: null, state: "idle" };
}

function createIdleStreamState(): SessionStreamState {
  return { error: null, lastSequence: 0, retryCount: 0, status: "historical_snapshot" };
}

function toAggregateQuery(filters: ConsoleFilters): SessionAggregateQuery {
  return {
    queue: filters.queue === "all" ? null : filters.queue,
    sort: filters.sort,
    status: filters.status,
  };
}

function requireSelectedSessionId(data: DashboardState): string {
  if (data.sessionId === null) {
    throw new Error("No selected session is loaded.");
  }
  return data.sessionId;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected Glassbox dashboard error.";
}
