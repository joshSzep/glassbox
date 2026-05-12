import {
  AlertTriangle,
  ClipboardCheck,
  ExternalLink,
  FileSearch,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import { buildAppRoute } from "@/routing/app-route";
import type { DashboardState, OperatorQueueItem } from "@/state/session-state";

type QueueLane = {
  count: (data: DashboardState) => number;
  description: string;
  families: OperatorQueueItem["family"][];
  icon: typeof AlertTriangle;
  label: string;
  variant: NonNullable<BadgeProps["variant"]>;
};

const queueLanes: QueueLane[] = [
  {
    count: (data) => data.operatorQueueCounts.work_blocking,
    description: "Blocked turns, approvals, questions, and failed active work.",
    families: ["work_blocking"],
    icon: AlertTriangle,
    label: "Action Needed",
    variant: "warning",
  },
  {
    count: (data) => data.operatorQueueCounts.verification_blocking,
    description: "Failed, stale, skipped, or missing confidence evidence.",
    families: ["verification_blocking"],
    icon: ClipboardCheck,
    label: "Verification",
    variant: "info",
  },
  {
    count: (data) => data.operatorQueueCounts.review_blocking,
    description: "Review handoff blockers and response-linked fixup evidence.",
    families: ["review_blocking"],
    icon: FileSearch,
    label: "Review",
    variant: "warning",
  },
  {
    count: (data) => data.operatorQueueCounts.maintenance,
    description: "Runtime, projection, repository, artifact, and job upkeep.",
    families: ["maintenance"],
    icon: Wrench,
    label: "Maintenance",
    variant: "outline",
  },
  {
    count: (data) => data.operatorQueueCounts.advisory + data.operatorQueueCounts.informational,
    description: "Useful context, watch items, and non-blocking recommendations.",
    families: ["advisory", "informational"],
    icon: ShieldCheck,
    label: "Advisory",
    variant: "muted",
  },
];

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

function OperatorQueueRow({
  item,
  onSelectSession,
}: {
  item: OperatorQueueItem;
  onSelectSession?: (sessionId: string) => void;
}) {
  const targetHref = targetLink(item);
  const targetText = targetLabel(item);

  return (
    <article
      className="grid min-w-0 gap-3 rounded-md border border-border/70 bg-surface px-3 py-3 text-left text-sm transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      tabIndex={0}
    >
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <TargetLink href={targetHref} item={item} onSelectSession={onSelectSession}>
            {item.safe_next_action.title}
          </TargetLink>
          <p className="mt-1 break-words text-xs text-muted-foreground">{targetText}</p>
        </div>
        <div className="flex max-w-full flex-wrap justify-start gap-1 sm:justify-end">
          <Badge variant={severityVariant(item.severity)}>{item.severity}</Badge>
          <Badge variant={priorityVariant(item.priority)}>{item.priority}</Badge>
          <Badge variant={item.stale ? "warning" : "outline"}>
            {item.stale ? "stale" : item.state}
          </Badge>
        </div>
      </div>

      <dl className="grid gap-2 text-xs sm:grid-cols-2">
        <QueueDetail label="Reason" value={item.safe_next_action.summary} />
        <QueueDetail label="Safe action" value={safeActionText(item)} />
        <QueueDetail label="Evidence" value={item.evidence_summary.summary} />
        <QueueDetail label="Freshness" value={freshnessText(item)} />
        <QueueDetail label="Confidence" value={item.safe_next_action.confidence} />
        <QueueDetail label="Limitations" value={limitationsText(item)} />
      </dl>

      <QueueDeepLinks item={item} targetHref={targetHref} />
    </article>
  );
}

function TargetLink({
  children,
  href,
  item,
  onSelectSession,
}: {
  children: string;
  href: string | null;
  item: OperatorQueueItem;
  onSelectSession?: (sessionId: string) => void;
}) {
  if (href === null) {
    return <p className="break-words font-semibold">{children}</p>;
  }
  return (
    <a
      className="break-words font-semibold text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      href={href}
      onClick={(event) => {
        if (
          onSelectSession === undefined ||
          item.target.kind !== "session" ||
          item.target.target_id === null ||
          item.target.target_id === undefined
        ) {
          return;
        }
        event.preventDefault();
        onSelectSession(item.target.target_id);
      }}
    >
      {children}
    </a>
  );
}

function QueueDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 break-words text-foreground">{value}</dd>
    </div>
  );
}

