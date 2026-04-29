import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  AutonomyBudget,
  AutonomyMode,
  BranchSearchDetailResponse,
  BranchSearchListPageResponse,
  GlassboxApiClient,
  RepositoryIndexEntryDetailResponse,
  RepositoryIndexRebuildResponse,
  RepositoryIndexSearchPageResponse,
  RepositoryIndexStatusResponse,
  SessionAggregateQuery,
  WorkspaceMemoryDetailResponse,
  WorkspaceMemoryKind,
  WorkspaceMemoryListPageResponse,
  WorkspaceMemoryPrunePreviewResponse,
  WorkspaceMemoryState,
} from "@/api/client";
import type { TaskDetailResponse, TaskEventPageResponse, TaskListPageResponse } from "@/api/client";
import {
  createSessionEventStream,
  type SessionEventStreamOptions,
  type SessionStreamState,
  type SseEventEnvelope,
} from "@/api/sse";
import {
  applySessionEvent,
  clearCompareSession,
  createDashboardState,
  hydrateCompareSession,
  hydrateSelectedSession,
  hydrateSessionAggregate,
  type DashboardState,
} from "@/state/session-state";
import type { TaskQueueFilter } from "@/routing/app-route";

export type LoadState = "failed" | "idle" | "loaded" | "loading";
export type ActionKind = "answer" | "approval" | "cancel" | "fork" | "prompt";
export type TaskActionKind =
  | "approve-plan"
  | "budget"
  | "cancel-background-job"
  | "cancel-task"
  | "continue-task"
  | "pause-task"
  | "resume-task";
export type KnowledgeActionKind =
  | "confirm-memory"
  | "invalidate-memory"
  | "preview-prune-memory"
  | "prune-memory"
  | "rebuild-index";
export type BranchSearchActionKind =
  | "needs-review-candidate"
  | "reject-candidate"
  | "select-candidate";
export type DetailPageKind = "events" | "metrics" | "transcript";
export type MemoryFilter = "active" | "all" | "invalidated" | "stale";

export type DetailPageStatus = {
  error: string | null;
  hasMore: boolean;
  nextCursor: number | null;
  state: LoadState;
};

export type DetailPageState = Record<DetailPageKind, DetailPageStatus>;

export type ActionStatus = {
  error: string | null;
  kind: ActionKind | null;
  state: "failed" | "idle" | "pending" | "succeeded";
};

export type TaskActionStatus = {
  error: string | null;
  kind: TaskActionKind | null;
  state: "failed" | "idle" | "pending" | "succeeded";
};

export type KnowledgeActionStatus = {
  error: string | null;
  kind: KnowledgeActionKind | null;
  state: "failed" | "idle" | "pending" | "succeeded";
};

export type BranchSearchActionStatus = {
  error: string | null;
  kind: BranchSearchActionKind | null;
  state: "failed" | "idle" | "pending" | "succeeded";
};

export type DraftState = {
  answerTextByQuestionId: Record<string, string>;
  composerText: string;
  forkLabel: string;
  selectedCompareTargetId: string | null;
};

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

export type TaskQueuePageState = {
  error: string | null;
  items: TaskListPageResponse["items"];
  loadState: LoadState;
  page: TaskListPageResponse["page"] | null;
  projectionHealth: TaskListPageResponse["projection_health"];
  queue: TaskQueueFilter;
};

export type TaskDetailState = {
  detail: TaskDetailResponse | null;
  error: string | null;
  eventPage: TaskEventPageResponse["page"] | null;
  events: TaskEventPageResponse["items"];
  eventState: LoadState;
  loadState: LoadState;
  selectedTaskId: string | null;
};

export type TaskStoreState = {
  action: TaskActionStatus;
  adjustTaskBudget: (input: {
    budget: AutonomyBudget;
    detail?: string | null;
    mode: AutonomyMode;
    reason?: string | null;
    taskId?: string;
  }) => Promise<void>;
  applyTaskUpdate: (taskId?: string | null) => Promise<void>;
  approvePlan: (input?: { reason?: string | null; taskId?: string }) => Promise<void>;
  cancelBackgroundJob: (input: { jobId: string; reason?: string | null }) => Promise<void>;
  cancelTask: (input?: { reason?: string | null; taskId?: string }) => Promise<void>;
  continueTask: (input?: {
    reason?: string | null;
    taskId?: string;
    verifyRepair?: boolean;
  }) => Promise<void>;
  detail: TaskDetailState;
  loadMoreTaskEvents: () => Promise<void>;
  loadTaskPage: (query?: { queue?: TaskQueueFilter; sessionId?: string | null }) => Promise<void>;
  pauseTask: (input?: { detail?: string | null; taskId?: string }) => Promise<void>;
  queue: TaskQueuePageState;
  reset: () => void;
  resumeTask: (input?: { reason?: string | null; taskId?: string }) => Promise<void>;
  selectTask: (taskId: string) => Promise<void>;
  setQueueFilter: (queue: TaskQueueFilter) => Promise<void>;
};

export type MemoryInspectorState = {
  error: string | null;
  filter: MemoryFilter;
  items: WorkspaceMemoryListPageResponse["items"];
  loadState: LoadState;
  page: WorkspaceMemoryListPageResponse["page"] | null;
  preview: WorkspaceMemoryPrunePreviewResponse | null;
  query: string;
  selectedEntry: WorkspaceMemoryDetailResponse["entry"] | null;
  selectedMemoryId: string | null;
};

