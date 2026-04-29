import { createStore, type StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
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
  type DashboardState,
} from "@/state/session-state";
import {
  createFailedActionStatus,
  createIdleActionStatus,
  createPendingActionStatus,
  createRequestTracker,
  createSucceededActionStatus,
  errorMessage,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type ActionKind = "answer" | "approval" | "cancel" | "fork" | "prompt";
export type DetailPageKind = "events" | "metrics" | "transcript";
export type ActionStatus = StoreActionStatus<ActionKind>;

export type DetailPageStatus = {
  error: string | null;
  hasMore: boolean;
  nextCursor: number | null;
  state: LoadState;
};

export type DetailPageState = Record<DetailPageKind, DetailPageStatus>;

export type DraftState = {
  answerTextByQuestionId: Record<string, string>;
  composerText: string;
  forkLabel: string;
  selectedCompareTargetId: string | null;
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
  detailPages: DetailPageState;
  disconnectStream: () => void;
  drafts: DraftState;
  error: string | null;
  forkSession: (input?: {
    branchLabel?: string | null;
    turnId?: string | null;
  }) => Promise<string | null>;
  loadCompareSession: (sessionId: string) => Promise<void>;
  loadMoreEvents: () => Promise<void>;
  loadMoreMetrics: () => Promise<void>;
  loadMoreTranscript: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  loadState: LoadState;
  requestCancellation: () => Promise<void>;
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

const DETAIL_PAGE_SIZE = 80;

export function createSessionStore({
  apiClient,
  createEventStream = createSessionEventStream,
}: {
  apiClient: GlassboxApiClient;
  createEventStream?: SessionEventStreamFactory;
}): StoreApi<SessionStoreState> {
  const sessionRequests = createRequestTracker();
  const compareRequests = createRequestTracker();
  const actionRequests = createRequestTracker();
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
      compareRequests.invalidate();
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
    detailPages: createIdleDetailPageState(),
    disconnectStream: () => {
      closeStream();
      set({ stream: createIdleStreamState() });
    },
    drafts: createEmptyDraftState(),
    error: null,
    forkSession: async (input = {}) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = actionRequests.next();
      set({ action: createPendingActionStatus("fork") });
      try {
        const fork = await apiClient.forkSession({
          branchLabel: (input.branchLabel ?? get().drafts.forkLabel) || null,
          sessionId,
          turnId: input.turnId ?? get().data.selectedForkTurnId,
        });
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set((state) => ({
            action: createSucceededActionStatus("fork"),
            drafts: { ...state.drafts, forkLabel: "" },
          }));
        }
        return fork.child_session_id;
      } catch (error) {
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createFailedActionStatus("fork", error) });
        }
        return null;
      }
    },
    loadCompareSession: async (sessionId) => {
      const currentRequestId = compareRequests.next();
      set((state) => ({
        data: { ...state.data, compareSession: null, compareSessionId: sessionId },
        drafts: { ...state.drafts, selectedCompareTargetId: sessionId },
      }));

      try {
        const snapshot = await apiClient.getCompareSessionSnapshot(sessionId);
        if (!compareRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({ data: hydrateCompareSession(state.data, snapshot) }));
      } catch (error) {
        if (!compareRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          action: { error: errorMessage(error), kind: null, state: "failed" },
          data: clearCompareSession(state.data),
        }));
      }
    },
    loadMoreEvents: async () => {
      await loadDetailPage({ apiClient, get, kind: "events", set });
    },
    loadMoreMetrics: async () => {
      await loadDetailPage({ apiClient, get, kind: "metrics", set });
    },
    loadMoreTranscript: async () => {
      await loadDetailPage({ apiClient, get, kind: "transcript", set });
    },
    loadSession: async (sessionId) => {
      const currentRequestId = sessionRequests.next();
      closeStream();
      set((state) => ({
        data: { ...state.data, selectedSessionId: sessionId },
        detailPages: createLoadingDetailPageState(),
        error: null,
        loadState: "loading",
        stream: createIdleStreamState(),
      }));

      try {
        const [snapshot, transcriptPage, eventPage, metricsPage] = await Promise.all([
          apiClient.getSessionSnapshot(sessionId),
          apiClient.getSessionTranscriptPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
          apiClient.getSessionEventLogPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
          apiClient.getSessionTurnMetricsPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
        ]);
        if (!sessionRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          data: {
            ...hydrateSelectedSession(state.data, snapshot),
            eventLog: eventPage.items.map((event) => ({
              event_type: event.event_type,
              sequence: event.sequence,
            })),
            transcript: transcriptPage.items,
            turnMetrics: metricsPage.items,
          },
          detailPages: {
            events: pageStatusFromResponse(eventPage.page),
            metrics: pageStatusFromResponse(metricsPage.page),
            transcript: pageStatusFromResponse(transcriptPage.page),
          },
          error: null,
          loadState: "loaded",
          stream: { ...state.stream, lastSequence: snapshot.last_sequence },
        }));
      } catch (error) {
        if (!sessionRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    requestCancellation: async () => {
      const data = get().data;
      const sessionId = requireSelectedSessionId(data);
      const currentActionRequestId = actionRequests.next();
      set({ action: createPendingActionStatus("cancel") });
      try {
        await apiClient.cancelTurn({
          reason: "operator requested cancellation from dashboard",
          sessionId,
          turnId: data.currentTurn?.turn_id ?? null,
        });
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createSucceededActionStatus("cancel") });
        }
      } catch (error) {
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createFailedActionStatus("cancel", error) });
        }
      }
    },
    resetForRoute: (sessionId = null) => {
      sessionRequests.invalidate();
      compareRequests.invalidate();
      actionRequests.invalidate();
      closeStream();
      set((state) => ({
        action: createIdleActionStatus(),
        data: { ...createDashboardState(), selectedSessionId: sessionId },
        detailPages: createIdleDetailPageState(),
        drafts: state.drafts,
        error: null,
        loadState: sessionId === null ? "idle" : "loading",
        stream: createIdleStreamState(),
      }));
    },
    resolveApproval: async ({ approvalId, decision }) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = actionRequests.next();
      set({ action: createPendingActionStatus("approval") });
      try {
        await apiClient.resolveApproval({ approvalId, decision, sessionId });
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createSucceededActionStatus("approval") });
        }
      } catch (error) {
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createFailedActionStatus("approval", error) });
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
      const currentActionRequestId = actionRequests.next();
      const answerText = answer ?? get().drafts.answerTextByQuestionId[questionId] ?? "";
      set({ action: createPendingActionStatus("answer") });
      try {
        await apiClient.submitAnswer({ answer: answerText, questionId, sessionId });
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set((state) => {
            const remainingAnswers = { ...state.drafts.answerTextByQuestionId };
            delete remainingAnswers[questionId];
            return {
              action: createSucceededActionStatus("answer"),
              drafts: { ...state.drafts, answerTextByQuestionId: remainingAnswers },
            };
          });
        }
      } catch (error) {
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createFailedActionStatus("answer", error) });
        }
      }
    },
    submitPrompt: async (text) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = actionRequests.next();
      const prompt = text ?? get().drafts.composerText;
      set({ action: createPendingActionStatus("prompt") });
      try {
        await apiClient.submitMessage({ sessionId, text: prompt });
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set((state) => ({
            action: createSucceededActionStatus("prompt"),
            drafts: { ...state.drafts, composerText: "" },
          }));
        }
      } catch (error) {
        if (actionRequests.isCurrent(currentActionRequestId)) {
          set({ action: createFailedActionStatus("prompt", error) });
        }
      }
    },
  }));
}

