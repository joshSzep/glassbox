import type {
  createBranchSearchStore,
  createConsoleStore,
  createKnowledgeStore,
  createSessionStore,
  createTaskStore,
} from "@/stores/dashboard-stores";

export type WorkspaceConsoleStores = {
  branchSearchStore: ReturnType<typeof createBranchSearchStore>;
  consoleStore: ReturnType<typeof createConsoleStore>;
  knowledgeStore: ReturnType<typeof createKnowledgeStore>;
  sessionStore: ReturnType<typeof createSessionStore>;
  taskStore: ReturnType<typeof createTaskStore>;
};
