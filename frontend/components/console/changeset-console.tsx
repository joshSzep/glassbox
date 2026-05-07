"use client";

import { RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { ChangesetActionStatus, ChangesetDetailState } from "@/stores/dashboard-stores";
import { CommitPreparationPanel } from "./changeset/commit-prep";
import { ChangesetDetailHeader } from "./changeset/detail";
import { ManualEvidencePanel, ReviewQuickActionsPanel } from "./changeset/evidence";
import { ReviewFeedbackPanel, ReviewPanel } from "./changeset/feedback";
import { CandidateAdoptionPanel, HandoffReadinessPanel } from "./changeset/handoff";
import { ChangesetList } from "./changeset/list";
import { Fact, Section, StateLine } from "./changeset/shared";
import type { ChangesetConsoleProps } from "./changeset/types";
import {
  CommandEvidencePanel,
  InventoryPanel,
  TopologyPanel,
  VerificationPanel,
} from "./changeset/verification";

export type { ChangesetConsoleProps } from "./changeset/types";

export function ChangesetConsole({
  action = { error: null, kind: null, state: "idle" },
  detail,
  onGenerateReviewBrief,
  onAttachManualEvidence,
  onInspectFeedbackStatus,
  onInspectHandoff,
  onPreviewVerification,
  onRecordFeedbackFixup,
  onRefresh,
  onRefreshChangeset,
  onSelectChangeset,
  onShowList,
  page,
}: ChangesetConsoleProps) {
  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5">
        <section
          aria-label="Changeset console status"
          className="grid gap-3 rounded-md border border-border/80 bg-card p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Review Console
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-normal">Changesets</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {page.items.length} local changeset{page.items.length === 1 ? "" : "s"} available for
              basic inspection.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info">Evidence object</Badge>
            <Button onClick={onRefresh} size="sm" type="button" variant="outline">
              <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </section>
        {action.state === "failed" && action.error !== null ? (
          <StateLine tone="destructive" value={action.error} />
        ) : null}
        <section className="grid gap-4 xl:grid-cols-[22rem_1fr]">
          <ChangesetList detail={detail} onSelectChangeset={onSelectChangeset} page={page} />
          <ChangesetDetail
            action={action}
            detail={detail}
            onAttachManualEvidence={onAttachManualEvidence}
            onGenerateReviewBrief={onGenerateReviewBrief}
            onInspectFeedbackStatus={onInspectFeedbackStatus}
            onInspectHandoff={onInspectHandoff}
            onPreviewVerification={onPreviewVerification}
            onRecordFeedbackFixup={onRecordFeedbackFixup}
            onRefreshChangeset={onRefreshChangeset}
            onShowList={onShowList}
          />
        </section>
      </div>
    </main>
  );
}

