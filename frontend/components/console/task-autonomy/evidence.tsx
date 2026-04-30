import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { TaskDetailState } from "@/stores/dashboard-stores";

import {
  artifactReference,
  defaultRepairHistory,
  eventSummary,
  lastKnownGoodSummary,
  latestAutonomyDecisionEvent,
  latestEvent,
  latestMatchingEvent,
  payloadIncludes,
  repairHistorySummary,
  taskEventAnchor,
  verificationSummary,
} from "./format";
import type { TaskDetail, TaskEvidenceRow } from "./types";

export function TaskWhyThisActionEvidence({
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

export function TaskEvidenceDrillDown({
  events,
  lastKnownGood,
  repairHistory,
  steps,
  task,
  verificationDrift,
  verifications,
}: {
  events: TaskDetailState["events"];
  lastKnownGood: TaskDetail["last_known_good"];
  repairHistory: TaskDetail["repair_history"];
  steps: TaskDetail["steps"];
  task: TaskDetail["task"];
  verificationDrift: TaskDetail["verification_drift"];
  verifications: TaskDetail["verifications"];
}) {
  const rows = taskEvidenceRows({
    events,
    lastKnownGood,
    repairHistory,
    steps,
    task,
    verificationDrift,
    verifications,
  });
  return (
    <section
      aria-label="Task evidence drill-down"
      className="rounded-md border border-border/80 bg-surface p-3"
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Task Evidence
        </h3>
        <Badge variant="info">{rows.filter((row) => row.event !== null).length} event links</Badge>
      </div>
      <DataList density="compact">
        {rows.map((row) => (
          <DataListItem key={row.label}>
            <DataListLabel>{row.label}</DataListLabel>
            <DataListMeta>
              <Badge className="mr-2" variant={evidenceToneVariant(row.tone)}>
                {row.state}
              </Badge>
              {row.detail}
              {row.event !== null ? (
                <>
                  {" "}
                  <a
                    className="text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    href={`#${taskEventAnchor(row.event.sequence)}`}
                  >
                    Event #{row.event.sequence} {row.event.event_type}
                  </a>
                </>
              ) : null}
            </DataListMeta>
          </DataListItem>
        ))}
      </DataList>
    </section>
  );
}

export function taskEvidenceRows({
  events,
  lastKnownGood,
  repairHistory,
  steps,
  task,
  verificationDrift,
  verifications,
}: {
  events: TaskDetailState["events"];
  lastKnownGood: TaskDetail["last_known_good"];
  repairHistory: TaskDetail["repair_history"];
  steps: TaskDetail["steps"];
  task: TaskDetail["task"];
  verificationDrift: TaskDetail["verification_drift"];
  verifications: TaskDetail["verifications"];
}): TaskEvidenceRow[] {
  const safeLastKnownGood = lastKnownGood ?? null;
  const safeRepairHistory: NonNullable<TaskDetail["repair_history"]> =
    repairHistory ?? defaultRepairHistory(task.task_id);
  const failedVerification = verifications.find((verification) => verification.status === "failed");
  const currentStep = steps.find((step) => step.step_id === task.current_step_id);
  const failedStep =
    currentStep?.status === "failed" ? currentStep : steps.find((step) => step.status === "failed");
  const budgetEvent = latestEvent(events, ["BudgetExhausted", "BudgetDecisionRecorded"]);
  const approvalEvent = latestMatchingEvent(events, (event) =>
    event.event_type.includes("Approval"),
  );
  const questionEvent = latestMatchingEvent(
    events,
    (event) => event.event_type.includes("Question") || event.event_type.includes("UserInput"),
  );
  const verificationEvent =
    failedVerification === undefined
      ? latestMatchingEvent(events, (event) => event.event_type.startsWith("TaskVerification"))
      : latestMatchingEvent(
          events,
          (event) =>
            event.event_type.startsWith("TaskVerification") &&
            event.payload.verification_id === failedVerification.verification_id,
        );
  const cancellationEvent = latestMatchingEvent(
    events,
    (event) => event.event_type.includes("Cancel") || event.event_type.includes("Cancelled"),
  );
  const providerEvent = latestMatchingEvent(events, (event) => payloadIncludes(event, "provider"));
  const artifactEvent = latestMatchingEvent(
    events,
    (event) =>
      event.payload.artifact_id !== undefined ||
      event.payload.artifact_path !== undefined ||
      event.payload.failure_artifact_path !== undefined,
  );

  return [
    {
      detail:
        task.blocked_reason === null
          ? task.next_action_summary
          : `${task.blocked_reason}${task.blocked_detail ? `: ${task.blocked_detail}` : ""}`,
      event: latestEvent(events, ["TaskStatusChanged", "TaskPaused", "TaskResumed"]) ?? null,
      label: "Stop reason",
      state: task.blocked_reason === null ? task.status : "blocked",
      tone: task.blocked_reason === null ? "default" : "warning",
    },
    {
      detail:
        failedStep === undefined
          ? (currentStep?.title ?? "No failed or current plan step is retained.")
          : `${failedStep.title}${failedStep.blocked_reason ? `: ${failedStep.blocked_reason}` : ""}`,
      event: latestMatchingEvent(
        events,
        (event) =>
          event.payload.step_id === (failedStep?.step_id ?? currentStep?.step_id) ||
          event.event_type.startsWith("TaskStep"),
      ),
      label: "Plan step",
      state: failedStep === undefined ? "current" : "failed",
      tone: failedStep === undefined ? "default" : "warning",
    },
    {
      detail:
        verificationDrift.posture === "stale"
          ? `${verificationDrift.reason}; stale paths: ${verificationDrift.stale_changed_paths.join(", ")}`
          : failedVerification === undefined
            ? verificationSummary(verifications, verificationDrift)
            : `${failedVerification.check_name}: ${failedVerification.summary ?? "verification failed"}`,
      event: verificationEvent,
      label: verificationDrift.posture === "stale" ? "Stale verification" : "Verification failure",
      state:
        verificationDrift.posture === "stale"
          ? "stale"
          : failedVerification === undefined
            ? "not failing"
            : "failed",
      tone:
        verificationDrift.posture === "stale"
          ? "warning"
          : failedVerification === undefined
            ? "success"
            : "destructive",
    },
    {
      detail: lastKnownGoodSummary(safeLastKnownGood),
      event:
        safeLastKnownGood === null
          ? null
          : latestMatchingEvent(
              events,
              (event) =>
                event.event_type.startsWith("TaskVerification") &&
                event.payload.verification_id === safeLastKnownGood.verification_id,
            ),
      label: "Last known good",
      state: safeLastKnownGood?.evidence_status ?? "missing",
      tone:
        safeLastKnownGood === null
          ? "default"
          : safeLastKnownGood.evidence_status === "stale"
            ? "warning"
            : safeLastKnownGood.evidence_status === "fresh"
              ? "success"
              : "info",
    },
    {
      detail: repairHistorySummary(safeRepairHistory),
      event: latestMatchingEvent(events, (event) =>
        ["TaskVerificationFailed", "TaskVerificationRetried"].includes(event.event_type),
      ),
      label: "Repair history",
      state: safeRepairHistory.status,
      tone:
        safeRepairHistory.status === "failed" || safeRepairHistory.status === "regressed"
          ? "destructive"
          : safeRepairHistory.status === "accepted_with_risk" ||
              safeRepairHistory.status === "repairing"
            ? "warning"
            : safeRepairHistory.status === "repaired" || safeRepairHistory.status === "clean"
              ? "success"
              : "default",
    },
    {
      detail:
        budgetEvent === null
          ? "No budget exhaustion or decision event is loaded."
          : eventSummary(budgetEvent.payload),
      event: budgetEvent,
      label: "Budget exhaustion",
      state: budgetEvent?.event_type === "BudgetExhausted" ? "exhausted" : "not exhausted",
      tone: budgetEvent?.event_type === "BudgetExhausted" ? "warning" : "default",
    },
    {
      detail:
        approvalEvent === null
          ? "No approval wait event is loaded for this task."
          : eventSummary(approvalEvent.payload),
      event: approvalEvent,
      label: "Approval wait",
      state: approvalEvent === null ? "none loaded" : "event backed",
      tone: approvalEvent === null ? "default" : "warning",
    },
    {
      detail:
        questionEvent === null
          ? "No user-input wait event is loaded for this task."
          : eventSummary(questionEvent.payload),
      event: questionEvent,
      label: "User-input wait",
      state: questionEvent === null ? "none loaded" : "event backed",
      tone: questionEvent === null ? "default" : "warning",
    },
    {
      detail:
        providerEvent === null
          ? "No provider-unavailability event is loaded for this task."
          : eventSummary(providerEvent.payload),
      event: providerEvent,
      label: "Provider availability",
      state: providerEvent === null ? "not indicated" : "provider cue",
      tone: providerEvent === null ? "default" : "warning",
    },
    {
      detail:
        task.status !== "cancelled" && cancellationEvent === null
          ? "No cancellation evidence is loaded for this task."
          : eventSummary(cancellationEvent?.payload ?? { status: task.status }),
      event: cancellationEvent,
      label: "Cancellation",
      state:
        task.status === "cancelled" || cancellationEvent !== null ? "cancelled" : "none loaded",
      tone: task.status === "cancelled" || cancellationEvent !== null ? "warning" : "default",
    },
    {
      detail:
        artifactEvent === null
          ? "No artifact or command-output reference is loaded for this task."
          : artifactReference(artifactEvent),
      event: artifactEvent,
      label: "Artifact or output",
      state: artifactEvent === null ? "none loaded" : "linked",
      tone: artifactEvent === null ? "default" : "info",
    },
  ];
}

function evidenceToneVariant(tone: TaskEvidenceRow["tone"]) {
  if (tone === "destructive") {
    return "destructive" as const;
  }
  if (tone === "success") {
    return "success" as const;
  }
  if (tone === "warning") {
    return "warning" as const;
  }
  if (tone === "info") {
    return "info" as const;
  }
  return "muted" as const;
}
