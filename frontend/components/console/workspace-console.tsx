"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "zustand";

import { createGlassboxApiClient } from "@/api/client";
import { SessionInspector } from "@/components/console/session-inspector";
import { WorkspaceOverview } from "@/components/console/workspace-overview";
import {
  buildAppRoute,
  createDefaultAppRoute,
  parseAppRoute,
  selectQueueRoute,
  selectSessionRoute,
  type AppQueue,
  type AppRouteState,
} from "@/routing/app-route";
import { createConsoleStore, createSessionStore } from "@/stores/dashboard-stores";

export function WorkspaceConsole() {
  const apiClient = useMemo(() => createGlassboxApiClient(), []);
  const consoleStore = useMemo(() => createConsoleStore(apiClient), [apiClient]);
  const sessionStore = useMemo(() => createSessionStore({ apiClient }), [apiClient]);
  const consoleState = useStore(consoleStore);
  const sessionState = useStore(sessionStore);
  const [route, setRoute] = useState<AppRouteState>(createDefaultAppRoute);

  useEffect(() => {
    const syncFromLocation = () => {
      const nextRoute = parseAppRoute(window.location.href);
      setRoute(nextRoute);
      void consoleStore.getState().loadAggregate({ queue: nextRoute.queue });
      if (nextRoute.selectedSessionId !== null) {
        void sessionStore.getState().loadSession(nextRoute.selectedSessionId);
      } else {
        sessionStore.getState().resetForRoute(null);
      }
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);
    return () => window.removeEventListener("popstate", syncFromLocation);
  }, [consoleStore, sessionStore]);

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

  return (
    <WorkspaceOverview
      data={consoleState.data}
      error={consoleState.error}
      inspector={
        route.selectedSessionId === null ? undefined : (
          <SessionInspector
            action={sessionState.action}
            activeTab={route.tab}
            data={sessionState.data}
            drafts={sessionState.drafts}
            error={sessionState.error}
            loadState={sessionState.loadState}
            onAnswerTextChange={(questionId, text) =>
              sessionStore.getState().setAnswerText(questionId, text)
            }
            onFork={(input) => {
              void (async () => {
                const childSessionId = await sessionStore.getState().forkSession(input);
                if (childSessionId !== null) {
                  const nextRoute = selectSessionRoute(route, childSessionId);
                  navigate(nextRoute);
                  await sessionStore.getState().loadSession(childSessionId);
                  void consoleStore.getState().loadAggregate();
                }
              })();
            }}
            onForkLabelChange={(text) => sessionStore.getState().setForkLabel(text)}
            onPromptChange={(text) => sessionStore.getState().setComposerText(text)}
            onResolveApproval={(input) => {
              void (async () => {
                await sessionStore.getState().resolveApproval(input);
                await refreshSelectedSession();
              })();
            }}
            onSubmitAnswer={(questionId) => {
              void (async () => {
                await sessionStore.getState().submitAnswer({ questionId });
                await refreshSelectedSession();
              })();
            }}
            onSubmitPrompt={() => {
              void (async () => {
                await sessionStore.getState().submitPrompt();
                await refreshSelectedSession();
              })();
            }}
            queue={route.queue}
            stream={sessionState.stream}
          />
        )
      }
      loadState={consoleState.loadState}
      onRefresh={() => void consoleStore.getState().loadAggregate()}
      onSelectQueue={(queue) => {
        const nextRoute = selectQueueRoute(parseAppRoute(window.location.href), queue as AppQueue);
        navigate(nextRoute);
        sessionStore.getState().resetForRoute(null);
        void consoleStore.getState().selectQueue(queue);
      }}
      onSelectSession={(sessionId) => {
        const nextRoute = selectSessionRoute(route, sessionId);
        navigate(nextRoute);
        void sessionStore.getState().loadSession(sessionId);
      }}
      selectedQueue={consoleState.filters.queue}
      selectedSessionId={route.selectedSessionId}
    />
  );
}
