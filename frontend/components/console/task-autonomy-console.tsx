"use client";

import type { ReactNode } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileSearch,
  ListChecks,
  Loader2,
  RefreshCcw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import { buildAppRoute, type TaskQueueFilter } from "@/routing/app-route";
import type { TaskDetailState, TaskQueuePageState } from "@/stores/dashboard-stores";

export type TaskAutonomyConsoleProps = {
  detail: TaskDetailState;
  onLoadMoreEvents?: () => void;
  onRefresh?: () => void;
  onSelectQueue?: (queue: TaskQueueFilter) => void;
  onSelectSession?: (sessionId: string) => void;
  onSelectTask?: (taskId: string) => void;
  queue: TaskQueuePageState;
};

const taskFilters: Array<{ label: string; queue: TaskQueueFilter }> = [
  { label: "All", queue: "all" },
  { label: "Active", queue: "active" },
  { label: "Blocked", queue: "blocked" },
  { label: "Failed", queue: "failed" },
  { label: "Completed", queue: "completed" },
  { label: "Background", queue: "background" },
  { label: "Historical", queue: "historical" },
];

export function TaskAutonomyConsole({
  detail,
  onLoadMoreEvents,
  onRefresh,
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
              detail={detail}
              onLoadMoreEvents={onLoadMoreEvents}
              onSelectSession={onSelectSession}
              selectedDetail={selectedDetail}
            />
          </section>
        </section>
      </div>
    </main>
  );
}