export type RepositoryInspectorState = {
  error: string | null;
  items: RepositoryIndexSearchPageResponse["items"];
  query: string;
  rebuild: RepositoryIndexRebuildResponse | null;
  searchState: LoadState;
  selectedEntry: RepositoryIndexEntryDetailResponse["entry"] | null;
  selectedEntryId: string | null;
  status: RepositoryIndexStatusResponse | null;
  statusState: LoadState;
};

export type KnowledgeStoreState = {
  action: KnowledgeActionStatus;
  confirmMemory: (input?: { memoryId?: string; reason?: string | null }) => Promise<void>;
  invalidateMemory: (input: { memoryId?: string; reason: string }) => Promise<void>;
  loadMemoryPage: (query?: {
    filter?: MemoryFilter;
    kind?: WorkspaceMemoryKind | null;
    query?: string;
  }) => Promise<void>;
  loadRepositoryStatus: () => Promise<void>;
  memory: MemoryInspectorState;
  previewPruneMemory: (input?: { memoryId?: string; reason?: string | null }) => Promise<void>;
  pruneMemory: (input: { memoryId?: string; reason: string }) => Promise<void>;
  rebuildRepositoryIndex: (input?: {
    background?: boolean;
    sessionId?: string | null;
  }) => Promise<void>;
  repository: RepositoryInspectorState;
  reset: () => void;
  searchRepositoryIndex: (query?: string) => Promise<void>;
  selectMemory: (memoryId: string) => Promise<void>;
  selectRepositoryEntry: (entryId: string) => Promise<void>;
  setMemoryFilter: (filter: MemoryFilter) => Promise<void>;
  setMemoryQuery: (query: string) => Promise<void>;
  setRepositoryQuery: (query: string) => Promise<void>;
};

export type BranchSearchPageState = {
  error: string | null;
  items: BranchSearchListPageResponse["items"];
  loadState: LoadState;
};

export type BranchSearchDetailState = {
  detail: BranchSearchDetailResponse | null;
  error: string | null;
  loadState: LoadState;
  selectedSearchId: string | null;
};

export type BranchSearchStoreState = {
  action: BranchSearchActionStatus;
  detail: BranchSearchDetailState;
  loadBranchSearchPage: (query?: { sessionId?: string | null }) => Promise<void>;
  markCandidate: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    reason: string;
    searchId?: string;
  }) => Promise<void>;
  page: BranchSearchPageState;
  reset: () => void;
  selectBranchSearch: (searchId: string) => Promise<void>;
};

export type SessionEventStreamHandle = ReturnType<typeof createSessionEventStream>;
export type SessionEventStreamFactory = (
  options: SessionEventStreamOptions,
) => SessionEventStreamHandle;

export type SessionStoreState = {
  action: ActionStatus;
  applyStreamEnvelope: (envelope: SseEventEnvelope) => void;
  clearCompareSession: () => void;
  connectStream: () => void;
  data: DashboardState;
  detailPages: DetailPageState;
  disconnectStream: () => void;
  drafts: DraftState;
  error: string | null;
  forkSession: (input?: {
    branchLabel?: string | null;
    turnId?: string | null;
  }) => Promise<string | null>;
  loadCompareSession: (sessionId: string) => Promise<void>;
  loadMoreEvents: () => Promise<void>;
  loadMoreMetrics: () => Promise<void>;
  loadMoreTranscript: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  loadState: LoadState;
  requestCancellation: () => Promise<void>;
  resetForRoute: (sessionId?: string | null) => void;
  resolveApproval: (input: {
    approvalId: string;
    decision: "approved" | "denied";
  }) => Promise<void>;
  setAnswerText: (questionId: string, text: string) => void;
  setComposerText: (text: string) => void;
  setForkLabel: (text: string) => void;
  setSelectedCompareTarget: (sessionId: string | null) => void;
  stream: SessionStreamState;
  submitAnswer: (input: { answer?: string; questionId: string }) => Promise<void>;
  submitPrompt: (text?: string) => Promise<void>;
};

