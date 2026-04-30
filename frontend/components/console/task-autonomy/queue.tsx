import { CheckCircle2, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
import type { TaskQueuePageState } from "@/stores/dashboard-stores";

import { formatDate } from "./format";
import { TaskState, TaskStatusBadge } from "./shared";

const taskFilters: Array<{ label: string; queue: TaskQueueFilter }> = [
  { label: "All", queue: "all" },
  { label: "Active", queue: "active" },
  { label: "Blocked", queue: "blocked" },
  { label: "Failed", queue: "failed" },
  { label: "Completed", queue: "completed" },
  { label: "Background", queue: "background" },
  { label: "Historical", queue: "historical" },
];

export function TaskFilterNavigation({
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

export function TaskQueueTable({
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
