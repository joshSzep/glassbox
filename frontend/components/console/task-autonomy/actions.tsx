"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, ListChecks, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { AutonomyBudget, AutonomyMode } from "@/api/client";
import type { TaskActionStatus } from "@/stores/dashboard-stores";

import { budgetFromMode, shortId } from "./format";

export function TaskActionControls({
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

function confirmAction(message: string): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm(message);
}
