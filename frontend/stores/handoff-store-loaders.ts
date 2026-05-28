import type { StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient } from "@/api/client";
import type { HandoffStoreState } from "@/stores/handoff-store";
import { needsSourceId, sourceIdForRequest } from "@/stores/handoff-store-drafts";
import { runHandoffAction } from "@/stores/handoff-store-package-actions";
import { requireSelectedRecord } from "@/stores/handoff-store-selectors";
import type { createRequestTracker } from "@/stores/store-actions";
import { errorMessage } from "@/stores/store-actions";

const HANDOFF_PAGE_SIZE = 100;

export function createHandoffLoaders({
  apiClient,
  get,
  listRequests,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: StoreApi<HandoffStoreState>["getState"];
  listRequests: ReturnType<typeof createRequestTracker>;
  set: StoreApi<HandoffStoreState>["setState"];
}) {
  return {
    loadGuidance: async () => {
      const record = requireSelectedRecord(get().detail);
      await runHandoffAction({
        action: async () => {
          const response = await apiClient.getHandoffGuidance(
            record.record.session_id,
            record.record.package_id,
          );
          set((state) => ({ detail: { ...state.detail, guidance: response } }));
        },
        kind: "guidance",
        set,
      });
    },
    loadHandoffs: async (query: { includeArchived?: boolean; sessionId?: string | null } = {}) => {
      const currentRequestId = listRequests.next();
      set((state) => ({
        list: { ...state.list, error: null, loadState: "loading" },
      }));
      try {
        const page = await apiClient.listHandoffs({
          include_archived: query.includeArchived ?? false,
          limit: HANDOFF_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set({
          list: {
            error: null,
            items: page.items ?? [],
            loadState: "loaded",
          },
        });
      } catch (error) {
        if (!listRequests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          list: { ...state.list, error: errorMessage(error), loadState: "failed" },
        }));
      }
    },
    loadReadiness: async () => {
      await runHandoffAction({
        action: async () => {
          const drafts = get().drafts;
          const response = await apiClient.getHandoffReadiness({
            intent: drafts.intent,
            source_id: needsSourceId(drafts.sourceKind) ? sourceIdForRequest(drafts) : undefined,
            source_kind: drafts.sourceKind,
          });
          set((state) => ({ detail: { ...state.detail, readiness: response } }));
        },
        kind: "readiness",
        set,
      });
    },
  } satisfies Pick<HandoffStoreState, "loadGuidance" | "loadHandoffs" | "loadReadiness">;
}
