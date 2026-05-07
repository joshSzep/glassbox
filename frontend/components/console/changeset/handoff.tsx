import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { ChangesetDetailState } from "@/stores/dashboard-stores";

import { candidateBadgeVariant, handoffBadgeVariant, verificationBadgeVariant } from "./format";
import { Section } from "./shared";

export function HandoffReadinessPanel({ detail }: { detail: ChangesetDetailState }) {
  const readiness = detail.handoffReadiness;
  if (readiness === null) {
    return (
      <Section title="Final Handoff">
        <p className="text-sm text-muted-foreground">Handoff readiness is not loaded yet.</p>
      </Section>
    );
  }
  const blockingSignals = readiness.signals.filter((signal) => signal.blocking);
  return (
    <Section title="Final Handoff">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={handoffBadgeVariant(readiness.state)}>
            {readiness.state.replaceAll("_", " ")}
          </Badge>
          <Badge variant="outline">Commit {readiness.commit_readiness_state}</Badge>
          <Badge variant={readiness.evidence.unresolved_feedback_count > 0 ? "warning" : "muted"}>
            {readiness.evidence.unresolved_feedback_count} unresolved feedback
          </Badge>
          <Badge variant={readiness.evidence.accepted_risk_count > 0 ? "outline" : "muted"}>
            {readiness.evidence.accepted_risk_count} accepted risk
          </Badge>
          <Badge variant={readiness.evidence.local_only_evidence_count > 0 ? "info" : "muted"}>
            {readiness.evidence.local_only_evidence_count} local-only evidence
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{readiness.reason}</p>
        {blockingSignals.length > 0 ? (
          <DataList density="compact">
            {blockingSignals.slice(0, 5).map((signal) => (
              <DataListItem key={`${signal.signal_id}-${signal.summary}`}>
                <DataListLabel>{signal.signal_id.replaceAll("-", " ")}</DataListLabel>
                <DataListMeta>{signal.summary}</DataListMeta>
                {signal.paths.slice(0, 2).map((path) => (
                  <DataListMeta className="break-all" key={path}>
                    {path}
                  </DataListMeta>
                ))}
              </DataListItem>
            ))}
          </DataList>
        ) : null}
        {readiness.limitations.length > 0 ? (
          <DataList density="compact">
            {readiness.limitations.slice(0, 4).map((limitation) => (
              <DataListItem key={limitation}>
                <DataListLabel>Limitation</DataListLabel>
                <DataListMeta>{limitation}</DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        ) : null}
        <ul className="grid gap-2 text-console text-muted-foreground">
          {readiness.safe_next_actions.slice(0, 6).map((action) => (
            <li className="break-all" key={action}>
              {action}
            </li>
          ))}
          {readiness.non_claims.slice(0, 1).map((claim) => (
            <li key={claim}>{claim}</li>
          ))}
        </ul>
      </div>
    </Section>
  );
}

export function CandidateAdoptionPanel({ detail }: { detail: ChangesetDetailState }) {
  const changesetDetail = detail.detail;
  if (changesetDetail === null) {
    return null;
  }
  const { changeset } = changesetDetail;
  const branchSearchId = changeset.branch_search_id;
  const candidateId = changeset.branch_candidate_id;
  if (branchSearchId === null && candidateId === null) {
    return null;
  }
  const branchDetail = detail.branchSearchDetail;
  const adoptionSource =
    changesetDetail.sources.find((source) => source.source_kind === "branch_search_candidate") ??
    null;
  const supportCandidates = branchDetail?.decision_support.candidates ?? [];
  const candidateRows = branchDetail?.candidates ?? [];
  const adoptedSupport =
    supportCandidates.find((candidate) => candidate.candidate_id === candidateId) ?? null;
  const adoptedCandidate =
    candidateRows.find((candidate) => candidate.candidate_id === candidateId) ?? null;
  const alternatives = supportCandidates.filter(
    (candidate) => candidate.candidate_id !== candidateId,
  );
  const selectedLabel =
    adoptedSupport?.strategy_label ??
    adoptedCandidate?.strategy_label ??
    candidateId ??
    "Candidate pending";
  const sourceReason =
    adoptionSource?.reason ?? "Branch-search candidate adoption source evidence is attached.";
  const mutationClaim = "Glassbox did not merge, rebase, stage, commit, push, or open a PR.";

  return (
    <Section title="Candidate Adoption">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="info">
            <GitBranch className={operatorIconSizeClass} aria-hidden="true" />
            {selectedLabel}
          </Badge>
          <Badge
            variant={candidateBadgeVariant(adoptedSupport?.status ?? adoptedCandidate?.status)}
          >
            {adoptedSupport?.selection_state ?? adoptedCandidate?.selection_state ?? "adopted"}
          </Badge>
          {adoptedSupport ? (
            <>
              <Badge variant={verificationBadgeVariant(adoptedSupport.verification_posture)}>
                Verification {adoptedSupport.verification_posture}
              </Badge>
              <Badge variant="outline">Risk {adoptedSupport.risk_posture}</Badge>
            </>
          ) : null}
        </div>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>{candidateId ?? "Candidate pending"}</DataListLabel>
            <DataListMeta>
              Search {branchSearchId ?? "unknown"} - {sourceReason}
            </DataListMeta>
            {adoptionSource?.limitation ? (
              <DataListMeta>{adoptionSource.limitation}</DataListMeta>
            ) : null}
          </DataListItem>
          <DataListItem>
            <DataListLabel>Workspace mutation performed: false</DataListLabel>
            <DataListMeta>{mutationClaim}</DataListMeta>
            <DataListMeta>
              Candidate adoption records review provenance and comparison context only.
            </DataListMeta>
          </DataListItem>
          {adoptedSupport ? (
            <DataListItem>
              <DataListLabel>{adoptedSupport.changed_files_summary}</DataListLabel>
              <DataListMeta>Follow-up: {adoptedSupport.recommended_follow_up_action}</DataListMeta>
              {adoptedSupport.accepted_risks?.length ? (
                <DataListMeta>
                  Accepted risks: {adoptedSupport.accepted_risks.join("; ")}
                </DataListMeta>
              ) : null}
            </DataListItem>
          ) : null}
        </DataList>
        {branchDetail === null && branchSearchId !== null ? (
          <p className="text-console text-muted-foreground">
            Branch-search comparison details are not loaded. Inspect retained evidence with glassbox
            branch-search show {branchSearchId} --cwd .
          </p>
        ) : null}
        {alternatives.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Rejected Alternatives
            </h4>
            <DataList className="mt-2" density="compact">
              {alternatives.map((candidate) => (
                <DataListItem key={candidate.candidate_id}>
                  <DataListLabel>{candidate.strategy_label}</DataListLabel>
                  <DataListMeta>
                    {candidate.selection_state ?? candidate.status} - verification{" "}
                    {candidate.verification_posture} - risk {candidate.risk_posture}
                  </DataListMeta>
                  <DataListMeta>Follow-up: {candidate.recommended_follow_up_action}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
          </div>
        ) : null}
        <p className="text-xs text-muted-foreground">{mutationClaim}</p>
      </div>
    </Section>
  );
}
