import {
  openLineageTargetRoute,
  parseAppRoute,
  selectChangesetRoute,
  selectChangesetSurfaceRoute,
  selectQueueRoute,
  selectSessionRoute,
  selectTaskQueueRoute,
  selectTaskRoute,
  setCompareRoute,
  setInspectorTabRoute,
  type AppQueue,
  type AppRouteState,
} from "@/routing/app-route";
import type { ConsoleFilters } from "@/stores/dashboard-stores";

import type { WorkspaceConsoleStores } from "./types";

type Navigate = (route: AppRouteState) => void;

export function taskConsoleActions({
  navigate,
  route,
  sessionStore,
  taskStore,
}: Pick<WorkspaceConsoleStores, "sessionStore" | "taskStore"> & {
  navigate: Navigate;
  route: AppRouteState;
}) {
  return {
    onAdjustBudget: (
      input: Parameters<ReturnType<typeof taskStore.getState>["adjustTaskBudget"]>[0],
    ) => {
      void taskStore.getState().adjustTaskBudget(input);
    },
    onApprovePlan: () => {
      void taskStore.getState().approvePlan();
    },
    onCancelBackgroundJob: (jobId: string) => {
      void taskStore.getState().cancelBackgroundJob({ jobId, reason: "dashboard request" });
    },
    onCancelTask: () => {
      void taskStore.getState().cancelTask({ reason: "dashboard request" });
    },
    onContinueTask: () => {
      void taskStore.getState().continueTask({ reason: "dashboard bounded continuation" });
    },
    onLoadMoreEvents: () => {
      void taskStore.getState().loadMoreTaskEvents();
    },
    onPauseTask: () => {
      void taskStore.getState().pauseTask({ detail: "dashboard pause" });
    },
    onRefresh: () => {
      void taskStore.getState().applyTaskUpdate();
    },
    onResumeTask: () => {
      void taskStore.getState().resumeTask({ reason: "dashboard resume" });
    },
    onSelectQueue: (
      queue: Parameters<ReturnType<typeof taskStore.getState>["setQueueFilter"]>[0],
    ) => {
      const nextRoute = selectTaskQueueRoute(parseAppRoute(window.location.href), queue);
      navigate(nextRoute);
      void taskStore.getState().setQueueFilter(queue);
    },
    onSelectSession: (sessionId: string) => {
      const nextRoute = selectSessionRoute(route, sessionId);
      navigate(nextRoute);
      taskStore.getState().reset();
      void sessionStore.getState().loadSession(sessionId);
    },
    onSelectTask: (taskId: string) => {
      const nextRoute = selectTaskRoute(route, taskId);
      navigate(nextRoute);
      void taskStore.getState().selectTask(taskId);
    },
  };
}

export function knowledgeConsoleActions({
  knowledgeStore,
  route,
}: Pick<WorkspaceConsoleStores, "knowledgeStore"> & {
  route: AppRouteState;
}) {
  return {
    onConfirmMemory: (memoryId: string) => {
      void knowledgeStore.getState().confirmMemory({ memoryId, reason: "dashboard confirm" });
    },
    onInvalidateMemory: (memoryId: string) => {
      if (!confirmAction("Invalidate this memory entry?")) {
        return;
      }
      void knowledgeStore
        .getState()
        .invalidateMemory({ memoryId, reason: "dashboard invalidation" });
    },
    onMemoryFilter: (
      filter: Parameters<ReturnType<typeof knowledgeStore.getState>["setMemoryFilter"]>[0],
    ) => {
      void knowledgeStore.getState().setMemoryFilter(filter);
    },
    onMemoryQuery: (query: string) => {
      void knowledgeStore.getState().setMemoryQuery(query);
    },
    onPreviewPruneMemory: (memoryId: string) => {
      void knowledgeStore
        .getState()
        .previewPruneMemory({ memoryId, reason: "dashboard prune preview" });
    },
    onPruneMemory: (memoryId: string) => {
      if (!confirmAction("Prune this memory entry from active retrieval?")) {
        return;
      }
      void knowledgeStore.getState().pruneMemory({ memoryId, reason: "dashboard prune" });
    },
    onRebuildRepositoryIndex: (
      input: Parameters<ReturnType<typeof knowledgeStore.getState>["rebuildRepositoryIndex"]>[0],
    ) => {
      void knowledgeStore.getState().rebuildRepositoryIndex(input);
    },
    onRefresh: () => {
      if (route.surface === "memory") {
        void knowledgeStore.getState().loadMemoryPage();
        return;
      }
      void (async () => {
        await knowledgeStore.getState().loadRepositoryStatus();
        await knowledgeStore.getState().searchRepositoryIndex();
      })();
    },
    onRepositoryQuery: (query: string) => {
      void knowledgeStore.getState().setRepositoryQuery(query);
    },
    onSelectMemory: (memoryId: string) => {
      void knowledgeStore.getState().selectMemory(memoryId);
    },
    onSelectRepositoryEntry: (entryId: string) => {
      void knowledgeStore.getState().selectRepositoryEntry(entryId);
    },
  };
}

