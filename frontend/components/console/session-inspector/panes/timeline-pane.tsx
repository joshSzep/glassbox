import { History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

  return (
    <Pane icon={History} title="Timeline">
      {narrative.turns.length === 0 ? (
        <EmptyLine value="No timeline events are available." />
      ) : (
        <div className="space-y-4">
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
        </div>
      )}
    </Pane>
  );
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
