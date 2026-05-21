import {
  Archive,
  CheckCircle2,
  FileSearch,
  PackageCheck,
  RefreshCcw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import type { ReactNode } from "react";

import type { HandoffIntent } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type {
  HandoffActionStatus,
  HandoffDetailState,
  HandoffDraftState,
  HandoffPageState,
} from "@/stores/dashboard-stores";

type HandoffCockpitProps = {
  action: HandoffActionStatus;
  detail: HandoffDetailState;
  drafts: HandoffDraftState;
  list: HandoffPageState;
  onAccept?: () => void;
  onArchive?: () => void;
  onExport?: () => void;
  onImport?: () => void;
  onInspect?: () => void;
  onLoadGuidance?: () => void;
  onLoadList?: () => void;
  onPreview?: () => void;
  onReadiness?: () => void;
  onReject?: () => void;
  onSelectHandoff?: (record: HandoffPageState["items"][number]) => void;
  onSetDraft?: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => void;
  onTriage?: () => void;
};

const intents: HandoffIntent[] = [
  "review-only",
  "continue-work",
  "verification-needed",
  "failure-triage",
  "release-signoff",
  "future-self",
  "fork-recommended",
];

const sourceKinds: HandoffDraftState["sourceKind"][] = [
  "session",
  "task",
  "changeset",
  "workspace",
  "release",
];

export function HandoffCockpit({
  action,
  detail,
  drafts,
  list,
  onAccept,
  onArchive,
  onExport,
  onImport,
  onInspect,
  onLoadGuidance,
  onLoadList,
  onPreview,
  onReadiness,
  onReject,
  onSelectHandoff,
  onSetDraft,
  onTriage,
}: HandoffCockpitProps) {
  const selectedRecord = detail.selected?.record ?? null;
  const triage = detail.triage?.triage ?? detail.inspect?.triage ?? null;
  const canImport = triage?.can_import_for_inspection === true && action.state !== "pending";
  const hasSelectedRecord = selectedRecord !== null;

  return (
    <main className="min-h-screen bg-surface-subtle px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-[1440px] gap-5">
        <header className="rounded-md border border-border/80 bg-card p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
                Local Handoff
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal">Handoff Cockpit</h1>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Prepare, inspect, triage, and record custody decisions from the same typed handoff
                API used by the CLI.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={list.items.length > 0 ? "warning" : "muted"}>
                {list.items.length} records
              </Badge>
              <Badge variant={action.state === "failed" ? "destructive" : "outline"}>
                {action.kind === null ? "idle" : `${action.kind} ${action.state}`}
              </Badge>
            </div>
          </div>
          {action.error !== null ? (
            <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {action.error}
            </div>
          ) : null}
        </header>

        <section className="grid gap-4 xl:grid-cols-[minmax(20rem,0.75fr)_minmax(0,1fr)]">
          <aside className="grid content-start gap-4">
            <CockpitPanel title="Handoff Records">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  Projected handoff rows remain local workflow evidence.
                </p>
                <Button onClick={onLoadList} size="sm" type="button" variant="outline">
                  <RefreshCcw className={operatorIconSizeClass} aria-hidden="true" />
                  Refresh
                </Button>
              </div>
              {list.error !== null ? (
                <StateLine tone="destructive">{list.error}</StateLine>
              ) : list.loadState === "loading" ? (
                <StateLine>Loading handoff records.</StateLine>
              ) : list.items.length === 0 ? (
                <StateLine>No handoff records are projected yet.</StateLine>
              ) : (
                <DataList density="compact">
                  {list.items.map((item) => (
                    <button
                      className={`grid min-h-density-row gap-1 px-3 py-2 text-left transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        selectedRecord?.package_id === item.record.package_id
                          ? "bg-accent text-accent-foreground"
                          : ""
                      }`}
                      key={`${item.record.session_id}-${item.record.package_id}`}
                      onClick={() => onSelectHandoff?.(item)}
                      type="button"
                    >
                      <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                        {item.record.package_id}
                        <Badge variant={custodyVariant(item.record.custody_state)}>
                          {item.record.custody_state}
                        </Badge>
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {item.record.source_kind} {item.record.source_id ?? item.record.session_id}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {item.record.intent ?? "intent unknown"} - {item.action_state}
                      </span>
                    </button>
                  ))}
                </DataList>
              )}
            </CockpitPanel>

            <CockpitPanel title="Custody Actions">
              {selectedRecord === null ? (
                <StateLine>
                  Select a handoff record to accept, reject, archive, or load guidance.
                </StateLine>
              ) : (
                <div className="grid gap-3">
                  <RecordSummary record={detail.selected} />
                  <Field label="Actor">
                    <Input
                      onChange={(event) => onSetDraft?.("decisionActor", event.target.value)}
                      value={drafts.decisionActor}
                    />
                  </Field>
                  <Field label="Decision reason">
                    <Textarea
                      className="min-h-20"
                      onChange={(event) => onSetDraft?.("decisionReason", event.target.value)}
                      value={drafts.decisionReason}
                    />
                  </Field>
                  <Field label="Follow-up intent">
                    <Select
                      onChange={(value) => onSetDraft?.("followUpIntent", value as HandoffIntent)}
                      options={intents}
                      value={drafts.followUpIntent}
                    />
                  </Field>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={!hasSelectedRecord}
                      onClick={onLoadGuidance}
                      variant="outline"
                    >
                      <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
                      Guidance
                    </Button>
                    <Button disabled={!hasSelectedRecord} onClick={onAccept}>
                      <CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />
                      Accept
                    </Button>
                    <Button disabled={!hasSelectedRecord} onClick={onReject} variant="outline">
                      <XCircle className={operatorIconSizeClass} aria-hidden="true" />
                      Reject
                    </Button>
                    <Button disabled={!hasSelectedRecord} onClick={onArchive} variant="outline">
                      <Archive className={operatorIconSizeClass} aria-hidden="true" />
                      Archive
                    </Button>
                  </div>
                </div>
              )}
            </CockpitPanel>
          </aside>

          <section className="grid min-w-0 gap-4">
            <CockpitPanel title="Prepare Handoff">
              <div className="grid gap-3 lg:grid-cols-2">
                <Field label="Source kind">
                  <Select
                    onChange={(value) =>
                      onSetDraft?.("sourceKind", value as HandoffDraftState["sourceKind"])
                    }
                    options={sourceKinds}
                    value={drafts.sourceKind}
                  />
                </Field>
                <Field label="Source id">
                  <Input
                    disabled={drafts.sourceKind === "workspace" || drafts.sourceKind === "release"}
                    onChange={(event) => onSetDraft?.("sourceId", event.target.value)}
                    placeholder="session, task, or changeset id"
                    value={drafts.sourceId}
                  />
                </Field>
                <Field label="Recipient intent">
                  <Select
                    onChange={(value) => onSetDraft?.("intent", value as HandoffIntent)}
                    options={intents}
                    value={drafts.intent}
                  />
                </Field>
                <Field label="Recipient">
                  <Input
                    onChange={(event) => onSetDraft?.("recipient", event.target.value)}
                    value={drafts.recipient}
                  />
                </Field>
                <Field label="Expected custodian">
                  <Input
                    onChange={(event) => onSetDraft?.("expectedCustodian", event.target.value)}
                    value={drafts.expectedCustodian}
                  />
                </Field>
                <Field label="Exported by">
                  <Input
                    onChange={(event) => onSetDraft?.("exportedBy", event.target.value)}
                    value={drafts.exportedBy}
                  />
                </Field>
                <Field label="Output path">
                  <Input
                    onChange={(event) => onSetDraft?.("outputPath", event.target.value)}
                    placeholder="handoff.json"
                    value={drafts.outputPath}
                  />
                </Field>
                <Field label="Markdown path">
                  <Input
                    onChange={(event) => onSetDraft?.("markdownOutputPath", event.target.value)}
                    placeholder="optional"
                    value={drafts.markdownOutputPath}
                  />
                </Field>
              </div>
              <Field className="mt-3" label="Note">
                <Textarea
                  className="min-h-20"
                  onChange={(event) => onSetDraft?.("note", event.target.value)}
                  value={drafts.note}
                />
              </Field>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={onReadiness} type="button" variant="outline">
                  <ShieldAlert className={operatorIconSizeClass} aria-hidden="true" />
                  Readiness
                </Button>
                <Button onClick={onPreview} type="button" variant="outline">
                  <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
                  Preview
                </Button>
                <Button onClick={onExport} type="button">
                  <PackageCheck className={operatorIconSizeClass} aria-hidden="true" />
                  Export
                </Button>
              </div>
            </CockpitPanel>

            <CockpitPanel title="Package Inspection">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
                <Field label="Package path">
                  <Input
                    onChange={(event) => onSetDraft?.("packagePath", event.target.value)}
                    placeholder="handoff.json"
                    value={drafts.packagePath}
                  />
                </Field>
                <div className="flex items-end gap-2">
                  <Button onClick={onInspect} type="button" variant="outline">
                    Inspect
                  </Button>
                  <Button onClick={onTriage} type="button" variant="outline">
                    Triage
                  </Button>
                  <Button disabled={!canImport} onClick={onImport} type="button">
                    Import
                  </Button>
                </div>
              </div>
            </CockpitPanel>

            <ReadinessPanel readiness={detail.readiness} />
            <PreviewPanel preview={detail.preview} />
            <PackagePanel detail={detail} />
          </section>
        </section>
      </div>
    </main>
  );
}

function CockpitPanel({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm">
      <h2 className="text-sm font-semibold tracking-normal">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Field({
  children,
  className,
  label,
}: {
  children: ReactNode;
  className?: string;
  label: string;
}) {
  return (
    <label className={`grid gap-1 ${className ?? ""}`}>
      <span className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

function Select<T extends string>({
  onChange,
  options,
  value,
}: {
  onChange: (value: T) => void;
  options: T[];
  value: T;
}) {
  return (
    <select
      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onChange={(event) => onChange(event.target.value as T)}
      value={value}
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

function StateLine({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "destructive" | "muted";
}) {
  return (
    <p
      className={
        tone === "destructive"
          ? "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "rounded-md border border-border/80 bg-surface px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {children}
    </p>
  );
}

function ReadinessPanel({ readiness }: { readiness: HandoffDetailState["readiness"] }) {
  if (readiness === null) {
    return null;
  }
  const model = readiness.readiness;
  return (
    <CockpitPanel title="Readiness Summary">
      <div className="grid gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge variant={readinessVariant(model.state)}>{model.state}</Badge>
          <Badge variant="outline">{model.intent}</Badge>
          <Badge variant="muted">{model.freshness}</Badge>
          <Badge variant="muted">{model.confidence}</Badge>
        </div>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>{model.source.label ?? model.source.kind}</DataListLabel>
            <DataListMeta>
              {model.source.kind} {model.source.primary_id ?? "workspace"}
            </DataListMeta>
          </DataListItem>
          {model.reasons?.slice(0, 5).map((reason) => (
            <DataListItem key={`${reason.kind}-${reason.summary}`}>
              <DataListLabel>{reason.kind}</DataListLabel>
              <DataListMeta>{reason.summary}</DataListMeta>
              {reason.limitation ? <DataListMeta>{reason.limitation}</DataListMeta> : null}
            </DataListItem>
          ))}
        </DataList>
        <CommandList commands={model.safe_first_commands ?? []} />
        <NonClaims claims={model.non_claims ?? []} />
      </div>
    </CockpitPanel>
  );
}

function PreviewPanel({ preview }: { preview: HandoffDetailState["preview"] }) {
  if (preview === null) {
    return null;
  }
  const model = preview.preview;
  return (
    <CockpitPanel title="Redaction Preview And Local-Only Inventory">
      <div className="grid gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge variant={redactionVariant(model.redaction.posture)}>
            {model.redaction.posture}
          </Badge>
          <Badge variant={model.local_only_evidence_count > 0 ? "warning" : "muted"}>
            {model.local_only_evidence_count} local-only
          </Badge>
          <Badge variant="outline">{model.intent}</Badge>
        </div>
        <DataList density="compact">
          <DataListItem>
            <DataListLabel>Included sections</DataListLabel>
            <DataListMeta>{(model.included_sections ?? []).join(", ") || "none"}</DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Redacted categories</DataListLabel>
            <DataListMeta>
              {(model.redaction.redacted_categories ?? []).join(", ") || "none"}
            </DataListMeta>
          </DataListItem>
          <DataListItem>
            <DataListLabel>Omitted raw categories</DataListLabel>
            <DataListMeta>{(model.omitted_raw_categories ?? []).join(", ") || "none"}</DataListMeta>
          </DataListItem>
          {model.local_only_inventory.items?.slice(0, 5).map((item) => (
            <DataListItem key={`${item.category}-${item.summary}`}>
              <DataListLabel>{item.category}</DataListLabel>
              <DataListMeta>{item.summary}</DataListMeta>
              <DataListMeta>{item.recipient_limitation}</DataListMeta>
            </DataListItem>
          ))}
        </DataList>
        <CommandList commands={model.safe_inspection_commands ?? []} />
      </div>
    </CockpitPanel>
  );
}

function PackagePanel({ detail }: { detail: HandoffDetailState }) {
  const triage = detail.triage?.triage ?? detail.inspect?.triage ?? null;
  const changesetSummary = detail.inspect?.changeset_summary ?? null;
  const guidance = detail.guidance?.guidance ?? null;

  if (
    triage === null &&
    changesetSummary === null &&
    guidance === null &&
    detail.exported === null &&
    detail.importResult === null
  ) {
    return null;
  }

  return (
    <CockpitPanel title="Package, Triage, And Follow-Up">
      <div className="grid gap-3">
        {detail.exported !== null ? (
          <StateLine>
            Exported {detail.exported.source_kind} handoff to {detail.exported.output_path}.
          </StateLine>
        ) : null}
        {detail.importResult !== null ? (
          <StateLine>Imported package for inspection-only local state.</StateLine>
        ) : null}
        {changesetSummary !== null ? (
          <DataList density="compact">
            <DataListItem>
              <DataListLabel>Changeset package</DataListLabel>
              <DataListMeta>
                {changesetSummary.changeset_id} - {changesetSummary.status}
              </DataListMeta>
            </DataListItem>
            <DataListItem>
              <DataListLabel>Evidence</DataListLabel>
              <DataListMeta>
                {changesetSummary.evidence_graph_node_count} nodes,{" "}
                {changesetSummary.local_only_evidence_count} local-only
              </DataListMeta>
            </DataListItem>
          </DataList>
        ) : null}
        {triage !== null ? (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant={compatibilityVariant(triage.compatibility.state)}>
                {triage.compatibility.state}
              </Badge>
              <Badge variant={triage.can_import_for_inspection ? "success" : "warning"}>
                {triage.recommended_disposition}
              </Badge>
              <Badge variant={triage.mutation_performed ? "destructive" : "muted"}>
                mutation {triage.mutation_performed ? "recorded" : "none"}
              </Badge>
            </div>
            <DataList density="compact">
              <DataListItem>
                <DataListLabel>{triage.package_id}</DataListLabel>
                <DataListMeta>{triage.package_path}</DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Included evidence</DataListLabel>
                <DataListMeta>{(triage.included_evidence ?? []).join(", ") || "none"}</DataListMeta>
              </DataListItem>
              <DataListItem>
                <DataListLabel>Local-only omissions</DataListLabel>
                <DataListMeta>
                  {(triage.local_only_omissions ?? []).join(", ") || "none"}
                </DataListMeta>
              </DataListItem>
            </DataList>
            <CommandList commands={triage.safe_first_commands ?? []} />
          </>
        ) : null}
        {guidance !== null ? (
          <>
            <DataList density="compact">
              <DataListItem>
                <DataListLabel>{guidance.state}</DataListLabel>
                <DataListMeta>{guidance.summary}</DataListMeta>
              </DataListItem>
              {guidance.paths?.map((path) => (
                <DataListItem key={path.path_id}>
                  <DataListLabel>
                    {path.title} {path.recommended ? "(recommended)" : ""}
                  </DataListLabel>
                  <DataListMeta>{path.summary}</DataListMeta>
                </DataListItem>
              ))}
              {guidance.blockers?.map((blocker) => (
                <DataListItem key={`${blocker.kind}-${blocker.summary}`}>
                  <DataListLabel>{blocker.kind}</DataListLabel>
                  <DataListMeta>{blocker.summary}</DataListMeta>
                </DataListItem>
              ))}
            </DataList>
            <CommandList commands={guidance.safe_commands ?? []} />
            <NonClaims claims={guidance.non_claims ?? []} />
          </>
        ) : null}
      </div>
    </CockpitPanel>
  );
}

function RecordSummary({ record }: { record: HandoffDetailState["selected"] }) {
  if (record === null) {
    return null;
  }
  return (
    <DataList density="compact">
      <DataListItem>
        <DataListLabel>{record.record.package_id}</DataListLabel>
        <DataListMeta>
          {record.record.custody_state} - {record.action_state}
        </DataListMeta>
      </DataListItem>
      <DataListItem>
        <DataListLabel>Safe next actions</DataListLabel>
        <DataListMeta>
          {(record.record.safe_next_actions ?? []).join("; ") || "none recorded"}
        </DataListMeta>
      </DataListItem>
    </DataList>
  );
}

function CommandList({
  commands,
}: {
  commands: { display: string; purpose: string; read_only: boolean }[];
}) {
  if (commands.length === 0) {
    return null;
  }
  return (
    <DataList density="compact">
      {commands.slice(0, 6).map((command) => (
        <DataListItem key={command.display}>
          <DataListLabel className="break-all">{command.display}</DataListLabel>
          <DataListMeta>
            {command.purpose} {command.read_only ? "(read-only)" : "(explicit mutation)"}
          </DataListMeta>
        </DataListItem>
      ))}
    </DataList>
  );
}

function NonClaims({ claims }: { claims: string[] }) {
  if (claims.length === 0) {
    return null;
  }
  return (
    <ul className="grid gap-1 text-console text-muted-foreground">
      {claims.slice(0, 4).map((claim) => (
        <li key={claim}>{claim}</li>
      ))}
    </ul>
  );
}

function custodyVariant(state: string) {
  if (state === "accepted" || state === "accepted-for-follow-up") {
    return "success" as const;
  }
  if (state === "rejected") {
    return "destructive" as const;
  }
  if (state === "archived") {
    return "muted" as const;
  }
  return "info" as const;
}

function readinessVariant(state: string) {
  if (state === "ready") {
    return "success" as const;
  }
  if (state === "blocked" || state === "failed-needs-triage") {
    return "destructive" as const;
  }
  if (state === "needs-verification" || state === "local-only-evidence") {
    return "warning" as const;
  }
  return "info" as const;
}

function redactionVariant(state: string) {
  if (state === "reviewer-safe" || state === "redacted") {
    return "success" as const;
  }
  if (state === "raw-included") {
    return "destructive" as const;
  }
  if (state === "local-only-omitted") {
    return "warning" as const;
  }
  return "muted" as const;
}

function compatibilityVariant(state: string) {
  if (state === "supported") {
    return "success" as const;
  }
  if (state === "supported-with-warnings" || state === "legacy-inspection-only") {
    return "warning" as const;
  }
  if (state === "unsupported" || state === "invalid" || state === "future-version") {
    return "destructive" as const;
  }
  return "muted" as const;
}
