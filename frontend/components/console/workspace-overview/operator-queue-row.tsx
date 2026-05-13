import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  freshnessText,
  limitationsText,
  priorityVariant,
  safeActionText,
  severityVariant,
  targetLabel,
} from "@/components/console/workspace-overview/operator-queue-format";
import {
  deepLinks,
  targetLink,
} from "@/components/console/workspace-overview/operator-queue-links";
import type { OperatorQueueItem } from "@/state/session-state";

export function OperatorQueueRow({
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
