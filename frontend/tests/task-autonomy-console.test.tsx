import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  filterTaskSummaries,
  TaskAutonomyConsole,
} from "@/components/console/task-autonomy-console";
import type { components } from "@/generated/api-types";
import type { TaskDetailState, TaskQueuePageState } from "@/stores/dashboard-stores";

type TaskSummary = components["schemas"]["TaskSummaryResponse"];
type TaskDetail = components["schemas"]["TaskDetailResponse"];
type TaskEvent = components["schemas"]["TaskEventResponse"];

describe("task autonomy console", () => {
  it("filters task queues by status, blockers, and historical state", () => {
    const tasks = [
      makeTask("active-task", { status: "active" }),
      makeTask("blocked-task", { blocked_reason: "budget_exhausted", status: "paused" }),
      makeTask("failed-task", { status: "failed" }),
      makeTask("completed-task", { status: "completed" }),
      makeTask("background-task", { next_action_summary: "background continuation queued" }),
    ];

    expect(filterTaskSummaries(tasks, "active").map((task) => task.task_id)).toEqual([
      "active-task",
      "blocked-task",
      "background-task",
    ]);
    expect(filterTaskSummaries(tasks, "blocked").map((task) => task.task_id)).toEqual([
      "blocked-task",
    ]);
    expect(filterTaskSummaries(tasks, "failed").map((task) => task.task_id)).toEqual([
      "failed-task",
    ]);
    expect(filterTaskSummaries(tasks, "historical").map((task) => task.task_id)).toEqual([
      "completed-task",
    ]);
    expect(filterTaskSummaries(tasks, "background").map((task) => task.task_id)).toEqual([
      "background-task",
    ]);
  });

  it("renders queue filters, selected task detail, budget evidence, and event history", () => {
    const task = makeTask("task-1", {
      blocked_reason: "verification_failed",
      current_step_id: "step-2",
      status: "paused",
    });
    const markup = renderTaskConsole({
      detail: {
        ...idleDetail,
        detail: makeTaskDetail(task),
        eventPage: { cursor: 0, has_more: true, limit: 1, next_cursor: 3, returned_count: 1 },
        events: [
          makeEvent("event-1", "TaskStepStarted", { summary: "Started edit step" }, 2),
          makeEvent(
            "event-2",
            "BudgetDecisionRecorded",
            { decision: "allowed", detail: "one step remains" },
            3,
          ),
          makeEvent(
            "event-3",
            "BackgroundJobCreated",
            { job_id: "job-1234567890", summary: "Continuation queued" },
            4,
          ),
        ],
        eventState: "loaded",
        loadState: "loaded",
        selectedTaskId: "task-1",
      },
      queue: {
        ...idleQueue,
        items: [task],
        loadState: "loaded",
        queue: "blocked",
      },
    });

    expect(markup).toContain("Task Queue");
    expect(markup).toContain("Task Filters");
    expect(markup).toContain("Blocked");
    expect(markup).toContain("Selected Task");
    expect(markup).toContain("Write tests");
    expect(markup).toContain("1 passed, 1 failed, 2 total.");
    expect(markup).toContain("allowed: one step remains");
    expect(markup).toContain("#3 BudgetDecisionRecorded");
    expect(markup).toContain("Load More Events");
    expect(markup).toContain("Task controls");
    expect(markup).toContain("Continue");
    expect(markup).toContain("Adjust Budget");
    expect(markup).toContain("Cancel Job job-1234");
  });

  it("renders loading and empty states", () => {
    expect(
      renderTaskConsole({
        detail: idleDetail,
        queue: { ...idleQueue, loadState: "loading", queue: "active" },
      }),
    ).toContain("Loading task queue");

    expect(
      renderTaskConsole({
        detail: idleDetail,
        queue: { ...idleQueue, loadState: "loaded", queue: "failed" },
      }),
    ).toContain("No failed tasks");

    expect(
      renderTaskConsole({
        detail: { ...idleDetail, selectedTaskId: "task-1", loadState: "loading" },
        queue: { ...idleQueue, items: [makeTask("task-1")], loadState: "loaded" },
      }),
    ).toContain("Loading task inspector");
  });
});

const page = { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 };
const projectionHealth = {
  canonical_last_sequence: 0,
  degraded: false,
  detail: null,
  estimated_rebuild_event_count: 0,
  lag: 0,
  projected_last_sequence: null,
  projected_progress_ratio: 1,
  state: "ok",
} as const;

const idleQueue: TaskQueuePageState = {
  error: null,
  items: [],
  loadState: "idle",
  page,
  projectionHealth: null,
  queue: "active",
};

const idleDetail: TaskDetailState = {
  detail: null,
  error: null,
  eventPage: null,
  events: [],
  eventState: "idle",
  loadState: "idle",
  selectedTaskId: null,
};

function renderTaskConsole({
  detail,
  queue,
}: {
  detail: TaskDetailState;
  queue: TaskQueuePageState;
}): string {
  return renderToStaticMarkup(
    React.createElement(TaskAutonomyConsole, {
      detail,
      queue,
    }),
  );
}

function makeTask(taskId: string, overrides: Partial<TaskSummary> = {}): TaskSummary {
  return {
    blocked_detail: null,
    blocked_reason: null,
    current_step_id: null,
    goal: "Make dashboard autonomy visible",
    next_action_summary: "continue from current step",
    session_id: "session-1",
    status: "active",
    step_count: 2,
    task_id: taskId,
    title: `Task ${taskId}`,
    updated_at: "2026-04-23T00:00:00Z",
    ...overrides,
  };
}

function makeTaskDetail(task: TaskSummary): TaskDetail {
  return {
    projection_health: projectionHealth,
    steps: [
      {
        blocked_reason: null,
        description: "Map current dashboard state",
        order: 0,
        status: "completed",
        step_id: "step-1",
        title: "Map state",
      },
      {
        blocked_reason: "verification_failed",
        description: "Add inspector evidence",
        order: 1,
        status: "failed",
        step_id: "step-2",
        title: "Write tests",
      },
    ],
    task,
    verifications: [
      {
        check_name: "frontend tests",
        status: "passed",
        step_id: "step-1",
        summary: "unit pass",
        verification_id: "verification-1",
      },
      {
        check_name: "typecheck",
        status: "failed",
        step_id: "step-2",
        summary: "type gap",
        verification_id: "verification-2",
      },
    ],
  };
}

function makeEvent(
  eventId: string,
  eventType: string,
  payload: Record<string, unknown>,
  sequence: number,
): TaskEvent {
  return {
    created_at: "2026-04-23T00:00:00Z",
    event_id: eventId,
    event_type: eventType,
    payload,
    sequence,
    session_id: "session-1",
    task_id: "task-1",
    turn_id: null,
  };
}