export function createConsoleStore(apiClient: GlassboxApiClient): StoreApi<ConsoleStoreState> {
  let requestId = 0;

  return createStore<ConsoleStoreState>((set, get) => ({
    data: createDashboardState(),
    error: null,
    filters: createDefaultConsoleFilters(),
    loadAggregate: async (query = {}) => {
      const currentRequestId = ++requestId;
      const filters = { ...get().filters, ...query };
      set({ error: null, filters, loadState: "loading" });

      try {
        const aggregate = await apiClient.getSessionAggregate(toAggregateQuery(filters));
        if (currentRequestId !== requestId) {
          return;
        }
        set((state) => ({
          data: hydrateSessionAggregate(state.data, aggregate),
          error: null,
          loadState: "loaded",
        }));
      } catch (error) {
        if (currentRequestId !== requestId) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    reset: () => {
      requestId += 1;
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

export function createTaskStore(apiClient: GlassboxApiClient): StoreApi<TaskStoreState> {
  let listRequestId = 0;
  let detailRequestId = 0;

  return createStore<TaskStoreState>((set, get) => ({
    action: createIdleTaskActionStatus(),
    adjustTaskBudget: async (input) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () =>
          apiClient.adjustTaskBudget({
            budget: input.budget,
            detail: input.detail,
            mode: input.mode,
            reason: input.reason,
            taskId,
          }),
        get,
        kind: "budget",
        set,
        taskId,
      });
    },
    applyTaskUpdate: async (taskId = get().detail.selectedTaskId) => {
      await get().loadTaskPage({ queue: get().queue.queue });
      if (taskId !== null && taskId !== undefined) {
        await get().selectTask(taskId);
      }
    },
    approvePlan: async (input = {}) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () => apiClient.approveTaskPlan({ reason: input.reason, taskId }),
        get,
        kind: "approve-plan",
        set,
        taskId,
      });
    },
    cancelBackgroundJob: async (input) => {
      await runTaskAction({
        action: () => apiClient.cancelBackgroundJob({ jobId: input.jobId, reason: input.reason }),
        get,
        kind: "cancel-background-job",
        set,
        taskId: get().detail.selectedTaskId,
      });
    },
    cancelTask: async (input = {}) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () => apiClient.cancelTask({ reason: input.reason, taskId }),
        get,
        kind: "cancel-task",
        set,
        taskId,
      });
    },
    continueTask: async (input = {}) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () =>
          apiClient.continueTask({
            reason: input.reason,
            taskId,
            verifyRepair: input.verifyRepair,
          }),
        get,
        kind: "continue-task",
        set,
        taskId,
      });
    },
    detail: createIdleTaskDetailState(),
    loadMoreTaskEvents: async () => {
      const current = get().detail;
      if (
        current.selectedTaskId === null ||
        current.eventPage === null ||
        !current.eventPage.has_more ||
        current.eventPage.next_cursor === null ||
        current.eventState === "loading"
      ) {
        return;
      }

      set((state) => ({
        detail: { ...state.detail, error: null, eventState: "loading" },
      }));

      try {
        const page = await apiClient.getTaskEventPage(current.selectedTaskId, {
          cursor: current.eventPage.next_cursor,
          limit: TASK_EVENT_PAGE_SIZE,
        });
        set((state) => ({
          detail: {
            ...state.detail,
            eventPage: page.page,
            events: [...state.detail.events, ...page.items],
            eventState: "loaded",
          },
        }));
      } catch (error) {
        set((state) => ({
          detail: { ...state.detail, error: errorMessage(error), eventState: "failed" },
        }));
      }
    },
    loadTaskPage: async (query = {}) => {
      const currentRequestId = ++listRequestId;
      const queue = query.queue ?? get().queue.queue;
      set((state) => ({
        queue: { ...state.queue, error: null, loadState: "loading", queue },
      }));

      try {
        const page = await apiClient.getTaskPage({
          limit: TASK_QUEUE_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (currentRequestId !== listRequestId) {
          return;
        }
        set((state) => ({
          queue: {
            ...state.queue,
            error: null,
            items: page.items,
            loadState: "loaded",
            page: page.page,
            projectionHealth: page.projection_health,
            queue,
          },
        }));
      } catch (error) {
        if (currentRequestId !== listRequestId) {
          return;
        }
        set((state) => ({
          queue: { ...state.queue, error: errorMessage(error), loadState: "failed", queue },
        }));
      }
    },
    queue: createIdleTaskQueueState(),
    pauseTask: async (input = {}) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () => apiClient.pauseTask({ detail: input.detail, taskId }),
        get,
        kind: "pause-task",
        set,
        taskId,
      });
    },
    reset: () => {
      listRequestId += 1;
      detailRequestId += 1;
      set({
        action: createIdleTaskActionStatus(),
        detail: createIdleTaskDetailState(),
        queue: createIdleTaskQueueState(),
      });
    },
    resumeTask: async (input = {}) => {
      const taskId = input.taskId ?? requireSelectedTaskId(get().detail);
      await runTaskAction({
        action: () => apiClient.resumeTask({ reason: input.reason, taskId }),
        get,
        kind: "resume-task",
        set,
        taskId,
      });
    },
    selectTask: async (taskId) => {
      const currentRequestId = ++detailRequestId;
      set({
        detail: {
          ...createIdleTaskDetailState(),
          loadState: "loading",
          selectedTaskId: taskId,
        },
      });

      try {
        const [detail, eventPage] = await Promise.all([
          apiClient.getTaskDetail(taskId),
          apiClient.getTaskEventPage(taskId, { limit: TASK_EVENT_PAGE_SIZE }),
        ]);
        if (currentRequestId !== detailRequestId) {
          return;
        }
        set({
          detail: {
            detail,
            error: null,
            eventPage: eventPage.page,
            events: eventPage.items,
            eventState: "loaded",
            loadState: "loaded",
            selectedTaskId: taskId,
          },
        });
      } catch (error) {
        if (currentRequestId !== detailRequestId) {
          return;
        }
        set({
          detail: {
            ...createIdleTaskDetailState(),
            error: errorMessage(error),
            loadState: "failed",
            selectedTaskId: taskId,
          },
        });
      }
    },
    setQueueFilter: async (queue) => {
      await get().loadTaskPage({ queue });
    },
  }));
}

