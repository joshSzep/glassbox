"use client";

import {
  ClipboardCheck,
  FileText,
  MessageSquareText,
  PlusCircle,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { ChangesetActionStatus, ChangesetDetailState } from "@/stores/dashboard-stores";

import { Section } from "./shared";
import type { ChangesetConsoleProps } from "./types";

type ChangesetDetailRecord = NonNullable<ChangesetDetailState["detail"]>;
type ManualEvidenceItem = ChangesetDetailRecord["manual_evidence"][number];

export function ReviewQuickActionsPanel({
  action,
  onAttachManualEvidence,
  onGenerateReviewBrief,
  onInspectFeedbackStatus,
  onInspectHandoff,
  onPreviewVerification,
  onRefreshChangeset,
}: {
  action: ChangesetActionStatus;
  onAttachManualEvidence?: ChangesetConsoleProps["onAttachManualEvidence"];
  onGenerateReviewBrief?: () => void;
  onInspectFeedbackStatus?: () => void;
  onInspectHandoff?: () => void;
  onPreviewVerification?: () => void;
  onRefreshChangeset?: () => void;
}) {
  const [summary, setSummary] = useState("");
  const [sourceLabel, setSourceLabel] = useState("operator note");
  const [note, setNote] = useState("");
  const actionPending = action.state === "pending";
  const canAttach =
    onAttachManualEvidence !== undefined &&
    summary.trim().length > 0 &&
    sourceLabel.trim().length > 0;
  return (
    <Section title="Review Quick Actions">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            disabled={actionPending || onRefreshChangeset === undefined}
            onClick={onRefreshChangeset}
            size="sm"
            type="button"
            variant="outline"
          >
            <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
            Refresh Inventory
          </Button>
          <Button
            disabled={actionPending || onPreviewVerification === undefined}
            onClick={onPreviewVerification}
            size="sm"
            type="button"
            variant="outline"
          >
            <ClipboardCheck className={operatorIconSizeClass} aria-hidden="true" />
            Preview Verification
          </Button>
          <Button
            disabled={actionPending || onInspectFeedbackStatus === undefined}
            onClick={onInspectFeedbackStatus}
            size="sm"
            type="button"
            variant="outline"
          >
            <MessageSquareText className={operatorIconSizeClass} aria-hidden="true" />
            Feedback Status
          </Button>
          <Button
            disabled={actionPending || onGenerateReviewBrief === undefined}
            onClick={onGenerateReviewBrief}
            size="sm"
            type="button"
            variant="outline"
          >
            <FileText className={operatorIconSizeClass} aria-hidden="true" />
            Generate Lifecycle
          </Button>
          <Button
            disabled={actionPending || onInspectHandoff === undefined}
            onClick={onInspectHandoff}
            size="sm"
            type="button"
            variant="outline"
          >
            <ShieldCheck className={operatorIconSizeClass} aria-hidden="true" />
            Handoff Posture
          </Button>
        </div>
        <form
          className="grid gap-2 rounded-md border border-border/70 bg-surface p-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!canAttach || actionPending) {
              return;
            }
            onAttachManualEvidence?.({
              evidenceKind: "operator_assertion",
              freshness: "needs_inspection",
              note: note.trim() || null,
              sourceLabel: sourceLabel.trim(),
              summary: summary.trim(),
            });
            setSummary("");
            setNote("");
          }}
        >
          <div className="grid gap-2 md:grid-cols-[1fr_14rem_auto]">
            <Input
              aria-label="Manual evidence summary"
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Manual evidence summary"
              value={summary}
            />
            <Input
              aria-label="Manual evidence source label"
              onChange={(event) => setSourceLabel(event.target.value)}
              placeholder="Source label"
              value={sourceLabel}
            />
            <Button disabled={!canAttach || actionPending} size="sm" type="submit">
              <PlusCircle className={operatorIconSizeClass} aria-hidden="true" />
              Attach
            </Button>
          </div>
          <Textarea
            aria-label="Manual evidence note"
            className="min-h-20"
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note. Manual evidence stays local-only and does not become retained command proof."
            value={note}
          />
          <p className="text-xs text-muted-foreground">
            Actions inspect state or record explicit local evidence only. Glassbox does not run
            checks, stage, commit, push, open PRs, merge, deploy, or publish from this panel.
          </p>
        </form>
      </div>
    </Section>
  );
}