function TaskFilterNavigation({
  counts,
  onSelectQueue,
  selectedQueue,
}: {
  counts: Record<TaskQueueFilter, number>;
  onSelectQueue?: (queue: TaskQueueFilter) => void;
  selectedQueue: TaskQueueFilter;
}) {
  return (
    <nav
      aria-label="Task queue filters"
      className="rounded-md border border-border/80 bg-card p-3 text-card-foreground shadow-sm"
    >
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Task Filters
        </h2>
        <Badge variant="muted">{counts.all}</Badge>
      </div>
      <div className="grid gap-1">
        {taskFilters.map((filter) => {
          const selected = selectedQueue === filter.queue;
          return (
            <a
              aria-current={selected ? "page" : undefined}
              className={`grid min-h-density-row rounded-md px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                selected ? "bg-accent text-accent-foreground" : "hover:bg-surface-raised"
              }`}
              href={buildAppRoute({
                compareSessionId: null,
                queue: "all",
                selectedSessionId: null,
                selectedTaskId: null,
                surface: "tasks",
                tab: "overview",
                taskQueue: filter.queue,
              })}
              key={filter.queue}
              onClick={(event) => {
                if (onSelectQueue === undefined) {
                  return;
                }
                event.preventDefault();
                onSelectQueue(filter.queue);
              }}
            >
              <span className="flex items-center justify-between gap-3 text-sm font-medium">
                {filter.label}
                <Badge variant={counts[filter.queue] > 0 ? "info" : "muted"}>
                  {counts[filter.queue]}
                </Badge>
              </span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}

function TaskQueueTable({
  error,
  loadState,
  onSelectTask,
  queue,
  selectedTaskId,
  tasks,
}: {
  error: string | null;
  loadState: string;
  onSelectTask?: (taskId: string) => void;
  queue: TaskQueueFilter;
  selectedTaskId: string | null;
  tasks: TaskQueuePageState["items"];
}) {
  if (error !== null) {
    return <TaskState title="Task queue unavailable" tone="destructive" value={error} />;
  }
  if (loadState === "loading" && tasks.length === 0) {
    return (
      <TaskState
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        title="Loading task queue"
        value="Fetching durable task-plan summaries."
      />
    );
  }
  if (tasks.length === 0) {
    return (
      <TaskState
        icon={<CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />}
        title={`No ${queue} tasks`}
        value="No autonomous work matches the current filter."
      />
    );
  }

  return (
    <section aria-label="Task queue rows" className="min-w-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Task</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Current</TableHead>
            <TableHead>Session</TableHead>
            <TableHead>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => (
            <TableRow
              data-state={selectedTaskId === task.task_id ? "selected" : undefined}
              key={task.task_id}
            >
              <TableCell className="min-w-64">
                <a
                  className="block rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  href={buildAppRoute({
                    compareSessionId: null,
                    queue: "all",
                    selectedSessionId: null,
                    selectedTaskId: task.task_id,
                    surface: "tasks",
                    tab: "overview",
                    taskQueue: queue,
                  })}
                  onClick={(event) => {
                    if (onSelectTask === undefined) {
                      return;
                    }
                    event.preventDefault();
                    onSelectTask(task.task_id);
                  }}
                >
                  <span className="block break-words font-medium">{task.title}</span>
                  <span className="mt-1 block break-words text-xs text-muted-foreground">
                    {task.goal}
                  </span>
                </a>
              </TableCell>
              <TableCell>
                <TaskStatusBadge status={task.status} blocked={task.blocked_reason !== null} />
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {task.blocked_reason ?? task.next_action_summary}
              </TableCell>
              <TableCell className="break-all font-mono text-xs">{task.session_id}</TableCell>
              <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                {formatDate(task.updated_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}

function TaskPlanInspector({
  detail,
  onLoadMoreEvents,
  onSelectSession,
  selectedDetail,
}: {
  detail: TaskDetailState;
  onLoadMoreEvents?: () => void;
  onSelectSession?: (sessionId: string) => void;
  selectedDetail: TaskDetailState["detail"];
}) {
  if (detail.selectedTaskId === null) {
    return (
      <TaskState
        icon={<ListChecks className={operatorIconSizeClass} aria-hidden="true" />}
        title="Select a task"
        value="Choose a task row to inspect plan steps, verification state, events, and related evidence."
      />
    );
  }
  if (detail.error !== null && selectedDetail === null) {
    return <TaskState title="Task inspector unavailable" tone="destructive" value={detail.error} />;
  }
  if (detail.loadState === "loading" || selectedDetail === null) {
    return (
      <TaskState
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        title="Loading task inspector"
        value="Fetching plan steps and task event history."
      />
    );
  }

  const currentStep = selectedDetail.steps.find(
    (step) => step.step_id === selectedDetail.task.current_step_id,
  );
  const budgetEvidence = latestBudgetEvidence(detail.events);

  return (
    <aside
      aria-label="Selected task inspector"
      className="min-w-0 rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            Selected Task
          </p>
          <h2 className="mt-1 break-words text-lg font-semibold tracking-normal">
            {selectedDetail.task.title}
          </h2>
          <p className="mt-1 break-words text-sm text-muted-foreground">
            {selectedDetail.task.goal}
          </p>
        </div>
        <TaskStatusBadge
          blocked={selectedDetail.task.blocked_reason !== null}
          status={selectedDetail.task.status}
        />
      </div>

      <div className="mt-4 grid gap-3">
        <DataList density="compact" aria-label="Task summary">
          <DataListItem>
            <DataListLabel>Current step</DataListLabel>
            <DataListMeta>{currentStep?.title ?? "No current step retained."}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Verification</DataListLabel>
            <DataListMeta>{verificationSummary(selectedDetail.verifications)}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Budget</DataListLabel>
            <DataListMeta>{budgetEvidence}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Branch attempts</DataListLabel>
            <DataListMeta>Branch-search comparison evidence arrives in GBX-884.</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Related session</DataListLabel>
            <DataListMeta>
              <button
                className="break-all text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => onSelectSession?.(selectedDetail.task.session_id)}
                type="button"
              >
                {selectedDetail.task.session_id}
              </button>
            </DataListMeta>
          </DataListItem>
        </DataList>

        <section aria-label="Task plan steps">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Plan
          </h3>
          <DataList density="compact">
            {selectedDetail.steps.length === 0 ? (
              <DataListItem>
                <DataListLabel>No steps retained</DataListLabel>
                <DataListMeta>The task projection has no plan steps.</DataListMeta>
              </DataListItem>
            ) : (
              selectedDetail.steps.map((step) => (
                <DataListItem key={step.step_id}>
                  <DataListLabel>
                    {step.order + 1}. {step.title}
                  </DataListLabel>
                  <DataListMeta>
                    {step.status}
                    {step.blocked_reason ? `; blocked by ${step.blocked_reason}` : ""}
                    {step.description ? `; ${step.description}` : ""}
                  </DataListMeta>
                </DataListItem>
              ))
            )}
          </DataList>
        </section>

        <section aria-label="Task event history">
          <div className="mb-2 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
              Event History
            </h3>
            <Badge variant={detail.eventState === "failed" ? "destructive" : "muted"}>
              {detail.events.length} loaded
            </Badge>
          </div>
          <DataList density="compact">
            {detail.events.length === 0 ? (
              <DataListItem>
                <DataListLabel>No task events loaded</DataListLabel>
                <DataListMeta>Refresh the task when live session events arrive.</DataListMeta>
              </DataListItem>
            ) : (
              detail.events.map((event) => (
                <DataListItem key={event.event_id}>
                  <DataListLabel>
                    #{event.sequence} {event.event_type}
                  </DataListLabel>
                  <DataListMeta>{eventSummary(event.payload)}</DataListMeta>
                </DataListItem>
              ))
            )}
          </DataList>
          {detail.eventPage?.has_more ? (
            <Button
              className="mt-3"
              onClick={onLoadMoreEvents}
              size="sm"
              type="button"
              variant="outline"
            >
              <Clock3 className={operatorIconSizeClass} aria-hidden="true" />
              Load More Events
            </Button>
          ) : null}
        </section>
      </div>
    </aside>
  );
}

function TaskState({
  icon,
  title,
  tone = "default",
  value,
}: {
  icon?: ReactNode;
  title: string;
  tone?: "default" | "destructive";
  value: string;
}) {
  return (
    <section
      aria-label={title}
      className={`rounded-md border p-4 shadow-sm ${
        tone === "destructive"
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : "border-border/80 bg-card text-card-foreground"
      }`}
    >
      <div className="flex items-start gap-3">
        {icon ?? <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold tracking-normal">{title}</h2>
          <p className="mt-1 break-words text-sm text-muted-foreground">{value}</p>
        </div>
      </div>
    </section>
  );
}

function TaskStatusBadge({ blocked, status }: { blocked: boolean; status: string }) {
  if (blocked) {
    return (
      <Badge variant="warning">
        <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
        Blocked
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge variant="destructive">
        <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
        Failed
      </Badge>
    );
  }
  if (status === "completed") {
    return (
      <Badge variant="success">
        <CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />
        Completed
      </Badge>
    );
  }
  if (status === "cancelled" || status === "abandoned") {
    return (
      <Badge variant="muted">
        <Clock3 className={operatorIconSizeClass} aria-hidden="true" />
        Historical
      </Badge>
    );
  }
  return (
    <Badge variant="info">
      <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
      {status}
    </Badge>
  );
}

export function filterTaskSummaries(
  tasks: TaskQueuePageState["items"],
  queue: TaskQueueFilter,
): TaskQueuePageState["items"] {
  if (queue === "all") {
    return tasks;
  }
  return tasks.filter((task) => matchesTaskFilter(task, queue));
}

function matchesTaskFilter(task: TaskQueuePageState["items"][number], queue: TaskQueueFilter) {
  if (queue === "active") {
    return ["active", "paused", "proposed"].includes(task.status);
  }
  if (queue === "blocked") {
    return task.blocked_reason !== null;
  }
  if (queue === "failed") {
    return task.status === "failed";
  }
  if (queue === "completed") {
    return task.status === "completed";
  }
  if (queue === "background") {
    return task.next_action_summary.toLowerCase().includes("background");
  }
  if (queue === "historical") {
    return ["abandoned", "cancelled", "completed"].includes(task.status);
  }
  return true;
}

function taskFilterCounts(tasks: TaskQueuePageState["items"]): Record<TaskQueueFilter, number> {
  return {
    active: filterTaskSummaries(tasks, "active").length,
    all: tasks.length,
    background: filterTaskSummaries(tasks, "background").length,
    blocked: filterTaskSummaries(tasks, "blocked").length,
    completed: filterTaskSummaries(tasks, "completed").length,
    failed: filterTaskSummaries(tasks, "failed").length,
    historical: filterTaskSummaries(tasks, "historical").length,
  };
}

function taskQueueSummary(queue: TaskQueuePageState, visibleCount: number): string {
  if (queue.loadState === "loading") {
    return "Refreshing task-plan projection state.";
  }
  if (queue.error !== null) {
    return queue.error;
  }
  return `${visibleCount} visible ${queue.queue} task${visibleCount === 1 ? "" : "s"} from ${queue.items.length} loaded task-plan summaries.`;
}

function verificationSummary(
  verifications: NonNullable<TaskDetailState["detail"]>["verifications"],
) {
  if (verifications.length === 0) {
    return "No verification checks retained.";
  }
  const failed = verifications.filter((verification) => verification.status === "failed").length;
  const passed = verifications.filter((verification) => verification.status === "passed").length;
  return `${passed} passed, ${failed} failed, ${verifications.length} total.`;
}

function latestBudgetEvidence(events: TaskDetailState["events"]): string {
  const budgetEvent = [...events]
    .reverse()
    .find(
      (event) =>
        event.event_type === "BudgetDecisionRecorded" || event.event_type === "BudgetExhausted",
    );
  if (budgetEvent === undefined) {
    return "No task budget decision retained in loaded events.";
  }
  const detail = budgetEvent.payload.detail;
  const decision = budgetEvent.payload.decision ?? budgetEvent.event_type;
  return `${String(decision)}${typeof detail === "string" ? `: ${detail}` : ""}`;
}

function eventSummary(payload: Record<string, unknown>): string {
  for (const key of ["summary", "reason", "detail", "blocked_reason", "status"]) {
    const value = payload[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }
  return "Structured event payload retained.";
}

function formatDate(value: string): string {
  return value
    .replace("T", " ")
    .replace(/\.\d+Z$/, "Z")
    .replace(/Z$/, " UTC");
}