export function createBranchSearchStore(
  apiClient: GlassboxApiClient,
): StoreApi<BranchSearchStoreState> {
  let listRequestId = 0;
  let detailRequestId = 0;

  return createStore<BranchSearchStoreState>((set, get) => ({
    action: createIdleBranchSearchActionStatus(),
    detail: createIdleBranchSearchDetailState(),
    loadBranchSearchPage: async (query = {}) => {
      const currentRequestId = ++listRequestId;
      set((state) => ({
        page: { ...state.page, error: null, loadState: "loading" },
      }));
      try {
        const page = await apiClient.getBranchSearchPage({
          limit: BRANCH_SEARCH_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (currentRequestId !== listRequestId) {
          return;
        }
        set({ page: { error: null, items: page.items, loadState: "loaded" } });
      } catch (error) {
        if (currentRequestId !== listRequestId) {
          return;
        }
        set((state) => ({
          page: { ...state.page, error: errorMessage(error), loadState: "failed" },
        }));
      }
    },
    markCandidate: async (input) => {
      const searchId = input.searchId ?? requireSelectedBranchSearchId(get().detail);
      const kind = branchActionKind(input.action);
      set({ action: { error: null, kind, state: "pending" } });
      try {
        await apiClient.markBranchCandidate({
          action: input.action,
          candidateId: input.candidateId,
          reason: input.reason,
          searchId,
        });
        set({ action: { error: null, kind, state: "succeeded" } });
        await get().selectBranchSearch(searchId);
        await get().loadBranchSearchPage();
      } catch (error) {
        set({ action: { error: errorMessage(error), kind, state: "failed" } });
      }
    },
    page: createIdleBranchSearchPageState(),
    reset: () => {
      listRequestId += 1;
      detailRequestId += 1;
      set({
        action: createIdleBranchSearchActionStatus(),
        detail: createIdleBranchSearchDetailState(),
        page: createIdleBranchSearchPageState(),
      });
    },
    selectBranchSearch: async (searchId) => {
      const currentRequestId = ++detailRequestId;
      set({
        detail: {
          detail: null,
          error: null,
          loadState: "loading",
          selectedSearchId: searchId,
        },
      });
      try {
        const detail = await apiClient.getBranchSearchDetail(searchId);
        if (currentRequestId !== detailRequestId) {
          return;
        }
        set({
          detail: { detail, error: null, loadState: "loaded", selectedSearchId: searchId },
        });
      } catch (error) {
        if (currentRequestId !== detailRequestId) {
          return;
        }
        set({
          detail: {
            detail: null,
            error: errorMessage(error),
            loadState: "failed",
            selectedSearchId: searchId,
          },
        });
      }
    },
  }));
}

export function createKnowledgeStore(apiClient: GlassboxApiClient): StoreApi<KnowledgeStoreState> {
  let memoryRequestId = 0;
  let memoryDetailRequestId = 0;
  let repositoryRequestId = 0;

  return createStore<KnowledgeStoreState>((set, get) => ({
    action: createIdleKnowledgeActionStatus(),
    confirmMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.confirmWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "confirm-memory",
        memoryId,
        set,
      });
    },
    invalidateMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.invalidateWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "invalidate-memory",
        memoryId,
        set,
      });
    },
    loadMemoryPage: async (query = {}) => {
      const currentRequestId = ++memoryRequestId;
      const filter = query.filter ?? get().memory.filter;
      const textQuery = query.query ?? get().memory.query;
      set((state) => ({
        memory: {
          ...state.memory,
          error: null,
          filter,
          loadState: "loading",
          query: textQuery,
        },
      }));

      try {
        const page = await apiClient.listWorkspaceMemory({
          include_pruned: true,
          kind: query.kind ?? undefined,
          limit: MEMORY_PAGE_SIZE,
          query: textQuery.trim() || undefined,
          state: memoryStateForFilter(filter),
        });
        if (currentRequestId !== memoryRequestId) {
          return;
        }
        set((state) => ({
          memory: {
            ...state.memory,
            error: null,
            items: page.items,
            loadState: "loaded",
            page: page.page,
          },
        }));
      } catch (error) {
        if (currentRequestId !== memoryRequestId) {
          return;
        }
        set((state) => ({
          memory: { ...state.memory, error: errorMessage(error), loadState: "failed" },
        }));
      }
    },
    loadRepositoryStatus: async () => {
      const currentRequestId = ++repositoryRequestId;
      set((state) => ({
        repository: { ...state.repository, error: null, statusState: "loading" },
      }));
      try {
        const status = await apiClient.getRepositoryIndexStatus();
        if (currentRequestId !== repositoryRequestId) {
          return;
        }
        set((state) => ({
          repository: { ...state.repository, error: null, status, statusState: "loaded" },
        }));
      } catch (error) {
        if (currentRequestId !== repositoryRequestId) {
          return;
        }
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error), statusState: "failed" },
        }));
      }
    },
    memory: createIdleMemoryInspectorState(),
    previewPruneMemory: async (input = {}) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      set({ action: { error: null, kind: "preview-prune-memory", state: "pending" } });
      try {
        const preview = await apiClient.previewWorkspaceMemoryPrune({
          memoryId,
          reason: input.reason,
        });
        set((state) => ({
          action: { error: null, kind: "preview-prune-memory", state: "succeeded" },
          memory: { ...state.memory, preview },
        }));
      } catch (error) {
        set({
          action: { error: errorMessage(error), kind: "preview-prune-memory", state: "failed" },
        });
      }
    },
    pruneMemory: async (input) => {
      const memoryId = input.memoryId ?? requireSelectedMemoryId(get().memory);
      await runKnowledgeAction({
        action: () => apiClient.pruneWorkspaceMemory({ memoryId, reason: input.reason }),
        get,
        kind: "prune-memory",
        memoryId,
        set,
      });
    },
    rebuildRepositoryIndex: async (input = {}) => {
      set({ action: { error: null, kind: "rebuild-index", state: "pending" } });
      try {
        const rebuild = await apiClient.rebuildRepositoryIndex({
          background: input.background,
          sessionId: input.sessionId,
        });
        set((state) => ({
          action: { error: null, kind: "rebuild-index", state: "succeeded" },
          repository: { ...state.repository, rebuild },
        }));
        await get().loadRepositoryStatus();
        if (get().repository.query.trim()) {
          await get().searchRepositoryIndex();
        }
      } catch (error) {
        set({ action: { error: errorMessage(error), kind: "rebuild-index", state: "failed" } });
      }
    },
    repository: createIdleRepositoryInspectorState(),
    reset: () => {
      memoryRequestId += 1;
      memoryDetailRequestId += 1;
      repositoryRequestId += 1;
      set({
        action: createIdleKnowledgeActionStatus(),
        memory: createIdleMemoryInspectorState(),
        repository: createIdleRepositoryInspectorState(),
      });
    },
    searchRepositoryIndex: async (query = get().repository.query) => {
      set((state) => ({
        repository: {
          ...state.repository,
          error: null,
          query,
          searchState: "loading",
        },
      }));
      try {
        const page = await apiClient.searchRepositoryIndex({
          limit: REPOSITORY_INDEX_SEARCH_SIZE,
          query: query.trim() || "glassbox",
        });
        set((state) => ({
          repository: {
            ...state.repository,
            error: null,
            items: page.items,
            query,
            searchState: "loaded",
          },
        }));
      } catch (error) {
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error), searchState: "failed" },
        }));
      }
    },
    selectMemory: async (memoryId) => {
      const currentRequestId = ++memoryDetailRequestId;
      set((state) => ({
        memory: {
          ...state.memory,
          error: null,
          preview: null,
          selectedEntry: null,
          selectedMemoryId: memoryId,
        },
      }));
      try {
        const detail = await apiClient.getWorkspaceMemoryDetail(memoryId);
        if (currentRequestId !== memoryDetailRequestId) {
          return;
        }
        set((state) => ({
          memory: { ...state.memory, selectedEntry: detail.entry },
        }));
      } catch (error) {
        if (currentRequestId !== memoryDetailRequestId) {
          return;
        }
        set((state) => ({
          memory: { ...state.memory, error: errorMessage(error) },
        }));
      }
    },
    selectRepositoryEntry: async (entryId) => {
      set((state) => ({
        repository: {
          ...state.repository,
          error: null,
          selectedEntry: null,
          selectedEntryId: entryId,
        },
      }));
      try {
        const detail = await apiClient.getRepositoryIndexEntryDetail(entryId);
        set((state) => ({
          repository: { ...state.repository, selectedEntry: detail.entry },
        }));
      } catch (error) {
        set((state) => ({
          repository: { ...state.repository, error: errorMessage(error) },
        }));
      }
    },
    setMemoryFilter: async (filter) => {
      await get().loadMemoryPage({ filter });
    },
    setMemoryQuery: async (query) => {
      await get().loadMemoryPage({ query });
    },
    setRepositoryQuery: async (query) => {
      set((state) => ({ repository: { ...state.repository, query } }));
      await get().searchRepositoryIndex(query);
    },
  }));
}

