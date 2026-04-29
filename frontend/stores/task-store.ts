import { createStore, type StoreApi } from "zustand/vanilla";

import type {
  AutonomyBudget,
  AutonomyMode,
  GlassboxApiClient,
  TaskDetailResponse,
  TaskEventPageResponse,
  TaskListPageResponse,
} from "@/api/client";
import type { TaskQueueFilter } from "@/routing/app-route";
import {
  createIdleActionStatus,
  createRequestTracker,
  errorMessage,
  runAsyncStoreAction,
  type LoadState,
  type StoreActionStatus,
} from "@/stores/store-actions";

export type TaskActionKind =
  | "approve-plan"
  | "budget"
  | "cancel-background-job"
  | "cancel-task"
  | "continue-task"
  | "pause-task"
  | "resume-task";

export type TaskActionStatus = StoreActionStatus<TaskActionKind>;

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

const TASK_EVENT_PAGE_SIZE = 80;
const TASK_QUEUE_PAGE_SIZE = 200;

export function createTaskStore(apiClient: GlassboxApiClient): StoreApi<TaskStoreState> {
  const listRequests = createRequestTracker();
  const detailRequests = createRequestTracker();

  return createStore<TaskStoreState>((set, get) => ({
    action: createIdleActionStatus(),
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
      const currentRequestId = listRequests.next();
      const queue = query.queue ?? get().queue.queue;
      set((state) => ({
        queue: { ...state.queue, error: null, loadState: "loading", queue },
      }));

      try {
        const page = await apiClient.getTaskPage({
          limit: TASK_QUEUE_PAGE_SIZE,
          session_id: query.sessionId ?? undefined,
        });
        if (!listRequests.isCurrent(currentRequestId)) {
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
        if (!listRequests.isCurrent(currentRequestId)) {
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
      listRequests.invalidate();
      detailRequests.invalidate();
      set({
        action: createIdleActionStatus(),
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
      const currentRequestId = detailRequests.next();
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
        if (!detailRequests.isCurrent(currentRequestId)) {
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
        if (!detailRequests.isCurrent(currentRequestId)) {
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
  await runAsyncStoreAction({
    action,
    kind,
    onSuccess: async () => {
      await get().applyTaskUpdate(taskId);
    },
    setAction: (status) => set({ action: status }),
  });
}

function requireSelectedTaskId(detail: TaskDetailState): string {
  if (detail.selectedTaskId === null) {
    throw new Error("No task is selected.");
  }
  return detail.selectedTaskId;
}
