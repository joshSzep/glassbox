import type {
  createBranchSearchStore,
  createChangesetStore,
  createConsoleStore,
  createHandoffStore,
  createKnowledgeStore,
  createSessionStore,
  createTaskStore,
} from "@/stores/dashboard-stores";

export type WorkspaceConsoleStores = {
  branchSearchStore: ReturnType<typeof createBranchSearchStore>;
  changesetStore: ReturnType<typeof createChangesetStore>;
  consoleStore: ReturnType<typeof createConsoleStore>;
  handoffStore: ReturnType<typeof createHandoffStore>;
  knowledgeStore: ReturnType<typeof createKnowledgeStore>;
  sessionStore: ReturnType<typeof createSessionStore>;
  taskStore: ReturnType<typeof createTaskStore>;
};