export function createSessionStore({
  apiClient,
  createEventStream = createSessionEventStream,
}: {
  apiClient: GlassboxApiClient;
  createEventStream?: SessionEventStreamFactory;
}): StoreApi<SessionStoreState> {
  let sessionRequestId = 0;
  let compareRequestId = 0;
  let actionRequestId = 0;
  let streamHandle: SessionEventStreamHandle | null = null;

  const closeStream = () => {
    streamHandle?.close();
    streamHandle = null;
  };

  return createStore<SessionStoreState>((set, get) => ({
    action: createIdleActionStatus(),
    applyStreamEnvelope: (envelope) => {
      set((state) => ({
        data: applySessionEvent(state.data, envelope),
        stream: {
          ...state.stream,
          lastSequence: Math.max(state.stream.lastSequence, envelope.sequence),
        },
      }));
    },
    clearCompareSession: () => {
      compareRequestId += 1;
      set((state) => ({
        data: clearCompareSession(state.data),
        drafts: { ...state.drafts, selectedCompareTargetId: null },
      }));
    },
    connectStream: () => {
      const sessionId = get().data.sessionId;
      if (sessionId === null) {
        return;
      }
      closeStream();
      streamHandle = createEventStream({
        afterSequence: get().data.lastSequence,
        onEnvelope: (envelope) => get().applyStreamEnvelope(envelope),
        onStateChange: (stream) => set({ stream }),
        sessionId,
      });
      streamHandle.start();
    },
    data: createDashboardState(),
    detailPages: createIdleDetailPageState(),
    disconnectStream: () => {
      closeStream();
      set({ stream: createIdleStreamState() });
    },
    drafts: createEmptyDraftState(),
    error: null,
    forkSession: async (input = {}) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      set({ action: { error: null, kind: "fork", state: "pending" } });
      try {
        const fork = await apiClient.forkSession({
          branchLabel: (input.branchLabel ?? get().drafts.forkLabel) || null,
          sessionId,
          turnId: input.turnId ?? get().data.selectedForkTurnId,
        });
        if (currentActionRequestId === actionRequestId) {
          set((state) => ({
            action: { error: null, kind: "fork", state: "succeeded" },
            drafts: { ...state.drafts, forkLabel: "" },
          }));
        }
        return fork.child_session_id;
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "fork", state: "failed" } });
        }
        return null;
      }
    },
    loadCompareSession: async (sessionId) => {
      const currentRequestId = ++compareRequestId;
      set((state) => ({
        data: { ...state.data, compareSession: null, compareSessionId: sessionId },
        drafts: { ...state.drafts, selectedCompareTargetId: sessionId },
      }));

      try {
        const snapshot = await apiClient.getCompareSessionSnapshot(sessionId);
        if (currentRequestId !== compareRequestId) {
          return;
        }
        set((state) => ({ data: hydrateCompareSession(state.data, snapshot) }));
      } catch (error) {
        if (currentRequestId !== compareRequestId) {
          return;
        }
        set((state) => ({
          action: { error: errorMessage(error), kind: null, state: "failed" },
          data: clearCompareSession(state.data),
        }));
      }
    },
    loadMoreEvents: async () => {
      await loadDetailPage({ apiClient, get, kind: "events", set });
    },
    loadMoreMetrics: async () => {
      await loadDetailPage({ apiClient, get, kind: "metrics", set });
    },
    loadMoreTranscript: async () => {
      await loadDetailPage({ apiClient, get, kind: "transcript", set });
    },
    loadSession: async (sessionId) => {
      const currentRequestId = ++sessionRequestId;
      closeStream();
      set((state) => ({
        data: { ...state.data, selectedSessionId: sessionId },
        detailPages: createLoadingDetailPageState(),
        error: null,
        loadState: "loading",
        stream: createIdleStreamState(),
      }));

      try {
        const [snapshot, transcriptPage, eventPage, metricsPage] = await Promise.all([
          apiClient.getSessionSnapshot(sessionId),
          apiClient.getSessionTranscriptPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
          apiClient.getSessionEventLogPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
          apiClient.getSessionTurnMetricsPage(sessionId, { limit: DETAIL_PAGE_SIZE }),
        ]);
        if (currentRequestId !== sessionRequestId) {
          return;
        }
        set((state) => ({
          data: {
            ...hydrateSelectedSession(state.data, snapshot),
            eventLog: eventPage.items.map((event) => ({
              event_type: event.event_type,
              sequence: event.sequence,
            })),
            transcript: transcriptPage.items,
            turnMetrics: metricsPage.items,
          },
          detailPages: {
            events: pageStatusFromResponse(eventPage.page),
            metrics: pageStatusFromResponse(metricsPage.page),
            transcript: pageStatusFromResponse(transcriptPage.page),
          },
          error: null,
          loadState: "loaded",
          stream: { ...state.stream, lastSequence: snapshot.last_sequence },
        }));
      } catch (error) {
        if (currentRequestId !== sessionRequestId) {
          return;
        }
        set({ error: errorMessage(error), loadState: "failed" });
      }
    },
    loadState: "idle",
    requestCancellation: async () => {
      const data = get().data;
      const sessionId = requireSelectedSessionId(data);
      const currentActionRequestId = ++actionRequestId;
      set({ action: { error: null, kind: "cancel", state: "pending" } });
      try {
        await apiClient.cancelTurn({
          reason: "operator requested cancellation from dashboard",
          sessionId,
          turnId: data.currentTurn?.turn_id ?? null,
        });
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: null, kind: "cancel", state: "succeeded" } });
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "cancel", state: "failed" } });
        }
      }
    },
    resetForRoute: (sessionId = null) => {
      sessionRequestId += 1;
      compareRequestId += 1;
      actionRequestId += 1;
      closeStream();
      set((state) => ({
        action: createIdleActionStatus(),
        data: { ...createDashboardState(), selectedSessionId: sessionId },
        detailPages: createIdleDetailPageState(),
        drafts: state.drafts,
        error: null,
        loadState: sessionId === null ? "idle" : "loading",
        stream: createIdleStreamState(),
      }));
    },
    resolveApproval: async ({ approvalId, decision }) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      set({ action: { error: null, kind: "approval", state: "pending" } });
      try {
        await apiClient.resolveApproval({ approvalId, decision, sessionId });
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: null, kind: "approval", state: "succeeded" } });
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "approval", state: "failed" } });
        }
      }
    },
    setAnswerText: (questionId, text) => {
      set((state) => ({
        drafts: {
          ...state.drafts,
          answerTextByQuestionId: {
            ...state.drafts.answerTextByQuestionId,
            [questionId]: text,
          },
        },
      }));
    },
    setComposerText: (text) => {
      set((state) => ({ drafts: { ...state.drafts, composerText: text } }));
    },
    setForkLabel: (text) => {
      set((state) => ({ drafts: { ...state.drafts, forkLabel: text } }));
    },
    setSelectedCompareTarget: (sessionId) => {
      set((state) => ({ drafts: { ...state.drafts, selectedCompareTargetId: sessionId } }));
    },
    stream: createIdleStreamState(),
    submitAnswer: async ({ answer, questionId }) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      const answerText = answer ?? get().drafts.answerTextByQuestionId[questionId] ?? "";
      set({ action: { error: null, kind: "answer", state: "pending" } });
      try {
        await apiClient.submitAnswer({ answer: answerText, questionId, sessionId });
        if (currentActionRequestId === actionRequestId) {
          set((state) => {
            const remainingAnswers = { ...state.drafts.answerTextByQuestionId };
            delete remainingAnswers[questionId];
            return {
              action: { error: null, kind: "answer", state: "succeeded" },
              drafts: { ...state.drafts, answerTextByQuestionId: remainingAnswers },
            };
          });
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "answer", state: "failed" } });
        }
      }
    },
    submitPrompt: async (text) => {
      const sessionId = requireSelectedSessionId(get().data);
      const currentActionRequestId = ++actionRequestId;
      const prompt = text ?? get().drafts.composerText;
      set({ action: { error: null, kind: "prompt", state: "pending" } });
      try {
        await apiClient.submitMessage({ sessionId, text: prompt });
        if (currentActionRequestId === actionRequestId) {
          set((state) => ({
            action: { error: null, kind: "prompt", state: "succeeded" },
            drafts: { ...state.drafts, composerText: "" },
          }));
        }
      } catch (error) {
        if (currentActionRequestId === actionRequestId) {
          set({ action: { error: errorMessage(error), kind: "prompt", state: "failed" } });
        }
      }
    },
  }));
}

