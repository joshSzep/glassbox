"use client";

import type { ReactNode } from "react";
import { useState } from "react";
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
import type { AutonomyBudget, AutonomyMode } from "@/api/client";
import type {
  TaskActionStatus,
  TaskDetailState,
  TaskQueuePageState,
} from "@/stores/dashboard-stores";

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
  action,
  detail,
  onAdjustBudget,
  onApprovePlan,
  onCancelBackgroundJob,
  onCancelTask,
  onContinueTask,
  onLoadMoreEvents,
  onPauseTask,
  onResumeTask,
  onSelectSession,
  selectedDetail,
}: {
  action: TaskActionStatus;
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
  onResumeTask?: () => void;
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
  const jobIds = backgroundJobIds(detail.events);

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
        <TaskActionControls
          action={action}
          jobIds={jobIds}
          onAdjustBudget={onAdjustBudget}
          onApprovePlan={onApprovePlan}
          onCancelBackgroundJob={onCancelBackgroundJob}
          onCancelTask={onCancelTask}
          onContinueTask={onContinueTask}
          onPauseTask={onPauseTask}
          onResumeTask={onResumeTask}
          status={selectedDetail.task.status}
        />

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

        <TaskWhyThisActionEvidence
          budgetEvidence={budgetEvidence}
          currentStepTitle={currentStep?.title ?? null}
          events={detail.events}
          verificationText={verificationSummary(selectedDetail.verifications)}
        />

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

function TaskActionControls({
  action,
  jobIds,
  onAdjustBudget,
  onApprovePlan,
  onCancelBackgroundJob,
  onCancelTask,
  onContinueTask,
  onPauseTask,
  onResumeTask,
  status,
}: {
  action: TaskActionStatus;
  jobIds: string[];
  onAdjustBudget?: (input: {
    budget: AutonomyBudget;
    detail?: string | null;
    mode: AutonomyMode;
  }) => void;
  onApprovePlan?: () => void;
  onCancelBackgroundJob?: (jobId: string) => void;
  onCancelTask?: () => void;
  onContinueTask?: () => void;
  onPauseTask?: () => void;
  onResumeTask?: () => void;
  status: string;
}) {
  const [mode, setMode] = useState<AutonomyMode>("inspect");
  const [maxSteps, setMaxSteps] = useState(2);
  const actionPending = action.state === "pending";
  const terminal = ["abandoned", "cancelled", "completed", "failed"].includes(status);
  const canApprove = status === "proposed" && onApprovePlan !== undefined;
  const canResume = status === "paused" && onResumeTask !== undefined;

  return (
    <section
      aria-label="Task controls"
      className="rounded-md border border-border/80 bg-surface p-3"
    >
      <div className="flex flex-wrap gap-2">
        {canApprove ? (
          <Button disabled={actionPending} onClick={onApprovePlan} size="sm" type="button">
            <CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />
            Approve Plan
          </Button>
        ) : null}
        <Button
          disabled={actionPending || terminal}
          onClick={() => {
            if (confirmAction("Start bounded background continuation for this task?")) {
              onContinueTask?.();
            }
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          <ListChecks className={operatorIconSizeClass} aria-hidden="true" />
          Continue
        </Button>
        <Button
          disabled={actionPending || terminal}
          onClick={() => onPauseTask?.()}
          size="sm"
          type="button"
          variant="outline"
        >
          <Clock3 className={operatorIconSizeClass} aria-hidden="true" />
          Pause
        </Button>
        <Button
          disabled={actionPending || !canResume}
          onClick={() => onResumeTask?.()}
          size="sm"
          type="button"
          variant="outline"
        >
          <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
          Resume
        </Button>
        <Button
          disabled={actionPending || terminal}
          onClick={() => {
            if (confirmAction("Cancel this task? This records an operator cancellation.")) {
              onCancelTask?.();
            }
          }}
          size="sm"
          type="button"
          variant="destructive"
        >
          <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
          Cancel
        </Button>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_7rem_auto]">
        <label className="grid gap-1 text-xs font-medium text-muted-foreground">
          Budget mode
          <select
            className="h-8 rounded-md border border-input bg-background px-2 text-sm text-foreground"
            onChange={(event) => setMode(event.target.value as AutonomyMode)}
            value={mode}
          >
            <option value="inspect">inspect</option>
            <option value="guided">guided</option>
            <option value="edit-safe">edit-safe</option>
            <option value="test-driven">test-driven</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs font-medium text-muted-foreground">
          Steps
          <input
            className="h-8 rounded-md border border-input bg-background px-2 text-sm text-foreground"
            min={0}
            onChange={(event) => setMaxSteps(Number(event.target.value))}
            type="number"
            value={maxSteps}
          />
        </label>
        <Button
          className="self-end"
          disabled={actionPending || terminal || onAdjustBudget === undefined}
          onClick={() => {
            if (
              confirmAction(
                "Adjust this task budget? Budget changes are recorded as backend evidence.",
              )
            ) {
              onAdjustBudget?.({
                budget: budgetFromMode(mode, maxSteps),
                detail: `dashboard set ${mode} budget with ${maxSteps} steps`,
                mode,
              });
            }
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          Adjust Budget
        </Button>
      </div>

      {jobIds.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {jobIds.map((jobId) => (
            <Button
              disabled={actionPending}
              key={jobId}
              onClick={() => {
                if (confirmAction(`Cancel background job ${jobId}?`)) {
                  onCancelBackgroundJob?.(jobId);
                }
              }}
              size="sm"
              type="button"
              variant="outline"
            >
              Cancel Job {shortId(jobId)}
            </Button>
          ))}
        </div>
      ) : null}

      {action.state === "failed" && action.error !== null ? (
        <p className="mt-3 text-sm text-destructive">{action.error}</p>
      ) : null}
      {action.state === "succeeded" ? (
        <p className="mt-3 text-sm text-muted-foreground">
          Action accepted; refreshed task evidence.
        </p>
      ) : null}
    </section>
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

function TaskWhyThisActionEvidence({
  budgetEvidence,
  currentStepTitle,
  events,
  verificationText,
}: {
  budgetEvidence: string;
  currentStepTitle: string | null;
  events: TaskDetailState["events"];
  verificationText: string;
}) {
  const decisionEvent = latestAutonomyDecisionEvent(events);
  const memoryEvents = events.filter((event) => event.event_type.includes("Memory")).length;
  const branchEvents = events.filter((event) => event.event_type.startsWith("Branch")).length;
  return (
    <section
      aria-label="Why this action"
      className="rounded-md border border-border/80 bg-surface p-3"
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Why this action
        </h3>
        <Badge variant={decisionEvent === null ? "warning" : "info"}>
          {decisionEvent === null ? "missing evidence" : "event backed"}
        </Badge>
      </div>
      <DataList density="compact">
        <DataListItem>
          <DataListLabel>Decision source</DataListLabel>
          <DataListMeta>
            {decisionEvent === null
              ? "No autonomous decision event is loaded for this task."
              : `${decisionEvent.event_type} at sequence ${decisionEvent.sequence}`}
          </DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Plan step</DataListLabel>
          <DataListMeta>{currentStepTitle ?? "No current plan step retained."}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Budget and policy</DataListLabel>
          <DataListMeta>{budgetEvidence}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Verification</DataListLabel>
          <DataListMeta>{verificationText}</DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>Context evidence</DataListLabel>
          <DataListMeta>
            {memoryEvents === 0 && branchEvents === 0
              ? "No memory/index or branch-search event is loaded for this task."
              : `${memoryEvents} memory event${memoryEvents === 1 ? "" : "s"}; ${branchEvents} branch event${branchEvents === 1 ? "" : "s"}.`}
          </DataListMeta>
        </DataListItem>
      </DataList>
    </section>
  );
}

function latestAutonomyDecisionEvent(events: TaskDetailState["events"]) {
  return (
    [...events]
      .reverse()
      .find((event) =>
        [
          "TaskStatusChanged",
          "TaskPaused",
          "TaskResumed",
          "TaskCancelled",
          "BudgetDecisionRecorded",
          "BudgetExhausted",
          "BackgroundJobCreated",
        ].includes(event.event_type),
      ) ?? null
  );
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

function backgroundJobIds(events: TaskDetailState["events"]): string[] {
  const ids = new Set<string>();
  for (const event of events) {
    const jobId = event.payload.job_id;
    if (typeof jobId === "string" && jobId.length > 0) {
      ids.add(jobId);
    }
  }
  return [...ids];
}

function budgetFromMode(mode: AutonomyMode, maxSteps: number): AutonomyBudget {
  const normalizedSteps = Number.isFinite(maxSteps) ? Math.max(0, Math.floor(maxSteps)) : 0;
  const canWrite = mode === "edit-safe" || mode === "test-driven";
  return {
    allowed_risk_buckets: canWrite ? ["read_only", "workspace_write"] : ["read_only"],
    max_artifact_bytes: 1_000_000,
    max_branch_attempts: 0,
    max_command_operations: 0,
    max_steps: normalizedSteps,
    max_tool_calls: Math.max(1, normalizedSteps * 3),
    max_verification_attempts: mode === "test-driven" ? 2 : 1,
    max_wall_clock_seconds: Math.max(60, normalizedSteps * 120),
    max_write_operations: canWrite ? Math.max(1, normalizedSteps) : 0,
  };
}

function confirmAction(message: string): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm(message);
}

function shortId(value: string): string {
  return value.length <= 8 ? value : value.slice(0, 8);
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
