import { History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import { formatDuration } from "@/components/console/session-inspector/format";
import { JumpLink, StatusBadge, narrativeTurnDomId } from "./shared";
import {
  buildSessionNarrative,
  type DashboardState,
  type SessionNarrativeTurn,
} from "@/state/session-state";

export function TimelinePane({
  data,
  onOpenForkTurn,
}: {
  data: DashboardState;
  onOpenForkTurn?: (turnId: string | null) => void;
}) {
  const narrative = buildSessionNarrative(data);
  const activeTurn =
    narrative.turns.find((turn) => turn.turnId === data.currentTurn?.turn_id) ??
    narrative.turns.find((turn) => ["active", "running"].includes(turn.status));
  const pendingTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "approval" || item.kind === "question"),
  );
  const failedTurn = narrative.turns.find((turn) => turn.status === "failed");
  const forkableTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "fork-boundary"),
  );
  const longRunItems = buildLongRunTimeline(data);

  return (
    <Pane icon={History} title="Timeline">
      <div className="space-y-4">
        <LongRunEvidenceTimeline items={longRunItems} />
        {narrative.turns.length === 0 ? (
          <EmptyLine value="No timeline events are available." />
        ) : (
          <>
            <div className="flex flex-wrap gap-2" aria-label="Timeline jumps">
              {activeTurn !== undefined ? <JumpLink label="Active turn" turn={activeTurn} /> : null}
              {pendingTurn !== undefined ? (
                <JumpLink label="Pending action" turn={pendingTurn} />
              ) : null}
              {failedTurn !== undefined ? <JumpLink label="Failed turn" turn={failedTurn} /> : null}
              {forkableTurn !== undefined ? (
                <JumpLink label="Fork boundary" turn={forkableTurn} />
              ) : null}
            </div>
            <div className="divide-y rounded-lg border bg-card" aria-label="Timeline turns">
              {narrative.turns.map((turn) => (
                <TimelineTurnRow key={turn.id} onOpenForkTurn={onOpenForkTurn} turn={turn} />
              ))}
            </div>
          </>
        )}
      </div>
    </Pane>
  );
}

type LongRunTimelineItem = {
  artifactId?: string | null;
  detail: string;
  eventRange?: string | null;
  kind: string;
  sequence: number;
  source: string;
  title: string;
  tone: "destructive" | "info" | "muted" | "outline" | "success" | "warning";
};

