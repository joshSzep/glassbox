import { createStore, type StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
import { createSessionEventStream } from "@/api/sse";
import {
  clearCompareSession,
  createDashboardState,
  hydrateCompareSession,
  hydrateSelectedSession,
} from "@/state/session-state";
import {
  abandonToolAttemptAction,
  forkSessionAction,
  requestCancellationAction,
  resolveApprovalAction,
  retryToolAttemptAction,
  submitAnswerAction,
  submitPromptAction,
} from "@/stores/session-store-actions";
import { createEmptyDraftState, withAnswerTextDraft } from "@/stores/session-store-drafts";
import {
  createIdleDetailPageState,
  createLoadingDetailPageState,
  DETAIL_PAGE_SIZE,
  loadDetailPage,
  pageStatusFromResponse,
} from "@/stores/session-store-pagination";
import {
  createIdleStreamState,
  createSessionStreamController,
} from "@/stores/session-store-stream";
import type { SessionEventStreamFactory, SessionStoreState } from "@/stores/session-store-types";
import { createIdleActionStatus, createRequestTracker, errorMessage } from "@/stores/store-actions";

export type {
  ActionKind,
  ActionStatus,
  DetailPageKind,
  DetailPageState,
  DetailPageStatus,
  DraftState,
  SessionEventStreamFactory,
  SessionEventStreamHandle,
  SessionStoreState,
} from "@/stores/session-store-types";

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

  return createStore<SessionStoreState>((set, get) => {
    const actionContext = { actionRequests, apiClient, get, set };
    const streamController = createSessionStreamController({
      createEventStream,
      get,
      set,
    });

    return {
      action: createIdleActionStatus(),
      applyStreamEnvelope: streamController.applyStreamEnvelope,
      clearCompareSession: () => {
        compareRequests.invalidate();
        set((state) => ({
          data: clearCompareSession(state.data),
          drafts: { ...state.drafts, selectedCompareTargetId: null },
        }));
      },
      connectStream: streamController.connectStream,
      data: createDashboardState(),
      detailPages: createIdleDetailPageState(),
      disconnectStream: streamController.disconnectStream,
      drafts: createEmptyDraftState(),
      error: null,
      forkSession: (input = {}) => forkSessionAction(actionContext, input),
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
        streamController.closeStream();
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
      abandonToolAttempt: (input) => abandonToolAttemptAction(actionContext, input),
      requestCancellation: () => requestCancellationAction(actionContext),
      resetForRoute: (sessionId = null) => {
        sessionRequests.invalidate();
        compareRequests.invalidate();
        actionRequests.invalidate();
        streamController.closeStream();
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
      resolveApproval: (input) => resolveApprovalAction(actionContext, input),
      setAnswerText: (questionId, text) => {
        set((state) => ({
          drafts: withAnswerTextDraft(state.drafts, questionId, text),
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
      submitAnswer: (input) => submitAnswerAction(actionContext, input),
      submitPrompt: (text) => submitPromptAction(actionContext, text),
      retryToolAttempt: (input) => retryToolAttemptAction(actionContext, input),
    };
  });
}