export function ManualEvidencePanel({ detail }: { detail: ChangesetDetailRecord }) {
  const evidence = detail.manual_evidence;
  const attached = evidence.filter((item) => item.state === "attached");
  const rejected = evidence.filter((item) => item.state === "rejected");
  const stale = evidence.filter((item) => item.freshness === "stale");
  const liveEvidence = evidence.filter(
    (item) => item.evidence_kind === "browser_observation" || item.evidence_kind === "screenshot",
  );
  const accessibilityEvidence = evidence.filter(
    (item) => item.evidence_kind === "accessibility_note",
  );
  const skippedLiveEvidence = evidence.filter((item) => skippedEvidenceState(item) !== null);
  return (
    <Section title="Manual Evidence Inbox">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={attached.length > 0 ? "info" : "muted"}>{attached.length} attached</Badge>
          <Badge variant={rejected.length > 0 ? "warning" : "muted"}>
            {rejected.length} rejected
          </Badge>
          <Badge variant={stale.length > 0 ? "warning" : "muted"}>{stale.length} stale</Badge>
          <Badge variant={liveEvidence.length > 0 ? "info" : "muted"}>
            {liveEvidence.length} live
          </Badge>
          <Badge variant={accessibilityEvidence.length > 0 ? "warning" : "muted"}>
            {accessibilityEvidence.length} accessibility
          </Badge>
          <Badge variant={skippedLiveEvidence.length > 0 ? "warning" : "muted"}>
            {skippedLiveEvidence.length} skipped live
          </Badge>
        </div>
        {evidence.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No manual evidence is attached to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {evidence.slice(0, 8).map((item) => {
              const skippedState = skippedEvidenceState(item);
              const skipReason = skippedEvidenceReason(item);
              return (
                <DataListItem id={evidenceRowId(item.evidence_id)} key={item.evidence_id}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <DataListLabel>{item.summary}</DataListLabel>
                    <div className="flex flex-wrap items-center gap-2">
                      {skippedState ? (
                        <Badge variant="warning">{skippedState.replaceAll("_", " ")}</Badge>
                      ) : null}
                      <Button asChild size="sm" variant="ghost">
                        <a href={`#${evidenceRowId(item.evidence_id)}`}>Link</a>
                      </Button>
                    </div>
                  </div>
                  <DataListMeta>
                    {item.evidence_kind} - {item.state} - {item.redaction_status} - {item.freshness}
                  </DataListMeta>
                  <DataListMeta>
                    Target {item.target_kind} {item.target_id} - source {item.source_label}
                  </DataListMeta>
                  {item.artifact_id ? (
                    <DataListMeta>Artifact {item.artifact_id}</DataListMeta>
                  ) : null}
                  {skippedState ? (
                    <DataListMeta>
                      Skipped live evidence remains a limitation, not a pass
                      {skipReason ? ` - ${skipReason}` : ""}
                    </DataListMeta>
                  ) : null}
                  {item.evidence_kind === "browser_observation" ||
                  item.evidence_kind === "screenshot" ? (
                    <DataListMeta>
                      Browser/dashboard evidence is advisory and local-only, including skipped cases
                      - inspect target {item.target_kind} {item.target_id}
                    </DataListMeta>
                  ) : null}
                  {item.evidence_kind === "accessibility_note" ? (
                    <DataListMeta>
                      Accessibility evidence is advisory, not certification - inspect target{" "}
                      {item.target_kind} {item.target_id}
                    </DataListMeta>
                  ) : null}
                  {item.rejected_reason ? (
                    <DataListMeta>Rejected: {item.rejected_reason}</DataListMeta>
                  ) : null}
                  {item.limitations.slice(0, 2).map((limitation) => (
                    <DataListMeta key={limitation}>Limitation: {limitation}</DataListMeta>
                  ))}
                </DataListItem>
              );
            })}
          </DataList>
        )}
        <ul className="grid gap-2 text-console text-muted-foreground">
          <li className="break-all">
            glassbox changeset evidence list --changeset {detail.changeset.changeset_id} --cwd .
          </li>
          <li className="break-all">
            glassbox changeset evidence browser {detail.changeset.changeset_id} --route ROUTE
            --environment local --viewport WIDTHxHEIGHT --cwd .
          </li>
          <li className="break-all">
            glassbox changeset evidence dashboard {detail.changeset.changeset_id} --capture-state
            not_run --skip-reason REASON --cwd .
          </li>
          <li>manual evidence is not retained command evidence or review approval</li>
          <li>
            skipped browser or dashboard evidence is not a pass, verification, or release authority
          </li>
          <li>accessibility evidence is advisory and not certification or WCAG conformance</li>
        </ul>
      </div>
    </Section>
  );
}

function skippedEvidenceState(item: ManualEvidenceItem): string | null {
  const captureState = item.limitations
    .find((limitation) => limitation.toLowerCase().startsWith("capture state: "))
    ?.split(": ", 2)[1];
  if (captureState === "not_run" || captureState === "not_applicable") {
    return captureState;
  }
  return null;
}

function skippedEvidenceReason(item: ManualEvidenceItem): string | null {
  return (
    item.limitations
      .find((limitation) => limitation.toLowerCase().startsWith("skip reason: "))
      ?.split(": ", 2)[1] ?? null
  );
}

function evidenceRowId(evidenceId: string) {
  return `evidence-${evidenceId}`;
}
