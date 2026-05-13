import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { DashboardState } from "@/state/session-state";
import {
  type QueueLane,
  queueLanes,
} from "@/components/console/workspace-overview/operator-queue-models";
import { OperatorQueueRow } from "@/components/console/workspace-overview/operator-queue-row";

export function OperatorQueueLanes({
  data,
  onSelectSession,
}: {
  data: DashboardState;
  onSelectSession?: (sessionId: string) => void;
}) {
  if (data.operatorQueue.length === 0 && data.operatorQueueCounts.total === 0) {
    return null;
  }

  return (
    <section className="grid gap-3" aria-label="Unified operator queue">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Unified Operator Queue
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data.operatorQueueCounts.total} ranked item
            {data.operatorQueueCounts.total === 1 ? "" : "s"} from {data.operatorQueueSchemaVersion}
            .
          </p>
        </div>
        <Badge variant={data.operatorQueueCounts.total > 0 ? "warning" : "success"}>
          {data.operatorQueueCounts.total} total
        </Badge>
      </div>

      <div className="grid gap-3 2xl:grid-cols-2" role="list">
        {queueLanes.map((lane) => (
          <OperatorQueueLane
            data={data}
            key={lane.label}
            lane={lane}
            onSelectSession={onSelectSession}
          />
        ))}
      </div>
    </section>
  );
}

function OperatorQueueLane({
  data,
  lane,
  onSelectSession,
}: {
  data: DashboardState;
  lane: QueueLane;
  onSelectSession?: (sessionId: string) => void;
}) {
  const LaneIcon = lane.icon;
  const items = data.operatorQueue.filter((item) => lane.families.includes(item.family));
  const count = lane.count(data);

  return (
    <section
      aria-label={`${lane.label} queue lane`}
      className="min-w-0 rounded-md border border-border/80 bg-card p-3 text-card-foreground shadow-sm"
      role="listitem"
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex min-w-0 items-center gap-2 text-sm font-semibold">
            <LaneIcon className={operatorIconSizeClass} aria-hidden="true" />
            <span className="truncate">{lane.label}</span>
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">{lane.description}</p>
        </div>
        <Badge variant={count > 0 ? lane.variant : "muted"}>{count}</Badge>
      </div>

      <div className="mt-3 grid gap-2">
        {items.length > 0 ? (
          items.map((item) => (
            <OperatorQueueRow item={item} key={item.item_id} onSelectSession={onSelectSession} />
          ))
        ) : (
          <p className="rounded-md border border-border/70 bg-surface px-3 py-2 text-xs text-muted-foreground">
            No visible {lane.label.toLowerCase()} items.
          </p>
        )}
      </div>
    </section>
  );
}
