import { Clock3, ListChecks, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { AutonomyBudget, AutonomyMode } from "@/api/client";
import type { TaskActionStatus, TaskDetailState } from "@/stores/dashboard-stores";

import { TaskActionControls } from "./actions";
import {
  backgroundJobIds,
  defaultRepairHistory,
  defaultVerificationDrift,
  eventSummary,
  lastKnownGoodSummary,
  latestBudgetEvidence,
  repairHistorySummary,
  taskEventAnchor,
  verificationSummary,
} from "./format";
import { TaskEvidenceDrillDown, TaskWhyThisActionEvidence } from "./evidence";
import { TaskState, TaskStatusBadge } from "./shared";

export function TaskPlanInspector({
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
  const verificationDrift =
    selectedDetail.verification_drift ?? defaultVerificationDrift(selectedDetail.task.task_id);
  const repairHistory =
    selectedDetail.repair_history ?? defaultRepairHistory(selectedDetail.task.task_id);
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
            <DataListMeta>
              {verificationSummary(selectedDetail.verifications, verificationDrift)}
            </DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Last known good</DataListLabel>
            <DataListMeta>{lastKnownGoodSummary(selectedDetail.last_known_good)}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Repair history</DataListLabel>
            <DataListMeta>{repairHistorySummary(repairHistory)}</DataListMeta>
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
          verificationText={verificationSummary(selectedDetail.verifications, verificationDrift)}
        />
        <TaskEvidenceDrillDown
          events={detail.events}
          steps={selectedDetail.steps}
          task={selectedDetail.task}
          lastKnownGood={selectedDetail.last_known_good}
          repairHistory={repairHistory}
          verificationDrift={verificationDrift}
          verifications={selectedDetail.verifications}
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
                <DataListItem id={taskEventAnchor(event.sequence)} key={event.event_id}>
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