function createDefaultConsoleFilters(): ConsoleFilters {
  return { queue: "all", sort: "priority", status: null };
}

function createEmptyDraftState(): DraftState {
  return {
    answerTextByQuestionId: {},
    composerText: "",
    forkLabel: "",
    selectedCompareTargetId: null,
  };
}

function createIdleActionStatus(): ActionStatus {
  return { error: null, kind: null, state: "idle" };
}

const BRANCH_SEARCH_PAGE_SIZE = 100;
const DETAIL_PAGE_SIZE = 80;
const MEMORY_PAGE_SIZE = 200;
const REPOSITORY_INDEX_SEARCH_SIZE = 50;
const TASK_EVENT_PAGE_SIZE = 80;
const TASK_QUEUE_PAGE_SIZE = 200;

function createIdleTaskQueueState(): TaskQueuePageState {
  return {
    error: null,
    items: [],
    loadState: "idle",
    page: null,
    projectionHealth: null,
    queue: "active",
  };
}

function createIdleTaskDetailState(): TaskDetailState {
  return {
    detail: null,
    error: null,
    eventPage: null,
    events: [],
    eventState: "idle",
    loadState: "idle",
    selectedTaskId: null,
  };
}

function createIdleTaskActionStatus(): TaskActionStatus {
  return { error: null, kind: null, state: "idle" };
}

