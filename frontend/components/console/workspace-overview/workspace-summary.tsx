import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { DashboardState } from "@/state/session-state";
import type { LoadState } from "@/stores/dashboard-stores";

export function WorkspaceSummary({
  data,
  loadState,
}: {
  data: DashboardState;
  loadState: LoadState;
}) {
  return (
    <section
      className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm"
      aria-label="Workspace overview"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
            Workspace
          </h2>
          <p className="mt-1 break-all text-sm font-medium">
            {data.runtimeSummary.workspace_root || "Local workspace"}
          </p>
        </div>
        <Badge variant={loadState === "failed" ? "destructive" : "outline"}>{loadState}</Badge>
      </div>
      <Separator className="my-3" />
      <div className="grid grid-cols-2 gap-2">
        <MetricTile label="Total" value={data.queueCounts.total} />
        <MetricTile label="Action" value={data.queueCounts.action_needed} variant="warning" />
        <MetricTile label="Approvals" value={data.queueCounts.approvals} />
        <MetricTile label="Questions" value={data.queueCounts.questions} />
      </div>
    </section>
  );
}

function MetricTile({
  label,
  value,
  variant = "outline",
}: {
  label: string;
  value: number | string;
  variant?: "outline" | "success" | "warning";
}) {
  return (
    <div className="min-h-16 rounded-md border border-border/70 bg-surface p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <Badge className="mt-2 justify-start" variant={variant}>
        {value}
      </Badge>
    </div>
  );
}
