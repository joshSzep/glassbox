"use client";

import { useEffect, useMemo } from "react";
import { useStore } from "zustand";

import { createGlassboxApiClient } from "@/api/client";
import { WorkspaceOverview } from "@/components/console/workspace-overview";
import { parseAppRoute, selectQueueRoute, type AppQueue } from "@/routing/app-route";
import { createConsoleStore } from "@/stores/dashboard-stores";

export function WorkspaceConsole() {
  const store = useMemo(() => createConsoleStore(createGlassboxApiClient()), []);
  const state = useStore(store);

  useEffect(() => {
    const route = parseAppRoute(window.location.href);
    void store.getState().loadAggregate({ queue: route.queue });
  }, [store]);

  return (
    <WorkspaceOverview
      data={state.data}
      error={state.error}
      loadState={state.loadState}
      onRefresh={() => void store.getState().loadAggregate()}
      onSelectQueue={(queue) => {
        const nextRoute = selectQueueRoute(parseAppRoute(window.location.href), queue as AppQueue);
        window.history.pushState(
          null,
          "",
          nextRoute.queue === "all" ? "/app" : `/app/queues/${nextRoute.queue}`,
        );
        void store.getState().selectQueue(queue);
      }}
      selectedQueue={state.filters.queue}
    />
  );
}
