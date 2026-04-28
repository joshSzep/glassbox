import { CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass, operatorStatusTokens } from "@/design-system/operator-status";
import { buildAppRoute, type AppQueue } from "@/routing/app-route";
import { queueDescriptors } from "./queue-descriptors";
import type { DashboardState } from "@/state/session-state";
import type { ConsoleFilters } from "@/stores/dashboard-stores";

export function QueueNavigation({
  data,
  onSelectQueue,
  selectedQueue,
}: {
  data: DashboardState;
  onSelectQueue?: (queue: ConsoleFilters["queue"]) => void;
  selectedQueue: ConsoleFilters["queue"];
}) {
  const priority = queuePrioritySummary(data);
  const PriorityIcon = priority.icon;
  return (
    <nav
      className="rounded-md border border-border/80 bg-card p-3 text-card-foreground shadow-sm"
      aria-label="Action queues"
    >
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Queues
        </h2>
        <Badge variant="muted">{data.queueCounts.total}</Badge>
      </div>
      <section
        className="mb-3 rounded-md border border-border/70 bg-surface p-3"
        aria-label="Queue priority summary"
      >
        <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
          Top priority
        </p>
        <Badge className="mt-2 max-w-full justify-start" variant={priority.variant}>
          <PriorityIcon className={operatorIconSizeClass} aria-hidden="true" />
          <span className="truncate">{priority.label}</span>
        </Badge>
        <p className="mt-2 text-xs text-muted-foreground">{priority.description}</p>
      </section>
      <div className="grid gap-1">
        {queueDescriptors.map((queue) => {
          const selected = selectedQueue === queue.queue;
          const count = data.queueCounts[queue.countKey];
          return (
            <a
              aria-current={selected ? "page" : undefined}
              className={`grid min-h-density-row rounded-md px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                selected ? "bg-accent text-accent-foreground" : "hover:bg-surface-raised"
              }`}
              href={buildAppRoute({
                compareSessionId: null,
                queue: queue.queue as AppQueue,
                selectedSessionId: null,
                tab: "overview",
              })}
              key={queue.queue}
              onClick={(event) => {
                if (onSelectQueue === undefined) {
                  return;
                }
                event.preventDefault();
                onSelectQueue(queue.queue);
              }}
            >
              <span className="flex items-center justify-between gap-3 text-sm font-medium">
                {queue.label}
                <Badge variant={count > 0 ? "warning" : "muted"}>{count}</Badge>
              </span>
              <span className="mt-1 text-xs text-muted-foreground">{queue.description}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}

function queuePrioritySummary(data: DashboardState) {
  if (data.queueCounts.approvals > 0) {
    return {
      description: "Review approval risk before prompts, forks, or passive evidence.",
      icon: operatorStatusTokens.approval.icon,
      label: `${data.queueCounts.approvals} approvals`,
      variant: "warning" as const,
    };
  }
  if (data.queueCounts.questions > 0) {
    return {
      description: "Answer pending ask_user questions before sending new prompts.",
      icon: operatorStatusTokens.question.icon,
      label: `${data.queueCounts.questions} questions`,
      variant: "info" as const,
    };
  }
  if (data.queueCounts.failures > 0) {
    return {
      description: "Inspect retryability and failure summaries before lower-priority work.",
      icon: operatorStatusTokens.failed.icon,
      label: `${data.queueCounts.failures} failures`,
      variant: "destructive" as const,
    };
  }
  if (data.queueCounts.degraded > 0) {
    return {
      description: "Projection health needs attention; canonical events remain authoritative.",
      icon: operatorStatusTokens.degraded.icon,
      label: `${data.queueCounts.degraded} degraded`,
      variant: "warning" as const,
    };
  }
  if (data.queueCounts.active > 0) {
    return {
      description: "Active work is available after urgent queues are clear.",
      icon: operatorStatusTokens.active.icon,
      label: `${data.queueCounts.active} active`,
      variant: "success" as const,
    };
  }
  if (data.queueCounts.historical > 0) {
    return {
      description: "Only historical snapshots remain for inspection.",
      icon: operatorStatusTokens.historical.icon,
      label: `${data.queueCounts.historical} historical`,
      variant: "muted" as const,
    };
  }
  return {
    description: "All queues are clear for this workspace.",
    icon: CheckCircle2,
    label: "queues clear",
    variant: "success" as const,
  };
}
