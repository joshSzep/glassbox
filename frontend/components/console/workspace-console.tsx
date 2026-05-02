"use client";

import { useEffect, useMemo } from "react";
import { useStore } from "zustand";

import { createGlassboxApiClient } from "@/api/client";
import { BranchSearchConsole } from "@/components/console/branch-search-console";
import { ChangesetConsole } from "@/components/console/changeset-console";
import { KnowledgeAutonomyConsole } from "@/components/console/knowledge-autonomy-console";
import { SessionInspector } from "@/components/console/session-inspector";
import { TaskAutonomyConsole } from "@/components/console/task-autonomy-console";
import { WorkspaceOverview } from "@/components/console/workspace-overview";
import {
  branchSearchConsoleActions,
  changesetConsoleActions,
  knowledgeConsoleActions,
  sessionInspectorActions,
  taskConsoleActions,
  workspaceOverviewActions,
} from "@/components/console/workspace-console/actions";
import { useWorkspaceConsoleRouting } from "@/components/console/workspace-console/routing";
import {
  createBranchSearchStore,
  createChangesetStore,
  createConsoleStore,
  createKnowledgeStore,
  createSessionStore,
  createTaskStore,
} from "@/stores/dashboard-stores";

export function WorkspaceConsole() {
  const apiClient = useMemo(() => createGlassboxApiClient(), []);
  const branchSearchStore = useMemo(() => createBranchSearchStore(apiClient), [apiClient]);
  const changesetStore = useMemo(() => createChangesetStore(apiClient), [apiClient]);
  const consoleStore = useMemo(() => createConsoleStore(apiClient), [apiClient]);
  const knowledgeStore = useMemo(() => createKnowledgeStore(apiClient), [apiClient]);
  const sessionStore = useMemo(() => createSessionStore({ apiClient }), [apiClient]);
  const taskStore = useMemo(() => createTaskStore(apiClient), [apiClient]);
  const branchSearchState = useStore(branchSearchStore);
  const changesetState = useStore(changesetStore);
  const consoleState = useStore(consoleStore);
  const knowledgeState = useStore(knowledgeStore);
  const sessionState = useStore(sessionStore);
  const taskState = useStore(taskStore);
  const { navigate, refreshSelectedSession, route } = useWorkspaceConsoleRouting({
    branchSearchStore,
    changesetStore,
    consoleStore,
    knowledgeStore,
    sessionStore,
    taskStore,
  });

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
        {...taskConsoleActions({ navigate, route, sessionStore, taskStore })}
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
        repository={knowledgeState.repository}
        surface={route.surface}
        {...knowledgeConsoleActions({ knowledgeStore, route })}
      />
    );
  }

  if (route.surface === "changesets") {
    return (
      <ChangesetConsole
        action={changesetState.action}
        detail={changesetState.detail}
        page={changesetState.page}
        {...changesetConsoleActions({ changesetStore, navigate, route })}
      />
    );
  }

  if (route.surface === "branches") {
    return (
      <BranchSearchConsole
        action={branchSearchState.action}
        detail={branchSearchState.detail}
        page={branchSearchState.page}
        {...branchSearchConsoleActions({ branchSearchStore })}
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
            queue={route.queue}
            stream={sessionState.stream}
            {...sessionInspectorActions({
              consoleStore,
              navigate,
              refreshSelectedSession,
              route,
              sessionStore,
            })}
          />
        )
      }
      loadState={consoleState.loadState}
      selectedQueue={consoleState.filters.queue}
      selectedSessionId={route.selectedSessionId}
      stream={sessionState.stream}
      {...workspaceOverviewActions({ consoleStore, navigate, route, sessionStore })}
    />
  );
}
