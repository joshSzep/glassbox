import type { AutonomyBudget, AutonomyMode } from "@/api/client";
import type { TaskQueueFilter } from "@/routing/app-route";
import type { TaskDetailState, TaskQueuePageState } from "@/stores/dashboard-stores";

import type { TaskDetail, TaskEvent } from "./types";

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

export function taskFilterCounts(
  tasks: TaskQueuePageState["items"],
): Record<TaskQueueFilter, number> {
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

export function taskQueueSummary(queue: TaskQueuePageState, visibleCount: number): string {
  if (queue.loadState === "loading") {
    return "Refreshing task-plan projection state.";
  }
  if (queue.error !== null) {
    return queue.error;
  }
  return `${visibleCount} visible ${queue.queue} task${visibleCount === 1 ? "" : "s"} from ${queue.items.length} loaded task-plan summaries.`;
}

export function verificationSummary(
  verifications: NonNullable<TaskDetailState["detail"]>["verifications"],
  drift?: NonNullable<TaskDetailState["detail"]>["verification_drift"],
) {
  if (drift?.posture === "stale") {
    return `Verification stale: ${drift.reason}.`;
  }
  if (drift?.posture === "missing_coverage") {
    return `Verification coverage missing: ${drift.reason}.`;
  }
  if (drift?.posture === "docs_only_drift" || drift?.posture === "generated_drift") {
    return `${drift.reason}.`;
  }
  if (verifications.length === 0) {
    return "No verification checks retained.";
  }
  const failed = verifications.filter((verification) => verification.status === "failed").length;
  const passed = verifications.filter((verification) => verification.status === "passed").length;
  return `${passed} passed, ${failed} failed, ${verifications.length} total.`;
}

export function defaultVerificationDrift(
  taskId: string,
): NonNullable<TaskDetailState["detail"]>["verification_drift"] {
  return {
    changed_path_digest: null,
    changed_paths: [],
    diff_summary_command: null,
    docs_only_changed_paths: [],
    error: null,
    generated_changed_paths: [],
    material_changed_paths: [],
    posture: "not_assessed",
    reason: "workspace drift was not assessed for this read",
    stale_changed_paths: [],
    stale_verification_ids: [],
    task_id: taskId,
    workspace_clean: true,
  };
}

export function defaultRepairHistory(
  taskId: string,
): NonNullable<NonNullable<TaskDetailState["detail"]>["repair_history"]> {
  return {
    accepted_risk_count: 0,
    attempts: [],
    failure_count: 0,
    latest_failure_sequence: null,
    latest_failure_summary: null,
    repaired_count: 0,
    repeated_failure_count: 0,
    retry_count: 0,
    status: "no_verification",
    task_id: taskId,
  };
}

export function lastKnownGoodSummary(
  lastKnownGood: NonNullable<TaskDetailState["detail"]>["last_known_good"] | null | undefined,
): string {
  if (lastKnownGood == null) {
    return "No passed verification marker retained.";
  }
  const checkpoint =
    lastKnownGood.checkpoint_id === null
      ? "no checkpoint linked"
      : `checkpoint ${lastKnownGood.checkpoint_id} at sequence ${lastKnownGood.checkpoint_sequence}`;
  return `${lastKnownGood.check_name} at sequence ${lastKnownGood.sequence} (${lastKnownGood.evidence_status}); ${checkpoint}.`;
}

export function repairHistorySummary(
  repairHistory:
    | NonNullable<NonNullable<TaskDetailState["detail"]>["repair_history"]>
    | null
    | undefined,
): string {
  const history: NonNullable<NonNullable<TaskDetailState["detail"]>["repair_history"]> =
    repairHistory ?? defaultRepairHistory("unknown");
  return `${history.status}: ${history.failure_count} failure${history.failure_count === 1 ? "" : "s"}, ${history.retry_count} retry${history.retry_count === 1 ? "" : "ies"}, ${history.repaired_count} repaired.`;
}

export function taskEventAnchor(sequence: number): string {
  return `task-event-${sequence}`;
}

export function latestEvent(
  events: TaskDetailState["events"],
  eventTypes: string[],
): TaskEvent | null {
  return latestMatchingEvent(events, (event) => eventTypes.includes(event.event_type));
}

export function latestMatchingEvent(
  events: TaskDetailState["events"],
  predicate: (event: TaskEvent) => boolean,
): TaskEvent | null {
  return [...events].reverse().find(predicate) ?? null;
}

export function payloadIncludes(event: TaskEvent, needle: string): boolean {
  return Object.values(event.payload).some((value) => String(value).toLowerCase().includes(needle));
}

export function artifactReference(event: TaskEvent): string {
  for (const key of ["artifact_path", "failure_artifact_path", "artifact_id"]) {
    const value = event.payload[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return `${key}: ${value}`;
    }
  }
  return eventSummary(event.payload);
}

export function latestAutonomyDecisionEvent(events: TaskDetailState["events"]) {
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

export function latestBudgetEvidence(events: TaskDetailState["events"]): string {
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

export function backgroundJobIds(events: TaskDetailState["events"]): string[] {
  const ids = new Set<string>();
  for (const event of events) {
    const jobId = event.payload.job_id;
    if (typeof jobId === "string" && jobId.length > 0) {
      ids.add(jobId);
    }
  }
  return [...ids];
}

export function budgetFromMode(mode: AutonomyMode, maxSteps: number): AutonomyBudget {
  const normalizedSteps = Number.isFinite(maxSteps) ? Math.max(0, Math.floor(maxSteps)) : 0;
  const canWrite = mode === "edit-safe" || mode === "test-driven";
  return {
    allowed_risk_buckets: canWrite ? ["read_only", "workspace_write"] : ["read_only"],
    checkpoint_approval_required: false,
    checkpoint_interval_seconds: Math.max(60, normalizedSteps * 60),
    max_artifact_bytes: 1_000_000,
    max_branch_attempts: 0,
    max_command_operations: 0,
    max_retry_delay_seconds: 60,
    max_steps: normalizedSteps,
    max_tool_calls: Math.max(1, normalizedSteps * 3),
    max_unattended_seconds: Math.max(60, normalizedSteps * 90),
    max_verification_attempts: mode === "test-driven" ? 2 : 1,
    max_wall_clock_seconds: Math.max(60, normalizedSteps * 120),
    max_write_operations: canWrite ? Math.max(1, normalizedSteps) : 0,
    quiet_window_policy: "allow",
  };
}

export function shortId(value: string): string {
  return value.length <= 8 ? value : value.slice(0, 8);
}

export function eventSummary(payload: Record<string, unknown>): string {
  for (const key of ["summary", "reason", "detail", "blocked_reason", "status"]) {
    const value = payload[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }
  return "Structured event payload retained.";
}

export function formatDate(value: string): string {
  return value
    .replace("T", " ")
    .replace(/\.\d+Z$/, "Z")
    .replace(/Z$/, " UTC");
}

export type { TaskDetail };
