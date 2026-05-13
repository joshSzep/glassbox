import type { BadgeProps } from "@/components/ui/badge";
import type { OperatorQueueItem } from "@/state/session-state";

export function targetLabel(item: OperatorQueueItem): string {
  const target = item.target.label ?? item.target.target_id ?? "workspace";
  return `${item.target.kind.replaceAll("_", " ")}: ${target}`;
}

export function safeActionText(item: OperatorQueueItem): string {
  const command = item.safe_next_action.command;
  if (command === null || command === undefined) {
    return item.safe_next_action.kind.replaceAll("_", " ");
  }
  return command.display || command.command.join(" ");
}

export function freshnessText(item: OperatorQueueItem): string {
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

export function limitationsText(item: OperatorQueueItem): string {
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

export function severityVariant(
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

export function priorityVariant(
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
