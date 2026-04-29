import { Badge, type BadgeProps } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { DashboardState } from "@/state/session-state";

export type WorkingSetItem = NonNullable<
  NonNullable<NonNullable<DashboardState["runtimeContext"]>["working_set"]>["items"]
>[number];

export type EvidenceCue = {
  badge: string;
  detail: string;
  label: string;
  source?: string;
  variant: NonNullable<BadgeProps["variant"]>;
};

export function EvidenceCueList({ cues }: { cues: EvidenceCue[] }) {
  return (
    <section aria-label="Evidence interpretation" className="mb-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Evidence interpretation
      </p>
      <DataList density="compact">
        {cues.map((cue) => (
          <DataListItem key={cue.label}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <DataListLabel>{cue.label}</DataListLabel>
                <DataListMeta>{cue.detail}</DataListMeta>
              </div>
              <Badge variant={cue.variant}>{cue.badge}</Badge>
            </div>
            {cue.source ? (
              <p className="mt-2 break-all text-xs text-muted-foreground">{cue.source}</p>
            ) : null}
          </DataListItem>
        ))}
      </DataList>
    </section>
  );
}

export function VerificationSummary({
  detail,
  label,
  value,
  variant,
}: {
  detail: string;
  label: string;
  value: string;
  variant: "destructive" | "info" | "muted" | "success" | "warning";
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <Badge variant={variant}>{value}</Badge>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

export function WorkingSetProvenance({
  inheritedWorkingSetCount,
  items,
}: {
  inheritedWorkingSetCount: number;
  items: WorkingSetItem[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Working-set provenance
      </p>
      <p className="mb-2 text-sm text-muted-foreground">
        {inheritedWorkingSetCount > 0
          ? `${inheritedWorkingSetCount} inherited item${inheritedWorkingSetCount === 1 ? "" : "s"} may explain drift before current-session changes.`
          : "Working-set items are current to this session."}
      </p>
      <DataList density="compact">
        {items.map((item) => (
          <DataListItem key={`${item.subject_kind}:${item.subject}`}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <DataListLabel>{item.subject}</DataListLabel>
                <DataListMeta>{item.summary}</DataListMeta>
              </div>
              <Badge variant={item.inherited ? "info" : "outline"}>
                {item.inherited ? "inherited working set" : "current working set"}
              </Badge>
            </div>
            <p className="mt-2 break-all text-xs text-muted-foreground">
              {item.signal_types?.join(", ") || "unknown signal"} ·{" "}
              {item.reasons?.join(", ") || "no recorded reason"}
            </p>
          </DataListItem>
        ))}
      </DataList>
    </div>
  );
}
