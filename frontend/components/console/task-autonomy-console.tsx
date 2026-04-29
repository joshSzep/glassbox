"use client";

import { RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { AutonomyBudget, AutonomyMode } from "@/api/client";
import type { TaskQueueFilter } from "@/routing/app-route";
import {
  filterTaskSummaries,
  TaskFilterNavigation,
  taskFilterCounts,
  TaskPlanInspector,
  taskQueueSummary,
  TaskQueueTable,
} from "@/components/console/task-autonomy-sections";
import type {
  TaskActionStatus,
  TaskDetailState,
  TaskQueuePageState,
} from "@/stores/dashboard-stores";

export { filterTaskSummaries } from "@/components/console/task-autonomy-sections";

export type TaskAutonomyConsoleProps = {
  action?: TaskActionStatus;
  detail: TaskDetailState;
  onAdjustBudget?: (input: {
    budget: AutonomyBudget;
    detail?: string | null;
    mode: AutonomyMode;
  }) => void;
  onApprovePlan?: () => void;
  onCancelBackgroundJob?: (jobId: string) => void;
  onCancelTask?: () => void;
  onContinueTask?: () => void;
  onLoadMoreEvents?: () => void;
  onPauseTask?: () => void;
  onRefresh?: () => void;
  onResumeTask?: () => void;
  onSelectQueue?: (queue: TaskQueueFilter) => void;
  onSelectSession?: (sessionId: string) => void;
  onSelectTask?: (taskId: string) => void;
  queue: TaskQueuePageState;
};

export function TaskAutonomyConsole({
  action = { error: null, kind: null, state: "idle" },
  detail,
  onAdjustBudget,
  onApprovePlan,
  onCancelBackgroundJob,
  onCancelTask,
  onContinueTask,
  onLoadMoreEvents,
  onPauseTask,
  onRefresh,
  onResumeTask,
  onSelectQueue,
  onSelectSession,
  onSelectTask,
  queue,
}: TaskAutonomyConsoleProps) {
  const visibleTasks = filterTaskSummaries(queue.items, queue.queue);
  const selectedTaskId = detail.selectedTaskId;
  const selectedDetail = detail.detail;

  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <section
          aria-label="Autonomy console status"
          className="grid gap-3 rounded-md border border-border/80 bg-card p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Autonomy Console
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-normal">Task Queue</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {taskQueueSummary(queue, visibleTasks.length)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={queue.projectionHealth?.degraded ? "warning" : "success"}>
              {queue.projectionHealth?.state ?? "workspace"}
            </Badge>
            <Button onClick={onRefresh} size="sm" type="button" variant="outline">
              <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </section>

        <section aria-label="Task console frame" className="grid gap-4 xl:grid-cols-[18rem_1fr]">
          <aside className="flex flex-col gap-4">
            <TaskFilterNavigation
              counts={taskFilterCounts(queue.items)}
              onSelectQueue={onSelectQueue}
              selectedQueue={queue.queue}
            />
          </aside>

          <section className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(30rem,0.85fr)]">
            <TaskQueueTable
              error={queue.error}
              loadState={queue.loadState}
              onSelectTask={onSelectTask}
              queue={queue.queue}
              selectedTaskId={selectedTaskId}
              tasks={visibleTasks}
            />
            <TaskPlanInspector
              action={action}
              detail={detail}
              onAdjustBudget={onAdjustBudget}
              onApprovePlan={onApprovePlan}
              onCancelBackgroundJob={onCancelBackgroundJob}
              onCancelTask={onCancelTask}
              onContinueTask={onContinueTask}
              onLoadMoreEvents={onLoadMoreEvents}
              onPauseTask={onPauseTask}
              onResumeTask={onResumeTask}
              onSelectSession={onSelectSession}
              selectedDetail={selectedDetail}
            />
          </section>
        </section>
      </div>
    </main>
  );
}
