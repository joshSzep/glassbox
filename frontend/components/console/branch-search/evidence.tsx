"use client";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";

import {
  decisionSupportFor,
  verificationRecommendationSummary,
  verificationVariant,
} from "./format";
import type { Candidate, CandidateDecisionSupport } from "./types";

export function CandidateEvidence({
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