export function branchSearchConsoleActions({
  branchSearchStore,
}: Pick<WorkspaceConsoleStores, "branchSearchStore">) {
  return {
    onMarkCandidate: (input: {
      action: "needs-review" | "reject" | "select";
      candidateId: string;
      searchId: string;
    }) => {
      if (!confirmAction(`Mark this candidate ${input.action}?`)) {
        return;
      }
      void branchSearchStore.getState().markCandidate({
        action: input.action,
        candidateId: input.candidateId,
        reason: `dashboard ${input.action}`,
        searchId: input.searchId,
      });
    },
    onRefresh: () => {
      void branchSearchStore.getState().loadBranchSearchPage();
      const selected = branchSearchStore.getState().detail.selectedSearchId;
      if (selected !== null) {
        void branchSearchStore.getState().selectBranchSearch(selected);
      }
    },
    onSelectSearch: (searchId: string) => {
      void branchSearchStore.getState().selectBranchSearch(searchId);
    },
  };
}

export function changesetConsoleActions({
  changesetStore,
  navigate,
  route,
}: Pick<WorkspaceConsoleStores, "changesetStore"> & {
  navigate: Navigate;
  route: AppRouteState;
}) {
  return {
    onRefresh: () => {
      void changesetStore.getState().loadChangesetPage();
      const selected = changesetStore.getState().detail.selectedChangesetId;
      if (selected !== null) {
        void changesetStore.getState().selectChangeset(selected);
      }
    },
    onRefreshChangeset: () => {
      if (!confirmAction("Refresh basic source evidence for this changeset?")) {
        return;
      }
      void changesetStore.getState().refreshChangeset();
    },
    onGenerateReviewBrief: () => {
      if (!confirmAction("Generate a reviewer-safe brief for this changeset?")) {
        return;
      }
      void changesetStore.getState().generateReviewBrief();
    },
    onSelectChangeset: (changesetId: string) => {
      navigate(selectChangesetRoute(route, changesetId));
      void changesetStore.getState().selectChangeset(changesetId);
    },
    onShowList: () => {
      navigate(selectChangesetSurfaceRoute(route));
      changesetStore.getState().reset();
      void changesetStore.getState().loadChangesetPage();
    },
  };
}

