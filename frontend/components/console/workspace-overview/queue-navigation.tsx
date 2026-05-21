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
        <Badge variant={data.operatorQueueCounts.total > 0 ? "warning" : "muted"}>
          {data.operatorQueueCounts.total} operator
        </Badge>
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
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "tasks",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Tasks
          <Badge variant="info">Autonomy</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Inspect durable plans, blockers, verification, and task events.
        </span>
      </a>
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "changesets",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Changesets
          <Badge variant="info">Review</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Inspect local change evidence, source references, and safe next actions.
        </span>
      </a>
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "handoffs",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Handoffs
          <Badge variant="info">Local</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Preview exports, inspect packages, triage imports, and record custody.
        </span>
      </a>
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "memory",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Memory
          <Badge variant="info">Context</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Curate confirmed, stale, and invalidated workspace knowledge.
        </span>
      </a>
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "repository",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Repository Index
          <Badge variant="info">Local</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Inspect index freshness, provenance, search results, and rebuilds.
        </span>
      </a>
      <a
        className="mb-3 grid min-h-density-row rounded-md border border-border/70 bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: null,
          selectedTaskId: null,
          surface: "branches",
          tab: "overview",
          taskQueue: "active",
        })}
      >
        <span className="flex items-center justify-between gap-3 text-sm font-medium">
          Branch Search
          <Badge variant="info">Compare</Badge>
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Compare candidate strategies and mark selection metadata.
        </span>
      </a>
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
  if (data.operatorQueueCounts.work_blocking > 0) {
    return {
      description: "Unified queue has action-needed work before lower-priority sessions.",
      icon: operatorStatusTokens.actionNeeded.icon,
      label: `${data.operatorQueueCounts.work_blocking} action-needed`,
      variant: "warning" as const,
    };
  }
  if (data.operatorQueueCounts.verification_blocking > 0) {
    return {
      description: "Verification evidence is blocking confidence claims.",
      icon: operatorStatusTokens.degraded.icon,
      label: `${data.operatorQueueCounts.verification_blocking} verification`,
      variant: "info" as const,
    };
  }
  if (data.operatorQueueCounts.review_blocking > 0) {
    return {
      description: "Review handoff needs response-linked evidence or risk decisions.",
      icon: operatorStatusTokens.approval.icon,
      label: `${data.operatorQueueCounts.review_blocking} review`,
      variant: "warning" as const,
    };
  }
  if (data.operatorQueueCounts.maintenance > 0) {
    return {
      description: "Maintenance queue items need upkeep before they become blockers.",
      icon: operatorStatusTokens.degraded.icon,
      label: `${data.operatorQueueCounts.maintenance} maintenance`,
      variant: "outline" as const,
    };
  }
  if (data.operatorQueueCounts.advisory + data.operatorQueueCounts.informational > 0) {
    return {
      description: "Advisory queue items are visible without blocking current work.",
      icon: operatorStatusTokens.unknown.icon,
      label: `${data.operatorQueueCounts.advisory + data.operatorQueueCounts.informational} advisory`,
      variant: "muted" as const,
    };
  }
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
