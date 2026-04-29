import { createStore, type StoreApi } from "zustand/vanilla";

import type { GlassboxApiClient, SessionAggregateQuery } from "@/api/client";
import {
  createDashboardState,
  hydrateSessionAggregate,
  type DashboardState,
} from "@/state/session-state";
import { createRequestTracker, errorMessage, type LoadState } from "@/stores/store-actions";

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

export function createConsoleStore(apiClient: GlassboxApiClient): StoreApi<ConsoleStoreState> {
  const requests = createRequestTracker();

  return createStore<ConsoleStoreState>((set, get) => ({
    data: createDashboardState(),
    error: null,
    filters: createDefaultConsoleFilters(),
    loadAggregate: async (query = {}) => {
      const currentRequestId = requests.next();
      const filters = { ...get().filters, ...query };
      set({ error: null, filters, loadState: "loading" });

      try {
        const aggregate = await apiClient.getSessionAggregate(toAggregateQuery(filters));
        if (!requests.isCurrent(currentRequestId)) {
          return;
        }
        set((state) => ({
          data: hydrateSessionAggregate(state.data, aggregate),
          error: null,
          loadState: "loaded",
        }));
      } catch (error) {
        if (!requests.isCurrent(currentRequestId)) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    reset: () => {
      requests.invalidate();
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

function createDefaultConsoleFilters(): ConsoleFilters {
  return { queue: "all", sort: "priority", status: null };
}

function toAggregateQuery(filters: ConsoleFilters): SessionAggregateQuery {
  return {
    queue: filters.queue === "all" ? null : filters.queue,
    sort: filters.sort,
    status: filters.status,
  };
}