function createIdleBranchSearchActionStatus(): BranchSearchActionStatus {
  return { error: null, kind: null, state: "idle" };
}

function createIdleBranchSearchPageState(): BranchSearchPageState {
  return { error: null, items: [], loadState: "idle" };
}

function createIdleBranchSearchDetailState(): BranchSearchDetailState {
  return { detail: null, error: null, loadState: "idle", selectedSearchId: null };
}

function createIdleKnowledgeActionStatus(): KnowledgeActionStatus {
  return { error: null, kind: null, state: "idle" };
}

function createIdleMemoryInspectorState(): MemoryInspectorState {
  return {
    error: null,
    filter: "active",
    items: [],
    loadState: "idle",
    page: null,
    preview: null,
    query: "",
    selectedEntry: null,
    selectedMemoryId: null,
  };
}

function createIdleRepositoryInspectorState(): RepositoryInspectorState {
  return {
    error: null,
    items: [],
    query: "",
    rebuild: null,
    searchState: "idle",
    selectedEntry: null,
    selectedEntryId: null,
    status: null,
    statusState: "idle",
  };
}

async function runTaskAction({
  action,
  get,
  kind,
  set,
  taskId,
}: {
  action: () => Promise<unknown>;
  get: StoreApi<TaskStoreState>["getState"];
  kind: TaskActionKind;
  set: StoreApi<TaskStoreState>["setState"];
  taskId: string | null;
}) {
  set({ action: { error: null, kind, state: "pending" } });
  try {
    await action();
    set({ action: { error: null, kind, state: "succeeded" } });
    await get().applyTaskUpdate(taskId);
  } catch (error) {
    set({ action: { error: errorMessage(error), kind, state: "failed" } });
  }
}

