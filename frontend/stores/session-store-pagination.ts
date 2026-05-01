import type { GlassboxApiClient } from "@/api/client";
import type { LoadState } from "@/stores/store-actions";
import { errorMessage } from "@/stores/store-actions";
import { requireSelectedSessionId } from "@/stores/session-store-shared";
import type {
  DetailPageKind,
  DetailPageState,
  DetailPageStatus,
  SessionStoreGet,
  SessionStoreSet,
} from "@/stores/session-store-types";

export const DETAIL_PAGE_SIZE = 80;

export function createIdleDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("idle"),
    metrics: createDetailPageStatus("idle"),
    transcript: createDetailPageStatus("idle"),
  };
}

export function createLoadingDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("loading"),
    metrics: createDetailPageStatus("loading"),
    transcript: createDetailPageStatus("loading"),
  };
}

function createDetailPageStatus(state: LoadState): DetailPageStatus {
  return { error: null, hasMore: false, nextCursor: null, state };
}

export function pageStatusFromResponse(page: {
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

export async function loadDetailPage({
  apiClient,
  get,
  kind,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: SessionStoreGet;
  kind: DetailPageKind;
  set: SessionStoreSet;
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