export function sessionInspectorActions({
  consoleStore,
  navigate,
  refreshSelectedSession,
  route,
  sessionStore,
}: Pick<WorkspaceConsoleStores, "consoleStore" | "sessionStore"> & {
  navigate: Navigate;
  refreshSelectedSession: () => Promise<void>;
  route: AppRouteState;
}) {
  return {
    onAbandonToolAttempt: (toolAttemptId: string) => {
      if (!confirmAction("Abandon this tool attempt?")) {
        return;
      }
      void (async () => {
        await sessionStore.getState().abandonToolAttempt({ toolAttemptId });
        await refreshSelectedSession();
      })();
    },
    onAnswerTextChange: (questionId: string, text: string) =>
      sessionStore.getState().setAnswerText(questionId, text),
    onClearCompare: () => {
      const nextRoute = setCompareRoute(route, null);
      navigate(nextRoute);
      sessionStore.getState().clearCompareSession();
    },
    onCompareSession: (sessionId: string) => {
      const nextRoute = setCompareRoute(route, sessionId);
      navigate(nextRoute);
      void sessionStore.getState().loadCompareSession(sessionId);
    },
    onFork: (input: Parameters<ReturnType<typeof sessionStore.getState>["forkSession"]>[0]) => {
      void (async () => {
        const childSessionId = await sessionStore.getState().forkSession(input);
        if (childSessionId !== null) {
          const nextRoute = openLineageTargetRoute(route, childSessionId);
          navigate(nextRoute);
          await sessionStore.getState().loadSession(childSessionId);
          void consoleStore.getState().loadAggregate();
        }
      })();
    },
    onForkLabelChange: (text: string) => sessionStore.getState().setForkLabel(text),
    onLoadMoreEvents: () => {
      void sessionStore.getState().loadMoreEvents();
    },
    onLoadMoreMetrics: () => {
      void sessionStore.getState().loadMoreMetrics();
    },
    onLoadMoreTranscript: () => {
      void sessionStore.getState().loadMoreTranscript();
    },
    onOpenSession: (sessionId: string) => {
      const nextRoute = openLineageTargetRoute(route, sessionId);
      navigate(nextRoute);
      sessionStore.getState().clearCompareSession();
      void sessionStore.getState().loadSession(sessionId);
    },
    onPromptChange: (text: string) => sessionStore.getState().setComposerText(text),
    onRequestCancellation: () => {
      void (async () => {
        await sessionStore.getState().requestCancellation();
        await refreshSelectedSession();
      })();
    },
    onResolveApproval: (
      input: Parameters<ReturnType<typeof sessionStore.getState>["resolveApproval"]>[0],
    ) => {
      void (async () => {
        await sessionStore.getState().resolveApproval(input);
        await refreshSelectedSession();
      })();
    },
    onRetryToolAttempt: (toolAttemptId: string) => {
      if (!confirmAction("Retry this tool attempt using retained arguments?")) {
        return;
      }
      void (async () => {
        await sessionStore.getState().retryToolAttempt({ toolAttemptId });
        await refreshSelectedSession();
      })();
    },
    onSelectTab: (tab: Parameters<typeof setInspectorTabRoute>[1]) =>
      navigate(setInspectorTabRoute(route, tab)),
    onSubmitAnswer: (questionId: string) => {
      void (async () => {
        await sessionStore.getState().submitAnswer({ questionId });
        await refreshSelectedSession();
      })();
    },
    onSubmitPrompt: () => {
      void (async () => {
        await sessionStore.getState().submitPrompt();
        await refreshSelectedSession();
      })();
    },
  };
}

export function workspaceOverviewActions({
  consoleStore,
  navigate,
  route,
  sessionStore,
}: Pick<WorkspaceConsoleStores, "consoleStore" | "sessionStore"> & {
  navigate: Navigate;
  route: AppRouteState;
}) {
  return {
    onRefresh: () => void consoleStore.getState().loadAggregate(),
    onSelectQueue: (queue: ConsoleFilters["queue"]) => {
      const nextRoute = selectQueueRoute(parseAppRoute(window.location.href), queue as AppQueue);
      navigate(nextRoute);
      sessionStore.getState().resetForRoute(null);
      void consoleStore.getState().selectQueue(queue);
    },
    onSelectSession: (sessionId: string) => {
      const nextRoute = selectSessionRoute(route, sessionId);
      navigate(nextRoute);
      void sessionStore.getState().loadSession(sessionId);
    },
  };
}

export function confirmAction(message: string): boolean {
  if (typeof window === "undefined" || typeof window.confirm !== "function") {
    return true;
  }
  return window.confirm(message);
}