async function runKnowledgeAction({
  action,
  get,
  kind,
  memoryId,
  set,
}: {
  action: () => Promise<unknown>;
  get: StoreApi<KnowledgeStoreState>["getState"];
  kind: KnowledgeActionKind;
  memoryId: string | null;
  set: StoreApi<KnowledgeStoreState>["setState"];
}) {
  set({ action: { error: null, kind, state: "pending" } });
  try {
    await action();
    set({ action: { error: null, kind, state: "succeeded" } });
    await get().loadMemoryPage();
    if (memoryId !== null) {
      await get().selectMemory(memoryId);
    }
  } catch (error) {
    set({ action: { error: errorMessage(error), kind, state: "failed" } });
  }
}

function requireSelectedTaskId(detail: TaskDetailState): string {
  if (detail.selectedTaskId === null) {
    throw new Error("No task is selected.");
  }
  return detail.selectedTaskId;
}

function requireSelectedBranchSearchId(detail: BranchSearchDetailState): string {
  if (detail.selectedSearchId === null) {
    throw new Error("No branch search is selected.");
  }
  return detail.selectedSearchId;
}

function branchActionKind(action: "needs-review" | "reject" | "select"): BranchSearchActionKind {
  if (action === "select") {
    return "select-candidate";
  }
  if (action === "reject") {
    return "reject-candidate";
  }
  return "needs-review-candidate";
}

function requireSelectedMemoryId(memory: MemoryInspectorState): string {
  if (memory.selectedMemoryId === null) {
    throw new Error("No workspace memory entry is selected.");
  }
  return memory.selectedMemoryId;
}

function memoryStateForFilter(filter: MemoryFilter): WorkspaceMemoryState | undefined {
  return filter === "all" ? undefined : filter;
}

function createIdleDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("idle"),
    metrics: createDetailPageStatus("idle"),
    transcript: createDetailPageStatus("idle"),
  };
}

function createLoadingDetailPageState(): DetailPageState {
  return {
    events: createDetailPageStatus("loading"),
    metrics: createDetailPageStatus("loading"),
    transcript: createDetailPageStatus("loading"),
  };
}

function createDetailPageStatus(state: LoadState): DetailPageStatus {
  return { error: null, hasMore: false, nextCursor: null, state };
}

function pageStatusFromResponse(page: {
  has_more: boolean;
  next_cursor: number | null;
}): DetailPageStatus {
  return {
    error: null,
    hasMore: page.has_more,
    nextCursor: page.next_cursor,
    state: "loaded",
  };
}

async function loadDetailPage({
  apiClient,
  get,
  kind,
  set,
}: {
  apiClient: GlassboxApiClient;
  get: StoreApi<SessionStoreState>["getState"];
  kind: DetailPageKind;
  set: StoreApi<SessionStoreState>["setState"];
}) {
  const state = get();
  const sessionId = requireSelectedSessionId(state.data);
  const currentPage = state.detailPages[kind];
  if (!currentPage.hasMore || currentPage.nextCursor === null || currentPage.state === "loading") {
    return;
  }

  set((nextState) => ({
    detailPages: {
      ...nextState.detailPages,
      [kind]: { ...nextState.detailPages[kind], error: null, state: "loading" },
    },
  }));

  try {
    if (kind === "transcript") {
      const page = await apiClient.getSessionTranscriptPage(sessionId, {
        cursor: currentPage.nextCursor,
        limit: DETAIL_PAGE_SIZE,
      });
      set((nextState) => ({
        data: { ...nextState.data, transcript: [...nextState.data.transcript, ...page.items] },
        detailPages: { ...nextState.detailPages, transcript: pageStatusFromResponse(page.page) },
      }));
      return;
    }
    if (kind === "events") {
      const page = await apiClient.getSessionEventLogPage(sessionId, {
        cursor: currentPage.nextCursor,
        limit: DETAIL_PAGE_SIZE,
      });
      set((nextState) => ({
        data: {
          ...nextState.data,
          eventLog: [
            ...nextState.data.eventLog,
            ...page.items.map((event) => ({
              event_type: event.event_type,
              sequence: event.sequence,
            })),
          ],
        },
        detailPages: { ...nextState.detailPages, events: pageStatusFromResponse(page.page) },
      }));
      return;
    }

    const page = await apiClient.getSessionTurnMetricsPage(sessionId, {
      cursor: currentPage.nextCursor,
      limit: DETAIL_PAGE_SIZE,
    });
    set((nextState) => ({
      data: { ...nextState.data, turnMetrics: [...nextState.data.turnMetrics, ...page.items] },
      detailPages: { ...nextState.detailPages, metrics: pageStatusFromResponse(page.page) },
    }));
  } catch (error) {
    set((nextState) => ({
      detailPages: {
        ...nextState.detailPages,
        [kind]: {
          ...nextState.detailPages[kind],
          error: errorMessage(error),
          state: "failed",
        },
      },
    }));
  }
}

function createIdleStreamState(): SessionStreamState {
  return { error: null, lastSequence: 0, retryCount: 0, status: "historical_snapshot" };
}

function toAggregateQuery(filters: ConsoleFilters): SessionAggregateQuery {
  return {
    queue: filters.queue === "all" ? null : filters.queue,
    sort: filters.sort,
    status: filters.status,
  };
}

function requireSelectedSessionId(data: DashboardState): string {
  if (data.sessionId === null) {
    throw new Error("No selected session is loaded.");
  }
  return data.sessionId;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected Glassbox dashboard error.";
}
