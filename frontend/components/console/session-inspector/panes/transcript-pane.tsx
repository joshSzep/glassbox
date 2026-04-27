import { MessageSquareText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import {
  formatDuration,
  formatMessage,
  formatTime,
} from "@/components/console/session-inspector/format";
import { JumpLink, StatusBadge, narrativeTurnDomId } from "./shared";
import {
  buildSessionNarrative,
  type DashboardState,
  type SessionNarrativeItem,
  type SessionNarrativeTurn,
} from "@/state/session-state";

export function TranscriptPane({ data }: { data: DashboardState }) {
  const narrative = buildSessionNarrative(data);
  const latestTurn = narrative.turns.at(-1) ?? null;
  const pendingTurn = narrative.turns.find((turn) =>
    turn.items.some((item) => item.kind === "approval" || item.kind === "question"),
  );
  const failedTurn = narrative.turns.find((turn) => turn.status === "failed");

  return (
    <Pane icon={MessageSquareText} title="Transcript">
      {narrative.turns.length === 0 ? (
        <EmptyLine value="No transcript narrative is available." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2" aria-label="Transcript jumps">
            {latestTurn !== null ? <JumpLink label="Latest activity" turn={latestTurn} /> : null}
            {pendingTurn !== undefined ? (
              <JumpLink label="Pending action" turn={pendingTurn} />
            ) : null}
            {failedTurn !== undefined ? <JumpLink label="Failed turn" turn={failedTurn} /> : null}
          </div>
          <div className="space-y-4" aria-label="Session narrative turns">
            {narrative.turns.map((turn) => (
              <NarrativeTurnCard key={turn.id} turn={turn} />
            ))}
          </div>
        </div>
      )}
    </Pane>
  );
}

function NarrativeTurnCard({ turn }: { turn: SessionNarrativeTurn }) {
  return (
    <article
      aria-labelledby={`${narrativeTurnDomId(turn)}-title`}
      className="rounded-md border bg-background p-3"
      id={narrativeTurnDomId(turn)}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h4
            className="break-words text-sm font-semibold tracking-normal"
            id={`${narrativeTurnDomId(turn)}-title`}
          >
            {turn.title}
          </h4>
          <p className="mt-1 text-xs text-muted-foreground">
            {turn.turnId ?? "partial history"}
            {turn.sequence !== null ? ` · sequence ${turn.sequence}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={turn.status} />
          {turn.isFallback ? <Badge variant="outline">partial metadata</Badge> : null}
        </div>
      </div>
      <div className="mt-3 space-y-2">
        {turn.items.map((item, index) => (
          <NarrativeItemRow item={item} key={`${item.kind}:${index}`} />
        ))}
      </div>
    </article>
  );
}

function NarrativeItemRow({ item }: { item: SessionNarrativeItem }) {
  switch (item.kind) {
    case "message":
      return (
        <div className="rounded-md border bg-card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Badge variant={item.message.role === "user" ? "info" : "outline"}>
              {item.message.role}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {formatTime(item.message.created_at)}
            </span>
          </div>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm">
            {formatMessage(item.message)}
          </p>
        </div>
      );
    case "tool-call":
      return (
        <NarrativeLine
          label={item.toolCall.tool_name}
          meta={item.toolCall.summary ?? item.toolCall.status}
        />
      );
    case "approval":
      return (
        <NarrativeLine label={`Approval: ${item.approval.subject}`} meta={item.approval.reason} />
      );
    case "question":
      return <NarrativeLine label="Question" meta={item.text ?? "Awaiting operator answer"} />;
    case "live-output":
      return <NarrativeLine label={`Live ${item.output.stream}`} meta={item.output.chunk} />;
    case "failure":
      return (
        <NarrativeLine
          label={item.retryable ? "Retryable failure" : "Failure"}
          meta={item.message}
          variant="destructive"
        />
      );
    case "metric":
      return (
        <NarrativeLine
          label="Turn metrics"
          meta={`${item.metric.model_call_count} model · ${item.metric.tool_call_count} tools · ${formatDuration(item.metric.turn_duration_ms)}`}
        />
      );
    case "fork-boundary":
      return (
        <NarrativeLine
          label="Fork boundary"
          meta={`${item.turn.label} · sequence ${item.turn.sequence}`}
        />
      );
    case "event-evidence":
      return (
        <NarrativeLine label={item.event.event_type} meta={`sequence ${item.event.sequence}`} />
      );
  }
}

function NarrativeLine({
  label,
  meta,
  variant = "outline",
}: {
  label: string;
  meta: string;
  variant?: "destructive" | "info" | "outline" | "warning";
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <Badge className="justify-start" variant={variant}>
        {label}
      </Badge>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm text-muted-foreground">{meta}</p>
    </div>
  );
}
