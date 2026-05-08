import type { components, paths } from "@/generated/api-types";

import type {
  ActionAcceptedResponse,
  ApprovalDecision,
  RequestJson,
  RequestOptions,
} from "./client-core";

export type TaskListPageResponse = components["schemas"]["TaskListPageResponse"];
export type TaskDetailResponse = components["schemas"]["TaskDetailResponse"];
export type TaskStepPageResponse = components["schemas"]["TaskStepPageResponse"];
export type TaskEventPageResponse = components["schemas"]["TaskEventPageResponse"];
export type BackgroundJobDetailResponse = components["schemas"]["BackgroundJobDetailResponse"];
export type TaskContinuationWindowActionResponse =
  components["schemas"]["TaskContinuationWindowActionResponse"];
export type TaskPauseWindowResponse = components["schemas"]["TaskPauseWindowResponse"];
export type AutonomyBudget = components["schemas"]["AutonomyBudget"];
export type AutonomyMode = components["schemas"]["AutonomyMode"];

export type TaskListPageQuery = NonNullable<paths["/tasks"]["get"]["parameters"]["query"]>;
export type TaskStepPageQuery = NonNullable<
  paths["/tasks/{task_id}/steps"]["get"]["parameters"]["query"]
>;
export type TaskEventPageQuery = NonNullable<
  paths["/tasks/{task_id}/events"]["get"]["parameters"]["query"]
>;

export function createTaskEndpoints(requestJson: RequestJson) {
  return {
    getTaskPage: (query: TaskListPageQuery = {}, requestOptions?: RequestOptions) =>
      requestJson<TaskListPageResponse>("GET", "/tasks", { ...requestOptions, query }),

    getTaskDetail: (taskId: string, requestOptions?: RequestOptions) =>
      requestJson<TaskDetailResponse>(
        "GET",
        `/tasks/${encodeURIComponent(taskId)}`,
        requestOptions,
      ),

    getTaskStepPage: (
      taskId: string,
      query: TaskStepPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskStepPageResponse>("GET", `/tasks/${encodeURIComponent(taskId)}/steps`, {
        ...requestOptions,
        query,
      }),

    getTaskEventPage: (
      taskId: string,
      query: TaskEventPageQuery = {},
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskEventPageResponse>("GET", `/tasks/${encodeURIComponent(taskId)}/events`, {
        ...requestOptions,
        query,
      }),

    approveTaskPlan: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/approve-plan`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    continueTask: (
      input: {
        checkpointId?: string | null;
        continueForMinutes?: number | null;
        reason?: string | null;
        requestedBy?: string;
        taskId: string;
        verifyRepair?: boolean;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BackgroundJobDetailResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/continue`,
        {
          ...requestOptions,
          body: {
            checkpoint_id: input.checkpointId ?? null,
            continue_for_minutes: input.continueForMinutes ?? null,
            reason: input.reason ?? null,
            requested_by: input.requestedBy ?? "operator",
            verify_repair: input.verifyRepair ?? true,
          },
        },
      ),

    resolveTaskContinuationWindow: (
      input: {
        checkpointId?: string | null;
        decidedBy?: string;
        decision?: ApprovalDecision;
        reason?: string | null;
        requestedBy?: string;
        requestedMinutes: number;
        taskId: string;
        verifyRepair?: boolean;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskContinuationWindowActionResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/continuation-window`,
        {
          ...requestOptions,
          body: {
            checkpoint_id: input.checkpointId ?? null,
            decided_by: input.decidedBy ?? "operator",
            decision: input.decision ?? "approved",
            reason: input.reason ?? null,
            requested_by: input.requestedBy ?? "operator",
            requested_minutes: input.requestedMinutes,
            verify_repair: input.verifyRepair ?? true,
          },
        },
      ),

    scheduleTaskPauseWindow: (
      input: {
        checkpointId?: string | null;
        pauseBefore?: string | null;
        policy: components["schemas"]["PauseWindowPolicy"];
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskPauseWindowResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause-window`,
        {
          ...requestOptions,
          body: {
            actor: "operator",
            checkpoint_id: input.checkpointId ?? null,
            pause_before: input.pauseBefore ?? null,
            policy: input.policy,
            reason: input.reason ?? null,
          },
        },
      ),

    cancelTaskPauseWindow: (
      input: {
        pauseWindowId: string;
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<TaskPauseWindowResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause-window/${encodeURIComponent(
          input.pauseWindowId,
        )}/cancel`,
        {
          ...requestOptions,
          body: {
            actor: "operator",
            reason: input.reason ?? "operator override",
          },
        },
      ),

    pauseTask: (
      input: {
        actor?: string;
        detail?: string | null;
        reason?: components["schemas"]["TaskBlockedReason"];
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/pause`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            detail: input.detail ?? null,
            reason: input.reason ?? "manual_pause",
          },
        },
      ),

    resumeTask: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/resume`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    cancelTask: (
      input: { actor?: string; reason?: string | null; taskId: string },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/cancel`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),

    adjustTaskBudget: (
      input: {
        actor?: string;
        budget: AutonomyBudget;
        detail?: string | null;
        mode: AutonomyMode;
        reason?: string | null;
        taskId: string;
      },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<ActionAcceptedResponse>(
        "POST",
        `/tasks/${encodeURIComponent(input.taskId)}/budget`,
        {
          ...requestOptions,
          body: {
            actor: input.actor ?? "operator",
            budget: input.budget,
            detail: input.detail ?? null,
            mode: input.mode,
            reason: input.reason ?? null,
          },
        },
      ),

    cancelBackgroundJob: (
      input: { actor?: string; jobId: string; reason?: string | null },
      requestOptions?: RequestOptions,
    ) =>
      requestJson<BackgroundJobDetailResponse>(
        "POST",
        `/jobs/${encodeURIComponent(input.jobId)}/cancel`,
        {
          ...requestOptions,
          body: { actor: input.actor ?? "operator", reason: input.reason ?? null },
        },
      ),
  };
}
