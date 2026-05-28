import { FileSearch, PackageCheck, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { HandoffDraftState } from "@/stores/dashboard-stores";

import { handoffIntentOptions, handoffSourceKindOptions } from "./options";
import { CockpitPanel, Field, Select } from "./shared";

export function PreparePanel({
  drafts,
  onExport,
  onPreview,
  onReadiness,
  onSetDraft,
}: {
  drafts: HandoffDraftState;
  onExport?: () => void;
  onPreview?: () => void;
  onReadiness?: () => void;
  onSetDraft?: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => void;
}) {
  return (
    <CockpitPanel title="Prepare Handoff">
      <div className="grid gap-3 lg:grid-cols-2">
        <Field label="Source kind">
          <Select
            onChange={(value) =>
              onSetDraft?.("sourceKind", value as HandoffDraftState["sourceKind"])
            }
            options={handoffSourceKindOptions}
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
            onChange={(value) => onSetDraft?.("intent", value as HandoffDraftState["intent"])}
            options={handoffIntentOptions}
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
  );
}
