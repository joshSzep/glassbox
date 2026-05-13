import { buildAppRoute } from "@/routing/app-route";
import type { OperatorQueueItem } from "@/state/session-state";

export function targetLink(item: OperatorQueueItem): string | null {
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

export function deepLinks(item: OperatorQueueItem, targetHref: string | null) {
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