function LongRunEvidenceTimeline({ items }: { items: LongRunTimelineItem[] }) {
  return (
    <section aria-label="Long-run evidence timeline">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold tracking-normal">Long-run evidence</h4>
        <Badge variant={items.length > 0 ? "info" : "muted"}>{items.length} items</Badge>
      </div>
      {items.length === 0 ? (
        <EmptyLine value="No checkpoint, compaction, attempt, or recovery timeline items are attached to this snapshot." />
      ) : (
        <DataList density="compact">
          {items.map((item) => (
            <DataListItem key={`${item.kind}:${item.sequence}:${item.title}`}>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <DataListLabel>{item.title}</DataListLabel>
                  <DataListMeta>{item.detail}</DataListMeta>
                </div>
                <Badge variant={item.tone}>{item.kind}</Badge>
              </div>
              <p className="mt-2 break-all text-xs text-muted-foreground">
                {item.source}
                {item.eventRange ? ` · ${item.eventRange}` : ""}
                {item.artifactId ? ` · artifact ${item.artifactId}` : ""}
              </p>
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  );
}

function buildLongRunTimeline(data: DashboardState): LongRunTimelineItem[] {
  const items: LongRunTimelineItem[] = [];
  for (const checkpoint of data.checkpointHistory) {
    items.push({
      detail: `${checkpoint.objective}; next: ${checkpoint.next_action}`,
      eventRange: `source events ${checkpoint.source_start_sequence}-${checkpoint.source_end_sequence}`,
      kind: "checkpoint",
      sequence: checkpoint.last_sequence,
      source: `checkpoint ${checkpoint.checkpoint_id}`,
      title: checkpoint.completed_step ?? checkpoint.current_phase ?? "Task checkpoint",
      tone: checkpoint.blockers.length > 0 ? "warning" : "success",
    });
  }

  const compactions = data.runtimeContext?.context_compactions;
  for (const compaction of compactions?.items ?? []) {
    items.push({
      artifactId: compaction.artifact_id,
      detail: compaction.summary,
      eventRange: `source events ${compaction.source_start_sequence}-${compaction.source_end_sequence}`,
      kind: "compaction",
      sequence: compaction.source_end_sequence,
      source: `compaction ${compaction.compaction_id}`,
      title: `${compaction.scope} compaction`,
      tone: "info",
    });
  }
  for (const compaction of compactions?.stale_items ?? []) {
    items.push({
      artifactId: compaction.artifact_id,
      detail: compaction.reason,
      eventRange: `source events ${compaction.source_start_sequence}-${compaction.source_end_sequence}`,
      kind: "stale compaction",
      sequence: compaction.source_end_sequence,
      source: `compaction ${compaction.compaction_id}`,
      title: `${compaction.scope} compaction stale`,
      tone: "warning",
    });
  }

  for (const attempt of data.recentToolAttempts) {
    items.push({
      artifactId: attempt.output_artifact_id,
      detail: attempt.message ?? attempt.retry_reason ?? attempt.status,
      kind: "tool attempt",
      sequence: attempt.last_sequence,
      source: `attempt ${attempt.tool_attempt_id}`,
      title: `${attempt.tool_name} ${attempt.status}`,
      tone: attempt.status === "failed" || attempt.status === "stale" ? "warning" : "outline",
    });
  }

  for (const approval of data.pendingApprovals) {
    items.push({
      detail: `${approval.subject}: ${approval.reason}`,
      kind: "approval",
      sequence: data.lastSequence,
      source: `approval ${approval.approval_id}`,
      title: "Pending approval",
      tone: "warning",
    });
  }
  if (data.pendingQuestionId !== null) {
    items.push({
      detail: data.pendingQuestionText ?? "Question text is not retained in this snapshot.",
      kind: "question",
      sequence: data.lastSequence,
      source: `question ${data.pendingQuestionId}`,
      title: "Pending question",
      tone: "warning",
    });
  }
  if (data.turnRecoveryPosture != null) {
    items.push({
      detail: data.turnRecoveryPosture.reason ?? data.turnRecoveryPosture.next_action,
      kind: "recovery",
      sequence: data.lastSequence,
      source: `turn ${data.turnRecoveryPosture.turn_id}`,
      title: `Recovery ${data.turnRecoveryPosture.state}`,
      tone: data.turnRecoveryPosture.safe_to_resume === false ? "warning" : "info",
    });
  }

  for (const event of data.eventLog) {
    if (!isLongRunTimelineEvent(event.event_type)) {
      continue;
    }
    items.push({
      detail: `canonical event sequence ${event.sequence}`,
      kind: eventKindLabel(event.event_type),
      sequence: event.sequence,
      source: `event ${event.event_type}`,
      title: event.event_type,
      tone: eventTone(event.event_type),
    });
  }

  return items
    .sort((left, right) => right.sequence - left.sequence || left.title.localeCompare(right.title))
    .slice(0, 40);
}

function isLongRunTimelineEvent(eventType: string): boolean {
  return /Checkpoint|Compaction|ToolAttempt|Verification|Approval|Question|Cancellation|Recovery|Resume/.test(
    eventType,
  );
}

function eventKindLabel(eventType: string): string {
  if (eventType.includes("Verification")) {
    return "verification";
  }
  if (eventType.includes("Cancellation")) {
    return "cancellation";
  }
  if (eventType.includes("Recovery") || eventType.includes("Resume")) {
    return "recovery";
  }
  if (eventType.includes("Approval")) {
    return "approval";
  }
  if (eventType.includes("Question")) {
    return "question";
  }
  if (eventType.includes("Compaction")) {
    return "compaction";
  }
  if (eventType.includes("Checkpoint")) {
    return "checkpoint";
  }
  return "event";
}

function eventTone(eventType: string): LongRunTimelineItem["tone"] {
  if (/Failed|Stale|Invalidated|Cancelled|Cancellation|Denied/.test(eventType)) {
    return "warning";
  }
  if (/Completed|Approved|Created|Recorded/.test(eventType)) {
    return "success";
  }
  return "outline";
}

function TimelineTurnRow({
  onOpenForkTurn,
  turn,
}: {
  onOpenForkTurn?: (turnId: string | null) => void;
  turn: SessionNarrativeTurn;
}) {
  const metric = turn.items.find((item) => item.kind === "metric");
  const forkBoundary = turn.items.find((item) => item.kind === "fork-boundary");
  const pendingCount = turn.items.filter(
    (item) => item.kind === "approval" || item.kind === "question",
  ).length;
  const toolCount = turn.items.filter((item) => item.kind === "tool-call").length;
  const liveOutputCount = turn.items.filter((item) => item.kind === "live-output").length;
  const failure = turn.items.find((item) => item.kind === "failure");

  return (
    <article
      className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_auto]"
      id={narrativeTurnDomId(turn)}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="break-words text-sm font-semibold tracking-normal">{turn.title}</h4>
          <StatusBadge status={turn.status} />
          {turn.isFallback ? <Badge variant="outline">partial</Badge> : null}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {turn.turnId ?? "unassigned evidence"}
          {turn.sequence !== null ? ` · sequence ${turn.sequence}` : ""}
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
          {metric?.kind === "metric" ? (
            <span>
              {metric.metric.model_call_count} model · {metric.metric.tool_call_count} tools ·{" "}
              {formatDuration(metric.metric.turn_duration_ms)}
            </span>
          ) : null}
          {pendingCount > 0 ? <span>{pendingCount} pending intervention</span> : null}
          {toolCount > 0 ? <span>{toolCount} active tool</span> : null}
          {liveOutputCount > 0 ? <span>{liveOutputCount} live output</span> : null}
          {failure?.kind === "failure" ? <span>{failure.message}</span> : null}
        </div>
      </div>
      {forkBoundary?.kind === "fork-boundary" ? (
        <div className="flex items-start sm:justify-end">
          <Button
            onClick={() => onOpenForkTurn?.(forkBoundary.turn.turn_id)}
            size="xs"
            type="button"
            variant="outline"
          >
            Open fork flow for {forkBoundary.turn.label}
          </Button>
        </div>
      ) : null}
    </article>
  );
}
