"use client";

import type { ReactNode } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSearch,
  GitBranch,
  Loader2,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import { buildAppRoute } from "@/routing/app-route";
import type {
  BranchSearchActionStatus,
  BranchSearchDetailState,
  BranchSearchPageState,
} from "@/stores/dashboard-stores";

type Candidate = NonNullable<BranchSearchDetailState["detail"]>["candidates"][number];
type CandidateDecisionSupport = NonNullable<
  BranchSearchDetailState["detail"]
>["decision_support"]["candidates"][number];

export function BranchSearchList({
  detail,
  onSelectSearch,
  page,
}: {
  detail: BranchSearchDetailState;
  onSelectSearch?: (searchId: string) => void;
  page: BranchSearchPageState;
}) {
  if (page.error !== null) {
    return <StateLine tone="destructive" value={page.error} />;
  }
  if (page.loadState === "loading" && page.items.length === 0) {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Loading branch searches."
      />
    );
  }
  if (page.items.length === 0) {
    return (
      <StateLine
        icon={<CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="No branch searches are available."
      />
    );
  }

  return (
    <aside
      aria-label="Branch search list"
      className="rounded-md border border-border/80 bg-card p-3 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
          Searches
        </h2>
        <Badge variant="muted">{page.items.length}</Badge>
      </div>
      <div className="grid gap-2">
        {page.items.map((search) => (
          <button
            aria-pressed={detail.selectedSearchId === search.search_id}
            className={`grid rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              detail.selectedSearchId === search.search_id
                ? "border-accent bg-accent text-accent-foreground"
                : "border-border/70 hover:bg-surface-raised"
            }`}
            key={search.search_id}
            onClick={() => onSelectSearch?.(search.search_id)}
            type="button"
          >
            <span className="text-sm font-medium">{search.objective}</span>
            <span className="mt-1 text-xs text-muted-foreground">
              {search.candidate_count} candidates · {search.status}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}

export function BranchSearchDetail({
  action,
  detail,
  onMarkCandidate,
}: {
  action: BranchSearchActionStatus;
  detail: BranchSearchDetailState;
  onMarkCandidate?: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    searchId: string;
  }) => void;
}) {
  if (detail.error !== null) {
    return <StateLine tone="destructive" value={detail.error} />;
  }
  if (detail.loadState === "loading") {
    return (
      <StateLine
        icon={<Loader2 className={operatorIconSizeClass} aria-hidden="true" />}
        value="Loading candidate comparison."
      />
    );
  }
  if (detail.detail === null) {
    return (
      <StateLine
        icon={<GitBranch className={operatorIconSizeClass} aria-hidden="true" />}
        value="Select a branch search to compare candidate strategies."
      />
    );
  }

  const selectedCandidate = selectedCandidateFor(detail.detail.candidates);
  const decisionSupportCandidates = detail.detail.decision_support?.candidates ?? [];
  return (
    <section className="grid min-w-0 gap-4">
      <section className="rounded-md border border-border/80 bg-card p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-base font-semibold tracking-normal">
              {detail.detail.search.objective}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Search {shortId(detail.detail.search.search_id)} · parent{" "}
              {shortId(detail.detail.search.parent_session_id)}
            </p>
          </div>
          <Badge variant={detail.detail.search.status === "completed" ? "success" : "info"}>
            {detail.detail.search.status}
          </Badge>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          Candidate selection records review metadata only. It does not merge files or mutate parent
          history.
        </p>
        {selectedCandidate !== null ? (
          <p className="mt-2 text-sm">
            Selected candidate:{" "}
            <span className="font-medium">{selectedCandidate.strategy_label}</span>
          </p>
        ) : null}
      </section>
      <CandidateTable
        action={action}
        candidates={detail.detail.candidates}
        decisionSupportCandidates={decisionSupportCandidates}
        onMarkCandidate={onMarkCandidate}
        searchId={detail.detail.search.search_id}
      />
      <CandidateEvidence
        candidates={detail.detail.candidates}
        decisionSupportCandidates={decisionSupportCandidates}
      />
    </section>
  );
}

function CandidateTable({
  action,
  candidates,
  decisionSupportCandidates,
  onMarkCandidate,
  searchId,
}: {
  action: BranchSearchActionStatus;
  candidates: Candidate[];
  decisionSupportCandidates: CandidateDecisionSupport[];
  onMarkCandidate?: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    searchId: string;
  }) => void;
  searchId: string;
}) {
  return (
    <section aria-label="Branch-search candidates" className="min-w-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Strategy</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Verification</TableHead>
            <TableHead>Decision</TableHead>
            <TableHead>Review</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {candidates.map((candidate) => {
            const support = decisionSupportFor(candidate, decisionSupportCandidates);
            return (
              <TableRow key={candidate.candidate_id}>
                <TableCell>
                  <span className="font-medium">{candidate.strategy_label}</span>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {candidate.patch_summary ?? "No structured patch summary retained."}
                  </p>
                </TableCell>
                <TableCell>
                  <Badge variant={candidateStatusVariant(candidate.status)}>
                    {candidate.selection_state ?? candidate.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={verificationVariant(candidate.verification_status)}>
                    {support?.verification_posture ?? candidate.verification_status}
                  </Badge>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {candidate.verification_summary ?? "No verification summary retained."}
                  </p>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {support != null ? (
                    <div className="grid gap-1">
                      <span>
                        Risk {support.risk_posture} · Cost {support.cost_estimate}
                      </span>
                      <span>{support.recommended_follow_up_action}</span>
                      <CandidateLinks candidate={candidate} />
                    </div>
                  ) : (
                    <CandidateLinks candidate={candidate} />
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <CandidateActionButton
                      action="select"
                      candidate={candidate}
                      disabled={action.state === "pending"}
                      icon={<ShieldCheck className={operatorIconSizeClass} aria-hidden="true" />}
                      label="Select"
                      onMarkCandidate={onMarkCandidate}
                      searchId={searchId}
                    />
                    <CandidateActionButton
                      action="needs-review"
                      candidate={candidate}
                      disabled={action.state === "pending"}
                      icon={<FileSearch className={operatorIconSizeClass} aria-hidden="true" />}
                      label="Review"
                      onMarkCandidate={onMarkCandidate}
                      searchId={searchId}
                    />
                    <CandidateActionButton
                      action="reject"
                      candidate={candidate}
                      disabled={action.state === "pending"}
                      icon={<XCircle className={operatorIconSizeClass} aria-hidden="true" />}
                      label="Reject"
                      onMarkCandidate={onMarkCandidate}
                      searchId={searchId}
                    />
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </section>
  );
}

function CandidateActionButton({
  action,
  candidate,
  disabled,
  icon,
  label,
  onMarkCandidate,
  searchId,
}: {
  action: "needs-review" | "reject" | "select";
  candidate: Candidate;
  disabled: boolean;
  icon: ReactNode;
  label: string;
  onMarkCandidate?: (input: {
    action: "needs-review" | "reject" | "select";
    candidateId: string;
    searchId: string;
  }) => void;
  searchId: string;
}) {
  return (
    <Button
      aria-label={`${label} ${candidate.strategy_label}`}
      disabled={disabled}
      onClick={() => onMarkCandidate?.({ action, candidateId: candidate.candidate_id, searchId })}
      size="sm"
      type="button"
      variant={action === "reject" ? "destructive" : action === "select" ? "secondary" : "outline"}
    >
      {icon}
      {label}
    </Button>
  );
}

function CandidateLinks({ candidate }: { candidate: Candidate }) {
  const links: ReactNode[] = [];
  if (candidate.candidate_session_id != null) {
    links.push(
      <a
        className="text-primary underline-offset-2 hover:underline"
        href={buildAppRoute({
          compareSessionId: null,
          queue: "all",
          selectedSessionId: candidate.candidate_session_id,
          selectedTaskId: null,
          surface: "sessions",
          tab: "overview",
          taskQueue: "active",
        })}
        key="session"
      >
        Session {shortId(candidate.candidate_session_id)}
      </a>,
    );
  }
  if (candidate.artifact_id != null) {
    links.push(<span key="artifact">Artifact {shortId(candidate.artifact_id)}</span>);
  }
  if (links.length === 0) {
    return <span>No linked session or artifact.</span>;
  }
  return <span className="flex flex-col gap-1">{links}</span>;
}

function CandidateEvidence({
  candidates,
  decisionSupportCandidates,
}: {
  candidates: Candidate[];
  decisionSupportCandidates: CandidateDecisionSupport[];
}) {
  return (
    <section className="grid gap-4 lg:grid-cols-3">
      {candidates.map((candidate) => {
        const support = decisionSupportFor(candidate, decisionSupportCandidates);
        return (
          <section
            className="rounded-md border border-border/80 bg-card p-4 shadow-sm"
            key={candidate.candidate_id}
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-semibold tracking-normal">{candidate.strategy_label}</h3>
              <Badge variant={verificationVariant(candidate.verification_status)}>
                {support?.verification_posture ?? candidate.verification_status}
              </Badge>
            </div>
            <DataList className="mt-3" density="compact">
              <DataListItem>
                <DataListLabel>Changed files</DataListLabel>
                <DataListMeta>
                  {support?.changed_files_summary ??
                    ((candidate.changed_files ?? []).length > 0
                      ? (candidate.changed_files ?? []).join(", ")
                      : "No structured changed-file summary retained.")}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Evidence</DataListLabel>
                <DataListMeta>
                  {support != null && (support.evidence ?? []).length > 0
                    ? (support.evidence ?? []).map((item) => item.summary).join("; ")
                    : "No retained decision evidence found."}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Posture</DataListLabel>
                <DataListMeta>
                  {support != null
                    ? `Risk ${support.risk_posture}; cost ${support.cost_estimate}.`
                    : "No decision posture available."}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Verification recommendation</DataListLabel>
                <DataListMeta>{verificationRecommendationSummary(support)}</DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Accepted risks</DataListLabel>
                <DataListMeta>
                  {support != null && (support.accepted_risks ?? []).length > 0
                    ? (support.accepted_risks ?? []).join("; ")
                    : "No accepted risks recorded."}
                </DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Follow-up</DataListLabel>
                <DataListMeta>
                  {support?.recommended_follow_up_action ?? "Inspect candidate evidence."}
                </DataListMeta>
              </DataListItem>
            </DataList>
          </section>
        );
      })}
    </section>
  );
}

function verificationRecommendationSummary(support: CandidateDecisionSupport | null): string {
  const recommendation = support?.verification_recommendations?.[0];
  if (recommendation == null) {
    return "Inspect candidate evidence before choosing verification.";
  }
  if ((recommendation.commands ?? []).length > 0) {
    return (recommendation.commands ?? []).join("; ");
  }
  return recommendation.rationale;
}

export function StateLine({
  icon,
  tone = "muted",
  value,
}: {
  icon?: ReactNode;
  tone?: "destructive" | "muted";
  value: string;
}) {
  const toneClass =
    tone === "destructive"
      ? "border-destructive/40 text-destructive"
      : "border-border/80 text-muted-foreground";
  return (
    <div className={`rounded-md border bg-card p-4 text-sm shadow-sm ${toneClass}`}>
      <span className="flex items-center gap-2">
        {icon ?? <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
        {value}
      </span>
    </div>
  );
}

function selectedCandidateFor(candidates: Candidate[]): Candidate | null {
  return candidates.find((candidate) => candidate.selection_state === "selected") ?? null;
}

function decisionSupportFor(
  candidate: Candidate,
  supportCandidates: CandidateDecisionSupport[],
): CandidateDecisionSupport | null {
  return (
    supportCandidates.find((support) => support.candidate_id === candidate.candidate_id) ?? null
  );
}

function candidateStatusVariant(status: string) {
  if (status === "selected" || status === "verified") {
    return "success" as const;
  }
  if (status === "rejected") {
    return "destructive" as const;
  }
  if (status === "needs_review" || status === "planned" || status === "forked") {
    return "warning" as const;
  }
  return "info" as const;
}

function verificationVariant(status: string) {
  if (status === "passed" || status === "strong") {
    return "success" as const;
  }
  if (status === "failed" || status === "timed_out" || status === "risky") {
    return "destructive" as const;
  }
  if (
    status === "blocked" ||
    status === "inconclusive" ||
    status === "not_run" ||
    status === "review"
  ) {
    return "warning" as const;
  }
  return "muted" as const;
}

function shortId(value: string): string {
  return value.length <= 10 ? value : `${value.slice(0, 8)}...`;
}
