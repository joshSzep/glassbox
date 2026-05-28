import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Input } from "@/components/ui/input";
import type {
  HandoffActionStatus,
  HandoffDetailState,
  HandoffDraftState,
} from "@/stores/dashboard-stores";

import {
  CockpitPanel,
  CommandList,
  Field,
  NonClaims,
  StateLine,
  compatibilityVariant,
} from "./shared";

export function PackageInspectionPanel({
  action,
  detail,
  drafts,
  onImport,
  onInspect,
  onSetDraft,
  onTriage,
}: {
  action: HandoffActionStatus;
  detail: HandoffDetailState;
  drafts: HandoffDraftState;
  onImport?: () => void;
  onInspect?: () => void;
  onSetDraft?: <K extends keyof HandoffDraftState>(key: K, value: HandoffDraftState[K]) => void;
  onTriage?: () => void;
}) {
  const triage = detail.triage?.triage ?? detail.inspect?.triage ?? null;
  const canImport = triage?.can_import_for_inspection === true && action.state !== "pending";

  return (
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
  );
}

export function PackagePanel({ detail }: { detail: HandoffDetailState }) {
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
