import { useState } from "react";
import { ChevronDown, MessageSquareText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import type { DetailPageStatus } from "@/stores/dashboard-stores";

const INITIAL_TURN_WINDOW = 40;

export function TranscriptPane({
  data,
  onLoadMore,
  page,
}: {
  data: DashboardState;
  onLoadMore?: () => void;
  page?: DetailPageStatus;
}) {
  const [visibleTurnCount, setVisibleTurnCount] = useState(INITIAL_TURN_WINDOW);
  const narrative = buildSessionNarrative(data);
  const visibleTurns = narrative.turns.slice(-visibleTurnCount);
  const hiddenTurnCount = Math.max(narrative.turns.length - visibleTurns.length, 0);
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
            {hiddenTurnCount > 0 ? (
              <Button
                onClick={() => setVisibleTurnCount((count) => count + INITIAL_TURN_WINDOW)}
                size="sm"
                type="button"
                variant="outline"
              >
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
                Show {Math.min(hiddenTurnCount, INITIAL_TURN_WINDOW)} earlier turns
              </Button>
            ) : null}
            {visibleTurns.map((turn) => (
              <NarrativeTurnCard key={turn.id} turn={turn} />
            ))}
          </div>
          <LoadMoreDetail page={page} onLoadMore={onLoadMore} />
        </div>
      )}
    </Pane>
  );
}

function LoadMoreDetail({
  onLoadMore,
  page,
}: {
  onLoadMore?: () => void;
  page?: DetailPageStatus;
}) {
  if (page === undefined || !page.hasMore) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-md border bg-card p-3">
      <Button
        disabled={page.state === "loading"}
        onClick={onLoadMore}
        size="sm"
        type="button"
        variant="outline"
      >
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
        {page.state === "loading" ? "Loading" : "Load more transcript"}
      </Button>
      {page.error !== null ? (
        <p className="text-xs text-destructive">{page.error}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Next cursor {page.nextCursor}</p>
      )}
    </div>
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
