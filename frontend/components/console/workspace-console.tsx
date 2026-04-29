"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "zustand";

import { createGlassboxApiClient } from "@/api/client";
import { KnowledgeAutonomyConsole } from "@/components/console/knowledge-autonomy-console";
import { SessionInspector } from "@/components/console/session-inspector";
import { TaskAutonomyConsole } from "@/components/console/task-autonomy-console";
import { WorkspaceOverview } from "@/components/console/workspace-overview";
import {
  buildAppRoute,
  createDefaultAppRoute,
  openLineageTargetRoute,
  parseAppRoute,
  selectQueueRoute,
  selectSessionRoute,
  selectTaskQueueRoute,
  selectTaskRoute,
  setCompareRoute,
  setInspectorTabRoute,
  type AppQueue,
  type AppRouteState,
} from "@/routing/app-route";
import {
  createConsoleStore,
  createKnowledgeStore,
  createSessionStore,
  createTaskStore,
} from "@/stores/dashboard-stores";

export function WorkspaceConsole() {
  const apiClient = useMemo(() => createGlassboxApiClient(), []);
  const consoleStore = useMemo(() => createConsoleStore(apiClient), [apiClient]);
  const knowledgeStore = useMemo(() => createKnowledgeStore(apiClient), [apiClient]);
  const sessionStore = useMemo(() => createSessionStore({ apiClient }), [apiClient]);
  const taskStore = useMemo(() => createTaskStore(apiClient), [apiClient]);
  const consoleState = useStore(consoleStore);
  const knowledgeState = useStore(knowledgeStore);
  const sessionState = useStore(sessionStore);
  const taskState = useStore(taskStore);
  const [route, setRoute] = useState<AppRouteState>(createDefaultAppRoute);

  useEffect(() => {
    const syncFromLocation = () => {
      const nextRoute = parseAppRoute(window.location.href);
      setRoute(nextRoute);
      void consoleStore.getState().loadAggregate({ queue: nextRoute.queue });
      if (nextRoute.surface === "tasks") {
        knowledgeStore.getState().reset();
        sessionStore.getState().resetForRoute(null);
        void (async () => {
          await taskStore.getState().loadTaskPage({ queue: nextRoute.taskQueue });
          if (nextRoute.selectedTaskId !== null) {
            await taskStore.getState().selectTask(nextRoute.selectedTaskId);
          }
        })();
      } else if (nextRoute.surface === "memory") {
        sessionStore.getState().resetForRoute(null);
        taskStore.getState().reset();
        void knowledgeStore.getState().loadMemoryPage();
      } else if (nextRoute.surface === "repository") {
        sessionStore.getState().resetForRoute(null);
        taskStore.getState().reset();
        void (async () => {
          await knowledgeStore.getState().loadRepositoryStatus();
          await knowledgeStore.getState().searchRepositoryIndex();
        })();
      } else if (nextRoute.selectedSessionId !== null) {
        knowledgeStore.getState().reset();
        taskStore.getState().reset();
        void (async () => {
          await sessionStore.getState().loadSession(nextRoute.selectedSessionId as string);
          if (nextRoute.compareSessionId !== null) {
            await sessionStore.getState().loadCompareSession(nextRoute.compareSessionId);
          }
        })();
      } else {
        knowledgeStore.getState().reset();
        taskStore.getState().reset();
        sessionStore.getState().resetForRoute(null);
      }
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);
    return () => window.removeEventListener("popstate", syncFromLocation);
  }, [consoleStore, knowledgeStore, sessionStore, taskStore]);

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

  if (route.surface === "tasks") {
    return (
      <TaskAutonomyConsole
        action={taskState.action}
        detail={taskState.detail}
        onAdjustBudget={(input) => {
          void taskStore.getState().adjustTaskBudget(input);
        }}
        onApprovePlan={() => {
          void taskStore.getState().approvePlan();
        }}
        onCancelBackgroundJob={(jobId) => {
          void taskStore.getState().cancelBackgroundJob({ jobId, reason: "dashboard request" });
        }}
        onCancelTask={() => {
          void taskStore.getState().cancelTask({ reason: "dashboard request" });
        }}
        onContinueTask={() => {
          void taskStore.getState().continueTask({ reason: "dashboard bounded continuation" });
        }}
        onLoadMoreEvents={() => {
          void taskStore.getState().loadMoreTaskEvents();
        }}
        onPauseTask={() => {
          void taskStore.getState().pauseTask({ detail: "dashboard pause" });
        }}
        onRefresh={() => {
          void taskStore.getState().applyTaskUpdate();
        }}
        onResumeTask={() => {
          void taskStore.getState().resumeTask({ reason: "dashboard resume" });
        }}
        onSelectQueue={(queue) => {
          const nextRoute = selectTaskQueueRoute(parseAppRoute(window.location.href), queue);
          navigate(nextRoute);
          void taskStore.getState().setQueueFilter(queue);
        }}
        onSelectSession={(sessionId) => {
          const nextRoute = selectSessionRoute(route, sessionId);
          navigate(nextRoute);
          taskStore.getState().reset();
          void sessionStore.getState().loadSession(sessionId);
        }}
        onSelectTask={(taskId) => {
          const nextRoute = selectTaskRoute(route, taskId);
          navigate(nextRoute);
          void taskStore.getState().selectTask(taskId);
        }}
        queue={taskState.queue}
      />
    );
  }

  if (route.surface === "memory" || route.surface === "repository") {
    const anchorSessionId =
      consoleState.data.sessionIndex.find((session) => session.has_active_turn)?.session_id ??
      consoleState.data.sessionIndex[0]?.session_id ??
      null;
    return (
      <KnowledgeAutonomyConsole
        action={knowledgeState.action}
        anchorSessionId={anchorSessionId}
        memory={knowledgeState.memory}
        onConfirmMemory={(memoryId) => {
          void knowledgeStore.getState().confirmMemory({ memoryId, reason: "dashboard confirm" });
        }}
        onInvalidateMemory={(memoryId) => {
          if (!confirmAction("Invalidate this memory entry?")) {
            return;
          }
          void knowledgeStore
            .getState()
            .invalidateMemory({ memoryId, reason: "dashboard invalidation" });
        }}
        onMemoryFilter={(filter) => {
          void knowledgeStore.getState().setMemoryFilter(filter);
        }}
        onMemoryQuery={(query) => {
          void knowledgeStore.getState().setMemoryQuery(query);
        }}
        onPreviewPruneMemory={(memoryId) => {
          void knowledgeStore
            .getState()
            .previewPruneMemory({ memoryId, reason: "dashboard prune preview" });
        }}
        onPruneMemory={(memoryId) => {
          if (!confirmAction("Prune this memory entry from active retrieval?")) {
            return;
          }
          void knowledgeStore.getState().pruneMemory({ memoryId, reason: "dashboard prune" });
        }}
        onRebuildRepositoryIndex={(input) => {
          void knowledgeStore.getState().rebuildRepositoryIndex(input);
        }}
        onRefresh={() => {
          if (route.surface === "memory") {
            void knowledgeStore.getState().loadMemoryPage();
            return;
          }
          void (async () => {
            await knowledgeStore.getState().loadRepositoryStatus();
            await knowledgeStore.getState().searchRepositoryIndex();
          })();
        }}
        onRepositoryQuery={(query) => {
          void knowledgeStore.getState().setRepositoryQuery(query);
        }}
        onSelectMemory={(memoryId) => {
          void knowledgeStore.getState().selectMemory(memoryId);
        }}
        onSelectRepositoryEntry={(entryId) => {
          void knowledgeStore.getState().selectRepositoryEntry(entryId);
        }}
        repository={knowledgeState.repository}
        surface={route.surface}
      />
    );
  }

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

function confirmAction(message: string): boolean {
  if (typeof window === "undefined" || typeof window.confirm !== "function") {
    return true;
  }
  return window.confirm(message);
}