function QueueDeepLinks({
  item,
  targetHref,
}: {
  item: OperatorQueueItem;
  targetHref: string | null;
}) {
  const links = deepLinks(item, targetHref);
  if (links.length === 0) {
    return null;
  }

  return (
    <div className="flex min-w-0 flex-wrap gap-2 border-t border-border/70 pt-2 text-xs">
      {links.map((link) => (
        <a
          className="inline-flex min-w-0 items-center gap-1 rounded-md border border-border/70 bg-card px-2 py-1"
          href={link.href}
          key={`${link.label}:${link.href}`}
        >
          <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="shrink-0 text-muted-foreground">{link.label}</span>
          <span className="min-w-0 truncate font-mono text-foreground">{link.href}</span>
        </a>
      ))}
    </div>
  );
}

function targetLink(item: OperatorQueueItem): string | null {
  const targetId = item.target.target_id ?? null;
  switch (item.target.kind) {
    case "session":
      return targetId === null
        ? null
        : buildAppRoute({
            compareSessionId: null,
            queue: "all",
            selectedSessionId: targetId,
            tab: "overview",
          });
    case "task":
      return targetId === null
        ? buildAppRoute({
            compareSessionId: null,
            queue: "all",
            selectedSessionId: null,
            surface: "tasks",
            tab: "overview",
          })
        : buildAppRoute({
            compareSessionId: null,
            queue: "all",
            selectedSessionId: null,
            selectedTaskId: targetId,
            surface: "tasks",
            tab: "overview",
          });
    case "changeset":
    case "review_feedback":
    case "verification":
      return changesetScopedLink(item.target.kind, targetId);
    case "repository_intelligence":
      return repositoryLink(targetId ?? item.safe_next_action.command?.cwd_hint ?? null);
    case "background_job":
      return queryRoute("/app/tasks", "job", targetId);
    case "artifact":
      return queryRoute("/app", "artifact", targetId);
    case "provider":
      return queryRoute("/app", "provider", targetId ?? item.target.label ?? null);
    case "projection":
      return queryRoute("/app", "projection", targetId);
    default:
      return null;
  }
}

function changesetScopedLink(kind: OperatorQueueItem["target"]["kind"], targetId: string | null) {
  if (targetId === null) {
    return buildAppRoute({
      compareSessionId: null,
      queue: "all",
      selectedSessionId: null,
      surface: "changesets",
      tab: "overview",
    });
  }
  if (kind === "changeset") {
    return buildAppRoute({
      compareSessionId: null,
      queue: "all",
      selectedChangesetId: targetId,
      selectedSessionId: null,
      surface: "changesets",
      tab: "overview",
    });
  }
  return queryRoute(
    "/app/changesets",
    kind === "verification" ? "verification" : "feedback",
    targetId,
  );
}

function deepLinks(item: OperatorQueueItem, targetHref: string | null) {
  const links: { href: string; label: string }[] = [];
  if (targetHref !== null) {
    links.push({ href: targetHref, label: "target" });
  }
  if (item.evidence_summary.evidence_graph_id) {
    links.push({
      href: queryRoute("/app/changesets", "evidenceGraph", item.evidence_summary.evidence_graph_id),
      label: "evidence graph",
    });
  }
  if (item.evidence_summary.claim_id) {
    links.push({
      href: queryRoute("/app/changesets", "claim", item.evidence_summary.claim_id),
      label: "claim",
    });
  }
  for (const ref of [
    ...(item.evidence_summary.supporting_evidence ?? []),
    ...(item.evidence_summary.missing_evidence ?? []),
    ...(item.evidence_summary.stale_evidence ?? []),
  ].slice(0, 3)) {
    links.push({
      href: evidenceLink(ref.kind, ref.ref_id, item.target.target_id ?? null),
      label: ref.kind.replaceAll("_", " "),
    });
  }
  return links;
}

