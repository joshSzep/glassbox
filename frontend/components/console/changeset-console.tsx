"use client";

import {
  ChevronLeft,
  ClipboardCheck,
  FileText,
  GitBranch,
  MessageSquareText,
  PlusCircle,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type {
  ChangesetActionStatus,
  ChangesetDetailState,
  ChangesetPageState,
} from "@/stores/dashboard-stores";

export type ChangesetConsoleProps = {
  action?: ChangesetActionStatus;
  detail: ChangesetDetailState;
  onGenerateReviewBrief?: () => void;
  onAttachManualEvidence?: (input: {
    commandText?: string | null;
    evidenceKind?: "manual_command" | "external_check" | "operator_assertion" | "reviewer_note";
    freshness?: "current" | "needs_inspection" | "stale" | "unknown";
    note?: string | null;
    sourceLabel: string;
    summary: string;
  }) => void;
  onInspectFeedbackStatus?: () => void;
  onInspectHandoff?: () => void;
  onPreviewVerification?: () => void;
  onRefresh?: () => void;
  onRefreshChangeset?: () => void;
  onSelectChangeset?: (changesetId: string) => void;
  onShowList?: () => void;
  page: ChangesetPageState;
};

export function ChangesetConsole({
  action = { error: null, kind: null, state: "idle" },
  detail,
  onGenerateReviewBrief,
  onAttachManualEvidence,
  onInspectFeedbackStatus,
  onInspectHandoff,
  onPreviewVerification,
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
            onRefreshChangeset={onRefreshChangeset}
            onShowList={onShowList}
          />
        </section>
      </div>
    </main>
  );
}

function ChangesetList({
  detail,
  onSelectChangeset,
  page,
}: {
  detail: ChangesetDetailState;
  onSelectChangeset?: (changesetId: string) => void;
  page: ChangesetPageState;
}) {
  if (page.loadState === "failed") {
    return <StateLine tone="destructive" value={page.error ?? "Unable to load changesets."} />;
  }
  if (page.items.length === 0) {
    return <StateLine value="No changesets found." />;
  }
  return (
    <DataList density="compact">
      {page.items.map((changeset) => (
        <DataListItem
          className={
            changeset.changeset_id === detail.selectedChangesetId ? "bg-surface-raised" : ""
          }
          key={changeset.changeset_id}
        >
          <button
            className="grid min-w-0 gap-1 text-left"
            onClick={() => onSelectChangeset?.(changeset.changeset_id)}
            type="button"
          >
            <DataListLabel className="truncate">{changeset.objective}</DataListLabel>
            <DataListMeta className="truncate">
              {changeset.status} - risk {changeset.risk_level} - {changeset.changeset_id}
            </DataListMeta>
          </button>
        </DataListItem>
      ))}
    </DataList>
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
  const highRisk = changeset.risk_level === "high";
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            {changeset.status}
          </p>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{changeset.objective}</h2>
          <p className="mt-1 break-all text-console text-muted-foreground">
            {changeset.changeset_id}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={highRisk ? "warning" : "muted"}>Risk {changeset.risk_level}</Badge>
            <Badge variant={staleInventory ? "warning" : "muted"}>
              Inventory {inventoryStatus.freshness}
            </Badge>
            <Badge variant={verificationBadgeVariant(verificationState)}>
              Verification {formatVerificationState(verificationState)}
            </Badge>
            {changeset.unresolved_risk_count > 0 ? (
              <Badge variant="outline">{changeset.unresolved_risk_count} unresolved</Badge>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={onShowList} size="sm" type="button" variant="ghost">
            <ChevronLeft className={operatorIconSizeClass} aria-hidden="true" />
            List
          </Button>
          <Button
            disabled={action.state === "pending"}
            onClick={onGenerateReviewBrief}
            size="sm"
            type="button"
            variant={briefCount > 0 ? "outline" : "default"}
          >
            <FileText className={operatorIconSizeClass} aria-hidden="true" />
            Brief
          </Button>
          <Button
            disabled={action.state === "pending"}
            onClick={onRefreshChangeset}
            size="sm"
            type="button"
            variant="outline"
          >
            <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>
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
      <ReviewFeedbackPanel detail={detail.detail} />
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

function ReviewQuickActionsPanel({
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

function CandidateAdoptionPanel({ detail }: { detail: ChangesetDetailState }) {
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

function CommandEvidencePanel({ detail }: { detail: NonNullable<ChangesetDetailState["detail"]> }) {
  const evidence = detail.command_evidence;
  return (
    <Section title="Command Evidence">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={evidence.verification_count > 0 ? "success" : "muted"}>
            {evidence.verification_count} verification
          </Badge>
          <Badge variant={evidence.failed_count > 0 ? "warning" : "muted"}>
            {evidence.failed_count} failed
          </Badge>
          <Badge variant={evidence.risky_count > 0 ? "warning" : "muted"}>
            {evidence.risky_count} risky
          </Badge>
          <Badge variant="outline">{evidence.environment_captured_count} environment</Badge>
        </div>
        {evidence.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No retained command attempts are linked to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {evidence.items.slice(0, 6).map((item) => (
              <DataListItem key={item.tool_attempt_id}>
                <DataListLabel>
                  {item.purpose} - {item.status}
                </DataListLabel>
                <DataListMeta>{item.summary}</DataListMeta>
                <DataListMeta>
                  {item.tool_name} attempt {item.tool_attempt_id} - {item.review_relevance}
                  {item.output_artifact_id ? ` - artifact ${item.output_artifact_id}` : ""}
                </DataListMeta>
                {item.environment_captured ? (
                  <DataListMeta>
                    Environment captured with {item.toolchain_count} toolchain
                    {item.toolchain_count === 1 ? "" : "s"}
                  </DataListMeta>
                ) : null}
                {item.policy_summary ? <DataListMeta>{item.policy_summary}</DataListMeta> : null}
              </DataListItem>
            ))}
          </DataList>
        )}
        {evidence.safe_next_actions.length > 0 ? (
          <ul className="grid gap-2 text-console text-muted-foreground">
            {evidence.safe_next_actions.map((action) => (
              <li className="break-all" key={action}>
                {action}
              </li>
            ))}
          </ul>
        ) : null}
        {evidence.limitations.length > 0 ? (
          <p className="text-xs text-muted-foreground">{evidence.limitations.join("; ")}</p>
        ) : null}
      </div>
    </Section>
  );
}

function CommitPreparationPanel({ detail }: { detail: ChangesetDetailState }) {
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

function HandoffReadinessPanel({ detail }: { detail: ChangesetDetailState }) {
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

function ReviewPanel({
  briefCount,
  latestBriefId,
  readiness,
}: {
  briefCount: number;
  latestBriefId: string | null;
  readiness: NonNullable<ChangesetDetailState["detail"]>["readiness"][number] | undefined;
}) {
  const state = readiness?.state ?? "needs_review";
  const blockers = readiness?.blockers ?? [];
  return (
    <Section title="Review Readiness">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={readinessBadgeVariant(state)}>{state.replaceAll("_", " ")}</Badge>
          <Badge variant={briefCount > 0 ? "success" : "warning"}>{briefCount} brief</Badge>
          {latestBriefId ? <Badge variant="outline">Latest brief attached</Badge> : null}
        </div>
        <p className="text-sm text-muted-foreground">
          {readiness?.reason ??
            "Generate a brief after inventory and verification evidence settle."}
        </p>
        {latestBriefId ? (
          <p className="break-all text-console text-muted-foreground">{latestBriefId}</p>
        ) : null}
        {blockers.length > 0 ? (
          <DataList density="compact">
            {blockers.map((blocker) => (
              <DataListItem key={blocker}>
                <DataListLabel>Blocker</DataListLabel>
                <DataListMeta>{blocker}</DataListMeta>
              </DataListItem>
            ))}
          </DataList>
        ) : null}
      </div>
    </Section>
  );
}

function ReviewFeedbackPanel({ detail }: { detail: NonNullable<ChangesetDetailState["detail"]> }) {
  const feedback = detail.review_feedback;
  const responseSummary = detail.review_response_summary;
  const responseByFeedbackId = new Map(
    responseSummary.items.map((item) => [item.feedback_id, item]),
  );
  const openItems = feedback.filter(
    (item) => item.disposition === "open" || item.disposition === "in_progress",
  );
  const questions = feedback.filter((item) => item.feedback_kind === "reviewer_question");
  const requestedChanges = feedback.filter((item) => item.feedback_kind === "requested_change");
  const acceptedRisks = feedback.filter((item) => item.disposition === "accepted_with_risk");
  const resolved = feedback.filter((item) => item.disposition === "resolved_locally");
  return (
    <Section title="Review Feedback">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={openItems.length > 0 ? "warning" : "muted"}>
            {openItems.length} open
          </Badge>
          <Badge variant={requestedChanges.length > 0 ? "warning" : "muted"}>
            {requestedChanges.length} requested
          </Badge>
          <Badge variant={questions.length > 0 ? "info" : "muted"}>
            {questions.length} questions
          </Badge>
          <Badge variant={resolved.length > 0 ? "success" : "muted"}>
            {resolved.length} resolved locally
          </Badge>
          <Badge variant={acceptedRisks.length > 0 ? "outline" : "muted"}>
            {acceptedRisks.length} accepted risks
          </Badge>
          <Badge variant={responseSummary.responded_count > 0 ? "success" : "muted"}>
            {responseSummary.responded_count} responded
          </Badge>
          <Badge variant={responseSummary.stale_response_count > 0 ? "warning" : "muted"}>
            {responseSummary.stale_response_count} stale responses
          </Badge>
        </div>
        {feedback.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No local review feedback is attached to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {feedback.slice(0, 8).map((item) => {
              const response = responseByFeedbackId.get(item.feedback_id);
              return (
                <DataListItem key={item.feedback_id}>
                  <DataListLabel>{item.summary}</DataListLabel>
                  <DataListMeta>
                    {item.feedback_kind} - {item.disposition} - {item.provenance}
                    {item.reviewer_label ? ` - ${item.reviewer_label}` : ""}
                  </DataListMeta>
                  {response ? (
                    <>
                      <DataListMeta>
                        Response {response.response_state} - {response.fixup_inventory_count}{" "}
                        inventories - {response.changed_path_count} paths -{" "}
                        {response.matched_scope_path_count} scoped matches
                      </DataListMeta>
                      <DataListMeta>
                        Freshness {response.inventory_freshness}
                        {response.stale_reason ? ` - ${response.stale_reason}` : ""}
                      </DataListMeta>
                      <DataListMeta>
                        Verification {response.verification_state}
                        {response.verification_reason ? ` - ${response.verification_reason}` : ""}
                      </DataListMeta>
                      {response.verification_safe_next_actions.slice(0, 1).map((action) => (
                        <DataListMeta className="break-all" key={action}>
                          {action}
                        </DataListMeta>
                      ))}
                      {response.path_summaries.slice(0, 2).map((summary) => (
                        <DataListMeta key={summary}>{summary}</DataListMeta>
                      ))}
                      {response.blockers.slice(0, 2).map((blocker) => (
                        <DataListMeta key={blocker}>Blocker: {blocker}</DataListMeta>
                      ))}
                    </>
                  ) : null}
                  {item.resolution_summary ? (
                    <DataListMeta>Resolution: {item.resolution_summary}</DataListMeta>
                  ) : null}
                  {item.risk_summary ? (
                    <DataListMeta>Accepted risk: {item.risk_summary}</DataListMeta>
                  ) : null}
                  {item.residual_risk ? (
                    <DataListMeta>Residual risk: {item.residual_risk}</DataListMeta>
                  ) : null}
                </DataListItem>
              );
            })}
          </DataList>
        )}
        <ul className="grid gap-2 text-console text-muted-foreground">
          {responseSummary.safe_next_actions.map((action) => (
            <li className="break-all" key={action}>
              {action}
            </li>
          ))}
          <li className="break-all">
            glassbox changeset feedback list --changeset {detail.changeset.changeset_id} --cwd .
          </li>
          {responseSummary.non_claims.slice(0, 1).map((claim) => (
            <li key={claim}>{claim}</li>
          ))}
        </ul>
      </div>
    </Section>
  );
}

function ManualEvidencePanel({ detail }: { detail: NonNullable<ChangesetDetailState["detail"]> }) {
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
        </div>
        {evidence.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No manual evidence is attached to this changeset.
          </p>
        ) : (
          <DataList density="compact">
            {evidence.slice(0, 8).map((item) => (
              <DataListItem key={item.evidence_id}>
                <DataListLabel>{item.summary}</DataListLabel>
                <DataListMeta>
                  {item.evidence_kind} - {item.state} - {item.redaction_status} - {item.freshness}
                </DataListMeta>
                <DataListMeta>
                  Target {item.target_kind} {item.target_id} - source {item.source_label}
                </DataListMeta>
                {item.artifact_id ? <DataListMeta>Artifact {item.artifact_id}</DataListMeta> : null}
                {item.evidence_kind === "browser_observation" ||
                item.evidence_kind === "screenshot" ? (
                  <DataListMeta>
                    Live evidence is advisory and local-only - inspect target {item.target_kind}{" "}
                    {item.target_id}
                  </DataListMeta>
                ) : null}
                {item.evidence_kind === "accessibility_note" ? (
                  <DataListMeta>
                    Accessibility observation is advisory - inspect target {item.target_kind}{" "}
                    {item.target_id}
                  </DataListMeta>
                ) : null}
                {item.rejected_reason ? (
                  <DataListMeta>Rejected: {item.rejected_reason}</DataListMeta>
                ) : null}
                {item.limitations.slice(0, 2).map((limitation) => (
                  <DataListMeta key={limitation}>Limitation: {limitation}</DataListMeta>
                ))}
              </DataListItem>
            ))}
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
          <li>manual evidence is not retained command evidence or review approval</li>
          <li>browser and dashboard evidence is advisory, local-only, and not release authority</li>
          <li>accessibility evidence is advisory and not certification or WCAG conformance</li>
        </ul>
      </div>
    </Section>
  );
}

function InventoryPanel({ detail }: { detail: NonNullable<ChangesetDetailState["detail"]> }) {
  const inventory = detail.inventory;
  if (inventory == null) {
    return (
      <Section title="Changed Files">
        <p className="text-sm text-muted-foreground">No structured inventory is attached yet.</p>
      </Section>
    );
  }
  return (
    <Section title="Changed Files">
      <DataList density="compact">
        <DataListItem>
          <DataListLabel>{inventory.changed_path_count} changed paths</DataListLabel>
          <DataListMeta>
            Risk {inventory.risk_level} - {inventory.unresolved_risk_count} unresolved -{" "}
            {inventory.accepted_risk_count} accepted
          </DataListMeta>
        </DataListItem>
        <DataListItem>
          <DataListLabel>{inventory.artifact_id}</DataListLabel>
          <DataListMeta>
            Inventory artifact - freshness {detail.inventory_status.freshness} - sequence{" "}
            {inventory.last_sequence}
          </DataListMeta>
        </DataListItem>
      </DataList>
    </Section>
  );
}

function TopologyPanel({
  verificationPlan,
}: {
  verificationPlan: ChangesetDetailState["verificationPlan"];
}) {
  const impacts = verificationPlan?.topology_impacts ?? [];
  if (impacts.length === 0) {
    return null;
  }
  return (
    <Section title="Affected Subsystems">
      <DataList density="compact">
        {impacts.slice(0, 6).map((impact) => (
          <DataListItem key={impact.component_id}>
            <DataListLabel>
              {impact.name} - {impact.kind}
            </DataListLabel>
            <DataListMeta>
              {impact.root_path} - topology {impact.topology_freshness} -{" "}
              {impact.recommendation_posture}
            </DataListMeta>
            {impact.test_roots.length > 0 ? (
              <DataListMeta>Tests: {impact.test_roots.join(", ")}</DataListMeta>
            ) : null}
            {impact.ownership_hints.length > 0 ? (
              <DataListMeta>Owners: {impact.ownership_hints.join(", ")}</DataListMeta>
            ) : null}
            {impact.dependency_hints.length > 0 ? (
              <DataListMeta>
                Dependencies: {impact.dependency_hints.slice(0, 4).join("; ")}
              </DataListMeta>
            ) : null}
            {impact.limitations.length > 0 ? (
              <DataListMeta>{impact.limitations.join("; ")}</DataListMeta>
            ) : null}
          </DataListItem>
        ))}
      </DataList>
    </Section>
  );
}

function VerificationPanel({
  posture,
  verificationPlan,
}: {
  posture: NonNullable<ChangesetDetailState["detail"]>["verification_posture"];
  verificationPlan: ChangesetDetailState["verificationPlan"];
}) {
  if (verificationPlan === null) {
    return (
      <Section title="Verification">
        <p className="text-sm text-muted-foreground">
          {posture == null
            ? "No verification posture is attached yet."
            : `${posture.state} - ${posture.summary}`}
        </p>
      </Section>
    );
  }
  const readiness = verificationPlan.readiness;
  const reviewLoop = verificationPlan.review_loop_summary;
  const visibleRequirements = readiness.requirements.slice(0, 6);
  return (
    <Section title="Verification">
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={verificationBadgeVariant(readiness.state)}>
            {formatVerificationState(readiness.state)}
          </Badge>
          {readiness.failed_count > 0 ? (
            <Badge variant="destructive">{readiness.failed_count} failed</Badge>
          ) : null}
          {readiness.stale_count > 0 ? (
            <Badge variant="warning">{readiness.stale_count} stale</Badge>
          ) : null}
          {readiness.missing_count > 0 ? (
            <Badge variant="warning">{readiness.missing_count} missing</Badge>
          ) : null}
          {readiness.accepted_risk_count > 0 ? (
            <Badge variant="outline">{readiness.accepted_risk_count} accepted risk</Badge>
          ) : null}
          <Badge variant={reviewLoop.feedback_count > 0 ? "info" : "muted"}>
            {reviewLoop.feedback_count} feedback
          </Badge>
          <Badge variant={reviewLoop.manual_evidence_count > 0 ? "outline" : "muted"}>
            {reviewLoop.manual_evidence_count} manual evidence
          </Badge>
          <Badge variant={reviewLoop.stale_response_count > 0 ? "warning" : "muted"}>
            {reviewLoop.stale_response_count} stale responses
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{readiness.summary}</p>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>Review-loop context</DataListLabel>
            <DataListMeta>
              {reviewLoop.open_feedback_count} open feedback -{" "}
              {reviewLoop.missing_response_verification_count} missing response checks -{" "}
              {reviewLoop.accepted_risk_response_count} accepted with risk
            </DataListMeta>
            <DataListMeta>
              {reviewLoop.browser_evidence_count} browser/dashboard -{" "}
              {reviewLoop.accessibility_evidence_count} accessibility -{" "}
              {reviewLoop.topology_impact_count} topology impacts
            </DataListMeta>
          </DataListItem>
        </DataList>
        {visibleRequirements.length > 0 ? (
          <DataList density="compact">
            {visibleRequirements.map((requirement) => (
              <DataListItem key={requirement.requirement_id}>
                <DataListLabel>{requirement.check_name}</DataListLabel>
                <DataListMeta>
                  {formatVerificationState(requirement.state)} - {requirement.reason}
                </DataListMeta>
                {requirement.evidence_summary ? (
                  <DataListMeta>{requirement.evidence_summary}</DataListMeta>
                ) : null}
              </DataListItem>
            ))}
          </DataList>
        ) : null}
        {verificationPlan.safe_next_actions.length > 0 ? (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              Safe next actions
            </h4>
            <ul className="mt-2 grid gap-2 text-console text-muted-foreground">
              {verificationPlan.safe_next_actions.map((action) => (
                <li className="break-all" key={action}>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {verificationPlan.retained_artifact_ids.length > 0 ? (
          <p className="break-all text-console text-muted-foreground">
            Artifacts: {verificationPlan.retained_artifact_ids.join(", ")}
          </p>
        ) : null}
      </div>
    </Section>
  );
}

function verificationBadgeVariant(
  state: string,
): "destructive" | "muted" | "outline" | "success" | "warning" {
  if (state === "failed") {
    return "destructive";
  }
  if (state === "passed" || state === "not_applicable") {
    return "success";
  }
  if (state === "stale" || state === "missing") {
    return "warning";
  }
  if (state === "accepted_with_risk" || state === "skipped") {
    return "outline";
  }
  return "muted";
}

function readinessBadgeVariant(
  state: string,
): "destructive" | "muted" | "outline" | "success" | "warning" {
  if (state === "ready") {
    return "success";
  }
  if (state === "failed_checks" || state === "not_ready") {
    return "destructive";
  }
  if (state === "accepted_with_risk") {
    return "outline";
  }
  if (state === "needs_verification" || state === "stale_inventory") {
    return "warning";
  }
  return "muted";
}

function handoffBadgeVariant(
  state: string,
): "destructive" | "muted" | "outline" | "success" | "warning" {
  if (state === "handoff_ready" || state === "commit_prep_ready") {
    return "success";
  }
  if (state === "accepted_with_risk") {
    return "outline";
  }
  if (state === "publication_blocked") {
    return "destructive";
  }
  if (
    state === "needs_review_response" ||
    state === "needs_verification" ||
    state === "stale_inventory" ||
    state === "unresolved_risk"
  ) {
    return "warning";
  }
  return "muted";
}

function candidateBadgeVariant(
  state: string | null | undefined,
): "destructive" | "info" | "muted" | "outline" | "success" | "warning" {
  if (state === "selected" || state === "verified" || state === "completed") {
    return "success";
  }
  if (state === "rejected") {
    return "destructive";
  }
  if (state === "needs_review" || state === "planned" || state === "forked") {
    return "warning";
  }
  if (state === null || state === undefined) {
    return "muted";
  }
  return "info";
}

function formatVerificationState(state: string): string {
  return state.replaceAll("_", " ");
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 bg-surface px-3 py-2">
      <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 truncate text-console">{value}</dd>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="mt-4">
      <h3 className="text-sm font-semibold tracking-normal">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function StateLine({ tone = "muted", value }: { tone?: "destructive" | "muted"; value: string }) {
  return (
    <div
      className={
        tone === "destructive"
          ? "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {value}
    </div>
  );
}
