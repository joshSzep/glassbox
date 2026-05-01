"use client";

import { FileSearch, GitBranch, Loader2, ShieldCheck, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { BranchSearchActionStatus, BranchSearchDetailState } from "@/stores/dashboard-stores";

import { CandidateActionButton, CandidateLinks } from "./actions";
import { CandidateEvidence } from "./evidence";
import {
  candidateStatusVariant,
  decisionSupportFor,
  selectedCandidateFor,
  shortId,
  verificationVariant,
} from "./format";
import { StateLine } from "./shared";
import type { Candidate, CandidateDecisionSupport, MarkCandidateInput } from "./types";

export function BranchSearchDetail({
  action,
  detail,
  onMarkCandidate,
}: {
  action: BranchSearchActionStatus;
  detail: BranchSearchDetailState;
  onMarkCandidate?: (input: MarkCandidateInput) => void;
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
  onMarkCandidate?: (input: MarkCandidateInput) => void;
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
