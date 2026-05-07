import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import type { ChangesetDetailState } from "@/stores/dashboard-stores";

import { handoffBadgeVariant, readinessBadgeVariant } from "./format";
import { Section } from "./shared";

export function CommitPreparationPanel({ detail }: { detail: ChangesetDetailState }) {
  const readiness = detail.commitReadiness;
  const suggestion = detail.commitMessage;
  const handoffReadiness = detail.handoffReadiness;
  if (readiness === null && suggestion === null) {
    return (
      <Section title="Commit Preparation">
        <p className="text-sm text-muted-foreground">
          Commit readiness and message suggestion are not loaded yet.
        </p>
      </Section>
    );
  }
  const riskyPaths = readiness
    ? [
        ...readiness.git.policy_sensitive_paths,
        ...readiness.git.generated_paths,
        ...readiness.git.unstaged_paths,
        ...readiness.git.untracked_paths,
      ].filter((path, index, paths) => paths.indexOf(path) === index)
    : [];
  const blockingSignals = readiness?.signals.filter((signal) => signal.blocking) ?? [];
  return (
    <Section title="Commit Preparation">
      <div className="grid gap-3">
        {readiness ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={readinessBadgeVariant(readiness.state)}>
                {readiness.state.replaceAll("_", " ")}
              </Badge>
              <Badge variant="outline">{readiness.git.staged_path_count} staged</Badge>
              <Badge variant={readiness.git.untracked_paths.length > 0 ? "warning" : "muted"}>
                {readiness.git.untracked_paths.length} untracked
              </Badge>
              <Badge variant={readiness.unresolved_feedback_count > 0 ? "warning" : "muted"}>
                {readiness.unresolved_feedback_count} unresolved feedback
              </Badge>
              <Badge variant={readiness.stale_response_count > 0 ? "warning" : "muted"}>
                {readiness.stale_response_count} stale responses
              </Badge>
              <Badge variant={readiness.local_only_evidence_count > 0 ? "info" : "muted"}>
                {readiness.local_only_evidence_count} local-only evidence
              </Badge>
              {handoffReadiness ? (
                <Badge variant={handoffBadgeVariant(handoffReadiness.state)}>
                  Handoff {handoffReadiness.state.replaceAll("_", " ")}
                </Badge>
              ) : null}
            </div>
            <p className="text-sm text-muted-foreground">{readiness.reason}</p>
            <DataList density="compact">
              <DataListItem>
                <DataListLabel>Review loop</DataListLabel>
                <DataListMeta>
                  {readiness.review_feedback_count} feedback, {readiness.unresolved_feedback_count}{" "}
                  unresolved, {readiness.stale_response_count} stale responses
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Manual evidence</DataListLabel>
                <DataListMeta>
                  {readiness.manual_evidence_count} attached, {readiness.local_only_evidence_count}{" "}
                  local-only
                </DataListMeta>
              </DataListItem>
              {handoffReadiness ? (
                <DataListItem>
                  <DataListLabel>Handoff posture</DataListLabel>
                  <DataListMeta>{handoffReadiness.reason}</DataListMeta>
                </DataListItem>
              ) : null}
            </DataList>
            {blockingSignals.length > 0 ? (
              <DataList density="compact">
                {blockingSignals.slice(0, 5).map((signal) => (
                  <DataListItem key={signal.signal_id}>
                    <DataListLabel>{signal.signal_id.replaceAll("-", " ")}</DataListLabel>
                    <DataListMeta>{signal.summary}</DataListMeta>
                  </DataListItem>
                ))}
              </DataList>
            ) : null}
            {riskyPaths.length > 0 ? (
              <div>
                <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
                  Risky or ambiguous paths
                </h4>
                <ul className="mt-2 grid gap-2 text-console text-muted-foreground">
                  {riskyPaths.slice(0, 8).map((path) => (
                    <li className="break-all" key={path}>
                      {path}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : null}
        {suggestion ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Suggested message
            </h4>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-border/70 bg-surface px-3 py-2 text-console">
              {suggestion.message}
            </pre>
          </div>
        ) : null}
        {readiness?.safe_next_actions.length ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Safe next commands
            </h4>
            <ul className="mt-2 grid gap-2 text-console text-muted-foreground">
              {readiness.safe_next_actions.map((action) => (
                <li className="break-all" key={action}>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="text-xs text-muted-foreground">
          Glassbox did not stage, commit, push, or open a PR.
        </p>
      </div>
    </Section>
  );
}
