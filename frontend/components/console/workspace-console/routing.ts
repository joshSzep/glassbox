"use client";

import { useEffect, useState } from "react";

import {
  buildAppRoute,
  createDefaultAppRoute,
  parseAppRoute,
  type AppRouteState,
} from "@/routing/app-route";

import type { WorkspaceConsoleStores } from "./types";

export function useWorkspaceConsoleRouting({
  branchSearchStore,
  consoleStore,
  knowledgeStore,
  sessionStore,
  taskStore,
}: WorkspaceConsoleStores) {
  const [route, setRoute] = useState<AppRouteState>(createDefaultAppRoute);

  useEffect(() => {
    const syncFromLocation = () => {
      const nextRoute = parseAppRoute(window.location.href);
      setRoute(nextRoute);
      loadRouteSurface(nextRoute, {
        branchSearchStore,
        consoleStore,
        knowledgeStore,
        sessionStore,
        taskStore,
      });
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);
    return () => window.removeEventListener("popstate", syncFromLocation);
  }, [branchSearchStore, consoleStore, knowledgeStore, sessionStore, taskStore]);

  const navigate = (nextRoute: AppRouteState) => {
    setRoute(nextRoute);
    window.history.pushState(null, "", buildAppRoute(nextRoute));
  };

  const refreshSelectedSession = async () => {
    const sessionId = sessionStore.getState().data.sessionId;
    if (sessionId !== null) {
      await sessionStore.getState().loadSession(sessionId);
    }
    void consoleStore.getState().loadAggregate();
  };

  return { navigate, refreshSelectedSession, route };
}

function loadRouteSurface(
  nextRoute: AppRouteState,
  {
    branchSearchStore,
    consoleStore,
    knowledgeStore,
    sessionStore,
    taskStore,
  }: WorkspaceConsoleStores,
) {
  void consoleStore.getState().loadAggregate({ queue: nextRoute.queue });
  if (nextRoute.surface === "tasks") {
    branchSearchStore.getState().reset();
    knowledgeStore.getState().reset();
    sessionStore.getState().resetForRoute(null);
    void (async () => {
      await taskStore.getState().loadTaskPage({ queue: nextRoute.taskQueue });
      if (nextRoute.selectedTaskId !== null) {
        await taskStore.getState().selectTask(nextRoute.selectedTaskId);
      }
    })();
  } else if (nextRoute.surface === "memory") {
    branchSearchStore.getState().reset();
    sessionStore.getState().resetForRoute(null);
    taskStore.getState().reset();
    void knowledgeStore.getState().loadMemoryPage();
  } else if (nextRoute.surface === "repository") {
    branchSearchStore.getState().reset();
    sessionStore.getState().resetForRoute(null);
    taskStore.getState().reset();
    void (async () => {
      await knowledgeStore.getState().loadRepositoryStatus();
      await knowledgeStore.getState().searchRepositoryIndex();
    })();
  } else if (nextRoute.surface === "branches") {
    knowledgeStore.getState().reset();
    sessionStore.getState().resetForRoute(null);
    taskStore.getState().reset();
    void branchSearchStore.getState().loadBranchSearchPage();
  } else if (nextRoute.selectedSessionId !== null) {
    branchSearchStore.getState().reset();
    knowledgeStore.getState().reset();
    taskStore.getState().reset();
    void (async () => {
      await sessionStore.getState().loadSession(nextRoute.selectedSessionId as string);
      if (nextRoute.compareSessionId !== null) {
        await sessionStore.getState().loadCompareSession(nextRoute.compareSessionId);
      }
    })();
  } else {
    branchSearchStore.getState().reset();
    knowledgeStore.getState().reset();
    taskStore.getState().reset();
    sessionStore.getState().resetForRoute(null);
  }
}
