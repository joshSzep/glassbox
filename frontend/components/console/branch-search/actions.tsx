"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { buildAppRoute } from "@/routing/app-route";

import { shortId } from "./format";
import type { Candidate, MarkCandidateInput } from "./types";

export function CandidateActionButton({
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
  onMarkCandidate?: (input: MarkCandidateInput) => void;
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

export function CandidateLinks({ candidate }: { candidate: Candidate }) {
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