function createEmptyDraftState(): DraftState {
  return {
    answerTextByQuestionId: {},
    composerText: "",
    forkLabel: "",
    selectedCompareTargetId: null,
  };
}

function createIdleDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("idle"),
    metrics: createDetailPageStatus("idle"),
    transcript: createDetailPageStatus("idle"),
  };
}

function createLoadingDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("loading"),
    metrics: createDetailPageStatus("loading"),
    transcript: createDetailPageStatus("loading"),
  };
}

function createDetailPageStatus(state: LoadState): DetailPageStatus {
  return { error: null, hasMore: false, nextCursor: null, state };
}

function pageStatusFromResponse(page: {
  has_more: boolean;
  next_cursor: number | null;
}): DetailPageStatus {
  return {
    error: null,
    hasMore: page.has_more,
    nextCursor: page.next_cursor,
    state: "loaded",
  };
}

async function loadDetailPage({
  apiClient,
  get,
  kind,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: StoreApi<SessionStoreState>["getState"];
  kind: DetailPageKind;
  set: StoreApi<SessionStoreState>["setState"];
}) {
  const state = get();
  const sessionId = requireSelectedSessionId(state.data);
  const currentPage = state.detailPages[kind];
  if (!currentPage.hasMore || currentPage.nextCursor === null || currentPage.state === "loading") {
    return;
  }

  set((nextState) => ({
    detailPages: {
      ...nextState.detailPages,
      [kind]: { ...nextState.detailPages[kind], error: null, state: "loading" },
    },
  }));

  try {
    if (kind === "transcript") {
      const page = await apiClient.getSessionTranscriptPage(sessionId, {
        cursor: currentPage.nextCursor,
        limit: DETAIL_PAGE_SIZE,
      });
      set((nextState) => ({
        data: { ...nextState.data, transcript: [...nextState.data.transcript, ...page.items] },
        detailPages: { ...nextState.detailPages, transcript: pageStatusFromResponse(page.page) },
      }));
      return;
    }
    if (kind === "events") {
      const page = await apiClient.getSessionEventLogPage(sessionId, {
        cursor: currentPage.nextCursor,
        limit: DETAIL_PAGE_SIZE,
      });
      set((nextState) => ({
        data: {
          ...nextState.data,
          eventLog: [
            ...nextState.data.eventLog,
            ...page.items.map((event) => ({
              event_type: event.event_type,
              sequence: event.sequence,
            })),
          ],
        },
        detailPages: { ...nextState.detailPages, events: pageStatusFromResponse(page.page) },
      }));
      return;
    }

    const page = await apiClient.getSessionTurnMetricsPage(sessionId, {
      cursor: currentPage.nextCursor,
      limit: DETAIL_PAGE_SIZE,
    });
    set((nextState) => ({
      data: { ...nextState.data, turnMetrics: [...nextState.data.turnMetrics, ...page.items] },
      detailPages: { ...nextState.detailPages, metrics: pageStatusFromResponse(page.page) },
    }));
  } catch (error) {
    set((nextState) => ({
      detailPages: {
        ...nextState.detailPages,
        [kind]: {
          ...nextState.detailPages[kind],
          error: errorMessage(error),
          state: "failed",
        },
      },
    }));
  }
}

function createIdleStreamState(): SessionStreamState {
  return { error: null, lastSequence: 0, retryCount: 0, status: "historical_snapshot" };
}

function requireSelectedSessionId(data: DashboardState): string {
  if (data.sessionId === null) {
    throw new Error("No selected session is loaded.");
  }
  return data.sessionId;
}
