import type { ReactNode } from "react";
import { Activity, AlertCircle, GitBranch, MessageSquareText, RadioTower } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { formatMessage } from "@/components/console/session-inspector/format";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState, TranscriptMessage } from "@/state/session-state";

type OverviewAction = {
  detail: string;
  label: string;
  title: string;
  variant: BadgeProps["variant"];
};

export function SessionOverviewTab({
  actionPane,
  data,
  stream,
}: {
  actionPane: ReactNode;
  data: DashboardState;
  stream: SessionStreamState;
}) {
  const nextAction = deriveNextAction(data, stream);
  const healthItems = deriveHealthItems(data, stream);
  const summaries = deriveDecisionSummaries(data, stream);
  const transcriptPreview = deriveTranscriptPreview(data);

  return (
    <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
      <section className="rounded-lg border bg-background p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              Next action
            </p>
            <h3 className="mt-1 text-base font-semibold tracking-normal">{nextAction.title}</h3>
          </div>
          <Badge className="justify-start" variant={nextAction.variant}>
            {nextAction.label}
          </Badge>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">{nextAction.detail}</p>
      </section>

      <section className="rounded-lg border bg-background p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          <RadioTower className="h-4 w-4" aria-hidden="true" />
          Session readout
        </h3>
        <div className="grid gap-2 sm:grid-cols-2">
          <ReadoutItem label="Status" value={data.status} />
          <ReadoutItem label="Live state" value={formatStreamStatus(stream)} />
          <ReadoutItem label="Projection" value={formatProjection(data)} />
          <ReadoutItem label="Runtime owner" value={formatRuntimeOwner(data)} />
          <ReadoutItem label="Model" value={data.modelName ?? "model unknown"} />
          <ReadoutItem label="Lineage" value={formatLineage(data)} />
        </div>
      </section>

      <section className="rounded-lg border bg-background p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          <MessageSquareText className="h-4 w-4" aria-hidden="true" />
          Recent narrative
        </h3>
        <DataList density="compact">
          {transcriptPreview.map((message) => (
            <DataListItem key={message.message_id}>
              <DataListLabel>{message.role}</DataListLabel>
              <DataListMeta>{formatMessage(message)}</DataListMeta>
            </DataListItem>
          ))}
          {transcriptPreview.length === 0 ? (
            <DataListItem>
              <DataListMeta>No recent transcript messages are available.</DataListMeta>
            </DataListItem>
          ) : null}
        </DataList>
      </section>

      <section className="rounded-lg border bg-background p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          <Activity className="h-4 w-4" aria-hidden="true" />
          Decision context
        </h3>
        {summaries.length > 0 ? (
          <DataList density="compact">
            {summaries.map((summary) => (
              <DataListItem key={summary.label}>
                <DataListLabel>{summary.label}</DataListLabel>
                <DataListMeta>{summary.value}</DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        ) : (
          <p className="text-sm text-muted-foreground">
            No compare, verification, runtime, or event evidence changes the next decision.
          </p>
        )}
      </section>

      {healthItems.length > 0 ? (
        <section className="rounded-lg border border-warning bg-background p-4 xl:col-span-2">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            Health attention
          </h3>
          <DataList density="compact">
            {healthItems.map((item) => (
              <DataListItem key={item.label}>
                <DataListLabel>{item.label}</DataListLabel>
                <DataListMeta>{item.value}</DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        </section>
      ) : null}

      <div className="xl:col-span-2">{actionPane}</div>
    </div>
  );
}

function ReadoutItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-medium">{value}</p>
    </div>
  );
}

function deriveNextAction(data: DashboardState, stream: SessionStreamState): OverviewAction {
  const approval = data.pendingApprovals[0];
  if (approval !== undefined) {
    return {
      detail: `${approval.subject}: ${approval.reason}`,
      label: "awaiting approval",
      title: "Review the pending approval before continuing.",
      variant: "warning",
    };
  }

  if (data.pendingQuestionId !== null) {
    return {
      detail: data.pendingQuestionText ?? "The session is waiting for an operator answer.",
      label: "awaiting answer",
      title: "Answer the pending ask_user question.",
      variant: "info",
    };
  }

  if (data.sessionFailureMessage !== null) {
    return {
      detail: data.sessionFailureMessage,
      label: data.sessionFailureRetryable ? "retryable failure" : "failed session",
      title: "Inspect the failure before taking another action.",
      variant: "destructive",
    };
  }

  const activeTool = data.activeToolCalls[0];
  if (activeTool !== undefined) {
    return {
      detail: activeTool.summary ?? activeTool.status,
      label: "active tool call",
      title: `${activeTool.tool_name} is still running.`,
      variant: "info",
    };
  }

  if (data.currentTurn !== null && data.status === "running") {
    return {
      detail: `Current turn ${data.currentTurn.turn_id} is ${data.currentTurn.status}.`,
      label: "live turn",
      title: "Watch the live turn or send the next prompt when ready.",
      variant: "success",
    };
  }

  if (isPromptable(data, stream)) {
    return {
      detail: "The session is live and has no blocking approval, question, failure, or tool call.",
      label: "ready for prompt",
      title: "Continue the session with the next prompt.",
      variant: "success",
    };
  }

  if (data.canFork) {
    return {
      detail: data.latestForkPointTurnId ?? "A persisted fork point is available.",
      label: "forkable snapshot",
      title: "Create a branch from the latest safe point.",
      variant: "outline",
    };
  }

  return {
    detail: data.forkBlockedReason ?? "Use the transcript, lineage, and evidence tabs for review.",
    label: "historical snapshot",
    title: "Inspect this session as a completed snapshot.",
    variant: "muted",
  };
}

function deriveHealthItems(data: DashboardState, stream: SessionStreamState) {
  const items: { label: string; value: string }[] = [];

  if (data.projectionHealth?.degraded) {
    items.push({
      label: "projection degraded",
      value: `${data.projectionHealth.detail ?? data.projectionHealth.state} · lag ${data.projectionHealth.lag}`,
    });
  }

  if (stream.status === "reconnecting" || stream.status === "live_unavailable") {
    items.push({
      label:
        stream.status === "reconnecting" ? "live stream reconnecting" : "live stream unavailable",
      value: stream.error ?? "Showing the last persisted snapshot while stream health recovers.",
    });
  }

  if (data.runtimeContext === null) {
    items.push({ label: "runtime context missing", value: "Repository context is unavailable." });
  }

  return items;
}

function deriveDecisionSummaries(data: DashboardState, stream: SessionStreamState) {
  const summaries: { label: string; value: string }[] = [];
  const workingSetCount = data.runtimeContext?.working_set?.items?.length ?? 0;
  const eventCount = data.eventLog.length;

  if (data.compareSession !== null) {
    summaries.push({
      label: "Compare",
      value: `${data.compareSession.sessionId} · ${data.compareSession.status}`,
    });
  }

  if (data.projectionHealth?.degraded) {
    summaries.push({
      label: "Verification",
      value: "projection degraded; verify evidence before resolving actions",
    });
  }

  if (workingSetCount > 0 && hasImmediateOperatorDecision(data)) {
    summaries.push({
      label: "Runtime",
      value: `${workingSetCount} working-set item${workingSetCount === 1 ? "" : "s"} may affect the next action`,
    });
  }

  if (stream.status !== "live" || data.liveOutput.length > 0 || eventCount > 0) {
    summaries.push({
      label: "Evidence",
      value: `${stream.status} · ${eventCount} captured event${eventCount === 1 ? "" : "s"}`,
    });
  }

  return summaries;
}

function deriveTranscriptPreview(data: DashboardState): TranscriptMessage[] {
  if (data.pendingQuestionId !== null) {
    return data.transcript.slice(-2);
  }
  if (data.sessionFailureMessage !== null) {
    return data.transcript.slice(-3);
  }
  return data.transcript.slice(-3);
}

function hasImmediateOperatorDecision(data: DashboardState): boolean {
  return (
    data.pendingApprovals.length > 0 ||
    data.pendingQuestionId !== null ||
    data.sessionFailureMessage !== null
  );
}

function isPromptable(data: DashboardState, stream: SessionStreamState): boolean {
  return data.status === "running" && stream.status !== "historical_snapshot";
}

function formatProjection(data: DashboardState): string {
  if (data.projectionHealth === null) {
    return "projection unavailable";
  }
  if (data.projectionHealth.degraded) {
    return "projection degraded";
  }
  return `projection ${data.projectionHealth.state}`;
}

function formatRuntimeOwner(data: DashboardState): string {
  return data.runtimeContext?.repository_context.workspace_name ?? "workspace unknown";
}

function formatLineage(data: DashboardState): string {
  if (data.parentSessionId !== null) {
    return `parent ${data.parentSessionId}`;
  }
  if (data.childSessions.length > 0) {
    return `${data.childSessions.length} child session${data.childSessions.length === 1 ? "" : "s"}`;
  }
  return "root session";
}

function formatStreamStatus(stream: SessionStreamState): string {
  if (stream.status === "reconnecting") {
    return "live stream reconnecting";
  }
  if (stream.status === "live_unavailable") {
    return "live stream unavailable";
  }
  return stream.status.replaceAll("_", " ");
}
