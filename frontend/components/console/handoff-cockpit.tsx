import { Badge } from "@/components/ui/badge";
import { CustodyActionsPanel } from "@/components/console/handoff/custody-actions";
import { PackageInspectionPanel, PackagePanel } from "@/components/console/handoff/package-panel";
import { PreparePanel } from "@/components/console/handoff/prepare-panel";
import { PreviewPanel } from "@/components/console/handoff/preview-panel";
import { ReadinessPanel } from "@/components/console/handoff/readiness-panel";
import { HandoffRecordsPanel } from "@/components/console/handoff/records-panel";
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
            <HandoffRecordsPanel
              list={list}
              onLoadList={onLoadList}
              onSelectHandoff={onSelectHandoff}
              selected={detail.selected}
            />
            <CustodyActionsPanel
              drafts={drafts}
              onAccept={onAccept}
              onArchive={onArchive}
              onLoadGuidance={onLoadGuidance}
              onReject={onReject}
              onSetDraft={onSetDraft}
              selected={detail.selected}
            />
          </aside>

          <section className="grid min-w-0 gap-4">
            <PreparePanel
              drafts={drafts}
              onExport={onExport}
              onPreview={onPreview}
              onReadiness={onReadiness}
              onSetDraft={onSetDraft}
            />
            <PackageInspectionPanel
              action={action}
              detail={detail}
              drafts={drafts}
              onImport={onImport}
              onInspect={onInspect}
              onSetDraft={onSetDraft}
              onTriage={onTriage}
            />
            <ReadinessPanel readiness={detail.readiness} />
            <PreviewPanel preview={detail.preview} />
            <PackagePanel detail={detail} />
          </section>
        </section>
      </div>
    </main>
  );
}
