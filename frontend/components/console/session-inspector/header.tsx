import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";

export function SessionHeader({
  data,
  stream,
}: {
  data: DashboardState;
  stream: SessionStreamState;
}) {
  return (
    <header className="border-b p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Selected session
          </p>
          <h2 className="mt-1 break-all text-lg font-semibold tracking-normal">{data.sessionId}</h2>
          <p className="mt-1 break-all text-sm text-muted-foreground">
            {data.cwd ?? "workspace unknown"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={data.status === "failed" ? "destructive" : "outline"}>
            {data.status}
          </Badge>
          <Badge variant={stream.status === "live" ? "success" : "muted"}>{stream.status}</Badge>
          <ProjectionBadge
            state={data.projectionHealth?.state ?? "unknown"}
            degraded={Boolean(data.projectionHealth?.degraded)}
          />
        </div>
      </div>
      <Separator className="my-3" />
      <div className="grid gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <HeaderFact label="Model" value={data.modelName ?? "unknown"} />
        <HeaderFact label="Last sequence" value={String(data.lastSequence)} />
        <HeaderFact label="Lineage" value={lineageLabel(data)} />
        <HeaderFact label="Next action" value={nextActionLabel(data)} />
      </div>
    </header>
  );
}

function HeaderFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-medium">{value}</p>
    </div>
  );
}

function ProjectionBadge({ degraded, state }: { degraded: boolean; state: string }) {
  return (
    <Badge variant={degraded || state !== "ok" ? "warning" : "success"}>projection {state}</Badge>
  );
}

function lineageLabel(data: DashboardState): string {
  if (data.parentSessionId !== null) {
    return `parent ${data.parentSessionId}`;
  }
  if (data.childSessions.length > 0) {
    return `${data.childSessions.length} child sessions`;
  }
  return data.branchLabel ?? "root session";
}

function nextActionLabel(data: DashboardState): string {
  if (data.pendingApprovalId !== null) {
    return `approval ${data.pendingApprovalId}`;
  }
  if (data.pendingQuestionId !== null) {
    return `question ${data.pendingQuestionId}`;
  }
  if (data.currentTurn !== null) {
    return data.currentTurn.status;
  }
  return data.canFork ? "fork available" : "inspect";
}
