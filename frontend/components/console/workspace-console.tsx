"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "zustand";

import { createGlassboxApiClient } from "@/api/client";
import { SessionInspector } from "@/components/console/session-inspector";
import { WorkspaceOverview } from "@/components/console/workspace-overview";
import {
  buildAppRoute,
  createDefaultAppRoute,
  openLineageTargetRoute,
  parseAppRoute,
  selectQueueRoute,
  selectSessionRoute,
  setCompareRoute,
  setInspectorTabRoute,
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
        void (async () => {
          await sessionStore.getState().loadSession(nextRoute.selectedSessionId as string);
          if (nextRoute.compareSessionId !== null) {
            await sessionStore.getState().loadCompareSession(nextRoute.compareSessionId);
          }
        })();
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

  useEffect(() => {
    if (sessionState.loadState !== "loaded" || sessionState.data.sessionId === null) {
      return;
    }

    sessionStore.getState().connectStream();
    return () => sessionStore.getState().disconnectStream();
  }, [sessionState.data.sessionId, sessionState.loadState, sessionStore]);

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
            detailPages={sessionState.detailPages}
            drafts={sessionState.drafts}
            error={sessionState.error}
            loadState={sessionState.loadState}
            onAnswerTextChange={(questionId, text) =>
              sessionStore.getState().setAnswerText(questionId, text)
            }
            onClearCompare={() => {
              const nextRoute = setCompareRoute(route, null);
              navigate(nextRoute);
              sessionStore.getState().clearCompareSession();
            }}
            onCompareSession={(sessionId) => {
              const nextRoute = setCompareRoute(route, sessionId);
              navigate(nextRoute);
              void sessionStore.getState().loadCompareSession(sessionId);
            }}
            onFork={(input) => {
              void (async () => {
                const childSessionId = await sessionStore.getState().forkSession(input);
                if (childSessionId !== null) {
                  const nextRoute = openLineageTargetRoute(route, childSessionId);
                  navigate(nextRoute);
                  await sessionStore.getState().loadSession(childSessionId);
                  void consoleStore.getState().loadAggregate();
                }
              })();
            }}
            onForkLabelChange={(text) => sessionStore.getState().setForkLabel(text)}
            onLoadMoreEvents={() => {
              void sessionStore.getState().loadMoreEvents();
            }}
            onLoadMoreMetrics={() => {
              void sessionStore.getState().loadMoreMetrics();
            }}
            onLoadMoreTranscript={() => {
              void sessionStore.getState().loadMoreTranscript();
            }}
            onOpenSession={(sessionId) => {
              const nextRoute = openLineageTargetRoute(route, sessionId);
              navigate(nextRoute);
              sessionStore.getState().clearCompareSession();
              void sessionStore.getState().loadSession(sessionId);
            }}
            onPromptChange={(text) => sessionStore.getState().setComposerText(text)}
            onRequestCancellation={() => {
              void (async () => {
                await sessionStore.getState().requestCancellation();
                await refreshSelectedSession();
              })();
            }}
            onResolveApproval={(input) => {
              void (async () => {
                await sessionStore.getState().resolveApproval(input);
                await refreshSelectedSession();
              })();
            }}
            onSelectTab={(tab) => navigate(setInspectorTabRoute(route, tab))}
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
      stream={sessionState.stream}
    />
  );
}