function ChangesetDetail({
  action,
  detail,
  onAttachManualEvidence,
  onGenerateReviewBrief,
  onInspectFeedbackStatus,
  onInspectHandoff,
  onPreviewVerification,
  onRecordFeedbackFixup,
  onRefreshChangeset,
  onShowList,
}: {
  action: ChangesetActionStatus;
  detail: ChangesetDetailState;
  onAttachManualEvidence?: ChangesetConsoleProps["onAttachManualEvidence"];
  onGenerateReviewBrief?: () => void;
  onInspectFeedbackStatus?: () => void;
  onInspectHandoff?: () => void;
  onPreviewVerification?: () => void;
  onRecordFeedbackFixup?: ChangesetConsoleProps["onRecordFeedbackFixup"];
  onRefreshChangeset?: () => void;
  onShowList?: () => void;
}) {
  if (detail.loadState === "idle") {
    return <StateLine value="Select a changeset to inspect its source evidence." />;
  }
  if (detail.loadState === "failed") {
    return <StateLine tone="destructive" value={detail.error ?? "Unable to load changeset."} />;
  }
  if (detail.detail === null) {
    return <StateLine value="Loading changeset evidence." />;
  }
  const { changeset } = detail.detail;
  const inventoryStatus = detail.detail.inventory_status;
  const staleInventory = inventoryStatus.stale || inventoryStatus.freshness === "stale";
  const verificationPlan = detail.verificationPlan;
  const verificationState = verificationPlan?.readiness.state ?? "missing";
  const reviewReadiness = detail.detail.readiness.find(
    (readiness) => readiness.readiness_kind === "review",
  );
  const branchCandidate = changeset.branch_search_id ?? changeset.branch_candidate_id;
  const briefCount = detail.detail.review_briefs.length;
  return (
    <article className="rounded-md border border-border/80 bg-card p-4 shadow-sm">
      <ChangesetDetailHeader
        action={action}
        briefCount={briefCount}
        changeset={changeset}
        inventoryStatus={inventoryStatus}
        onGenerateReviewBrief={onGenerateReviewBrief}
        onRefreshChangeset={onRefreshChangeset}
        onShowList={onShowList}
        verificationState={verificationState}
      />
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Fact label="Session" value={changeset.session_id} />
        <Fact label="Task" value={changeset.task_id ?? "None"} />
        <Fact label="Branch search" value={changeset.branch_search_id ?? "None"} />
        <Fact label="Inventory" value={inventoryStatus.freshness} />
        <Fact
          label="Verification"
          value={
            verificationPlan === null
              ? (detail.detail.verification_posture?.state ?? "missing")
              : verificationPlan.readiness.state
          }
        />
        <Fact label="Risk" value={changeset.risk_summary ?? changeset.risk_level} />
      </dl>
      {inventoryStatus.reason ? (
        <StateLine tone={staleInventory ? "destructive" : "muted"} value={inventoryStatus.reason} />
      ) : null}
      {detail.lastActionMessage ? <StateLine value={detail.lastActionMessage} /> : null}
      <ReviewQuickActionsPanel
        action={action}
        onAttachManualEvidence={onAttachManualEvidence}
        onGenerateReviewBrief={onGenerateReviewBrief}
        onInspectFeedbackStatus={onInspectFeedbackStatus}
        onInspectHandoff={onInspectHandoff}
        onPreviewVerification={onPreviewVerification}
        onRefreshChangeset={onRefreshChangeset}
      />
      <ReviewPanel
        briefCount={briefCount}
        latestBriefId={changeset.latest_review_brief_artifact_id ?? null}
        readiness={reviewReadiness}
      />
      <ReviewFeedbackPanel
        action={action}
        detail={detail.detail}
        onRecordFeedbackFixup={onRecordFeedbackFixup}
      />
      <ManualEvidencePanel detail={detail.detail} />
      <InventoryPanel detail={detail.detail} />
      <TopologyPanel verificationPlan={verificationPlan} />
      <VerificationPanel
        posture={detail.detail.verification_posture}
        verificationPlan={verificationPlan}
      />
      <CommandEvidencePanel detail={detail.detail} />
      <HandoffReadinessPanel detail={detail} />
      <CommitPreparationPanel detail={detail} />
      {branchCandidate ? <CandidateAdoptionPanel detail={detail} /> : null}
      <Section title="Brief Artifacts">
        {detail.detail.review_briefs.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No reviewer-safe brief artifact is attached yet.
          </p>
        ) : (
          <DataList density="compact">
            {detail.detail.review_briefs.map((brief) => (
              <DataListItem key={brief.artifact_id}>
                <DataListLabel className="break-all">{brief.artifact_id}</DataListLabel>
                <DataListMeta>
                  {brief.render_targets.join(", ")} - local only {String(brief.local_only)} -
                  sequence {brief.last_sequence}
                </DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        )}
      </Section>
      <Section title="Sources">
        {detail.detail.sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">No source records attached.</p>
        ) : (
          <DataList density="compact">
            {detail.detail.sources.map((source) => (
              <DataListItem key={`${source.source_kind}-${source.last_sequence}`}>
                <DataListLabel>{source.source_kind}</DataListLabel>
                <DataListMeta>{source.reason}</DataListMeta>
                {source.limitation ? <DataListMeta>{source.limitation}</DataListMeta> : null}
              </DataListItem>
            ))}
          </DataList>
        )}
      </Section>
      <Section title="Safe Next Actions">
        <ul className="grid gap-2 text-console text-muted-foreground">
          {detail.detail.safe_next_actions.map((item) => (
            <li className="break-all" key={item}>
              {item}
            </li>
          ))}
        </ul>
      </Section>
      {detail.detail.limitations.length > 0 ? (
        <Section title="Limitations">
          <ul className="grid gap-2 text-sm text-muted-foreground">
            {detail.detail.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}
    </article>
  );
}