function evidenceLink(kind: string, refId: string, targetId: string | null): string {
  switch (kind) {
    case "artifact":
      return queryRoute("/app", "artifact", refId);
    case "background_job":
      return queryRoute("/app/tasks", "job", refId);
    case "projection":
      return queryRoute("/app", "projection", refId);
    case "repository_intelligence":
      return repositoryLink(refId);
    case "review_feedback":
      return queryRoute("/app/changesets", "feedback", refId);
    case "verification":
      return queryRoute("/app/changesets", "verification", refId);
    case "tool_attempt":
      return targetId === null
        ? queryRoute("/app", "toolAttempt", refId)
        : queryRoute(`/app/sessions/${encodeURIComponent(targetId)}`, "toolAttempt", refId);
    default:
      return queryRoute("/app", "evidence", refId);
  }
}

function repositoryLink(path: string | null): string {
  return path === null
    ? "/app/repository-index"
    : queryRoute("/app/repository-index", "path", path);
}

function queryRoute(path: string, key: string, value: string | null): string {
  if (value === null) {
    return path;
  }
  const params = new URLSearchParams();
  params.set(key, value);
  return `${path}?${params.toString()}`;
}

function targetLabel(item: OperatorQueueItem): string {
  const target = item.target.label ?? item.target.target_id ?? "workspace";
  return `${item.target.kind.replaceAll("_", " ")}: ${target}`;
}

function safeActionText(item: OperatorQueueItem): string {
  const command = item.safe_next_action.command;
  if (command === null || command === undefined) {
    return item.safe_next_action.kind.replaceAll("_", " ");
  }
  return command.display || command.command.join(" ");
}

function freshnessText(item: OperatorQueueItem): string {
  const evidence = [
    ...(item.evidence_summary.supporting_evidence ?? []),
    ...(item.evidence_summary.missing_evidence ?? []),
    ...(item.evidence_summary.stale_evidence ?? []),
  ];
  const freshness = evidence
    .map((ref) => ref.freshness)
    .filter((value): value is string => value !== null && value !== undefined);
  if (item.stale) {
    return freshness.length === 0 ? "stale" : `stale; ${freshness.join(", ")}`;
  }
  if (freshness.length === 0) {
    return "current or not time-sensitive";
  }
  return freshness.join(", ");
}

function limitationsText(item: OperatorQueueItem): string {
  const limitations = [
    ...(item.limitations ?? []),
    ...(item.safe_next_action.limitations ?? []),
  ].filter((value, index, values) => values.indexOf(value) === index);
  if (limitations.length === 0 && item.evidence_summary.limitation_count === 0) {
    return "none reported";
  }
  if (limitations.length === 0) {
    return `${item.evidence_summary.limitation_count} evidence limitation${
      item.evidence_summary.limitation_count === 1 ? "" : "s"
    }`;
  }
  return limitations.join("; ");
}

function severityVariant(
  severity: OperatorQueueItem["severity"],
): NonNullable<BadgeProps["variant"]> {
  return severity === "critical" || severity === "high"
    ? "destructive"
    : severity === "medium"
      ? "warning"
      : severity === "low"
        ? "info"
        : "muted";
}

function priorityVariant(
  priority: OperatorQueueItem["priority"],
): NonNullable<BadgeProps["variant"]> {
  return priority === "blocked" || priority === "action-needed"
    ? "warning"
    : priority === "degraded"
      ? "destructive"
      : priority === "recommended"
        ? "info"
        : "muted";
}
