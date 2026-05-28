import { Archive, CheckCircle2, FileSearch, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { operatorIconSizeClass } from "@/design-system/operator-status";
import type { HandoffDetailState, HandoffDraftState } from "@/stores/dashboard-stores";

import { handoffIntentOptions } from "./options";
import { CockpitPanel, Field, Select, StateLine } from "./shared";

export function CustodyActionsPanel({
  drafts,
  onAccept,
  onArchive,
  onLoadGuidance,
  onReject,
  onSetDraft,
  selected,
}: {
  drafts: HandoffDraftState;
  onAccept?: () => void;
  onArchive?: () => void;
  onLoadGuidance?: () => void;
  onReject?: () => void;
  onSetDraft?: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => void;
  selected: HandoffDetailState["selected"];
}) {
  const hasSelectedRecord = selected !== null;

  return (
    <CockpitPanel title="Custody Actions">
      {selected === null ? (
        <StateLine>Select a handoff record to accept, reject, archive, or load guidance.</StateLine>
      ) : (
        <div className="grid gap-3">
          <RecordSummary record={selected} />
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
              onChange={(value) =>
                onSetDraft?.("followUpIntent", value as HandoffDraftState["followUpIntent"])
              }
              options={handoffIntentOptions}
              value={drafts.followUpIntent}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button disabled={!hasSelectedRecord} onClick={onLoadGuidance} variant="outline">
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
