import { TerminalSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { EmptyLine, Pane } from "@/components/console/session-inspector/frame";
import type { DashboardState } from "@/state/session-state";

export function RuntimePane({ data }: { data: DashboardState }) {
  const context = data.runtimeContext;
  const workingSet = context?.working_set?.items ?? [];
  const notes = context?.runtime_notes ?? [];
  const artifacts = context?.artifact_context?.summaries ?? [];
  const memory = context?.workspace_memory ?? [];
  const repositoryIndex = context?.repository_index ?? null;
  const repositoryIndexItems = repositoryIndex?.items ?? [];

  if (context === null) {
    return (
      <Pane icon={TerminalSquare} title="Runtime context">
        <EmptyLine value="Runtime context is unavailable for this snapshot." />
      </Pane>
    );
  }

  return (
    <Pane icon={TerminalSquare} title="Runtime context">
      <div className="space-y-4">
        <section className="rounded-md border bg-card p-3">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold tracking-normal">
              {context.repository_context.workspace_name}
            </h4>
            <Badge variant="outline">Repository</Badge>
          </div>
          <RuntimeTextList
            empty="No high-signal paths"
            label="High-signal paths"
            values={context.repository_context.high_signal_paths ?? []}
          />
          <RuntimeTextList
            empty="No project markers"
            label="Project markers"
            values={context.repository_context.project_markers ?? []}
          />
          <RuntimeTextList
            empty="No top-level entries"
            label="Top-level entries"
            values={[
              ...(context.repository_context.top_level_directories ?? []),
              ...(context.repository_context.top_level_files ?? []),
            ]}
          />
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Workspace memory influence
          </p>
          {memory.length === 0 ? (
            <EmptyLine value="No workspace memory items influenced this runtime context." />
          ) : (
            <DataList density="compact">
              {memory.map((item) => (
                <DataListItem key={item.memory_id}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.summary}</DataListLabel>
                      <DataListMeta>{item.content}</DataListMeta>
                    </div>
                    <Badge variant={item.redacted ? "warning" : "success"}>{item.kind}</Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.provenance.source_type}
                    {item.provenance.session_id
                      ? ` ${item.provenance.session_id}#${item.provenance.source_sequence ?? 0}`
                      : ""}
                    {" · "}
                    {item.use_count} use{item.use_count === 1 ? "" : "s"}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Repository index influence
          </p>
          {repositoryIndex === null ? (
            <EmptyLine value="Repository index context was not available for this snapshot." />
          ) : repositoryIndexItems.length === 0 ? (
            <EmptyLine
              value={
                repositoryIndex.detail ??
                "No repository index items were selected for this runtime context."
              }
            />
          ) : (
            <DataList density="compact">
              {repositoryIndexItems.map((item) => (
                <DataListItem key={item.entry_id}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.name}</DataListLabel>
                      <DataListMeta>{item.summary ?? item.path ?? item.symbol}</DataListMeta>
                    </div>
                    <Badge variant="outline">{item.kind}</Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.source_type ?? "source"} · {item.path ?? item.symbol ?? item.entry_id}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
          {repositoryIndex !== null ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {repositoryIndex.status} · {repositoryIndex.entry_count} indexed entries ·{" "}
              {repositoryIndex.context_bytes} context bytes
            </p>
          ) : null}
        </section>
        <section>
          <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Working set
          </p>
          {workingSet.length === 0 ? (
            <EmptyLine value="No working-set items are retained in this snapshot." />
          ) : (
            <DataList density="compact">
              {workingSet.map((item) => (
                <DataListItem key={`${item.subject_kind}:${item.subject}`}>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <DataListLabel>{item.subject}</DataListLabel>
                      <DataListMeta>{item.summary}</DataListMeta>
                    </div>
                    <Badge variant={item.inherited ? "info" : "success"}>
                      {item.inherited ? "inherited" : "current"}
                    </Badge>
                  </div>
                  <p className="mt-2 break-all text-xs text-muted-foreground">
                    {item.signal_types?.join(", ") || "unknown signal"} ·{" "}
                    {item.reasons?.join(", ") || "no recorded reason"}
                  </p>
                </DataListItem>
              ))}
            </DataList>
          )}
        </section>
        <RuntimeNotes notes={notes} />
        <ArtifactProvenance artifacts={artifacts} />
      </div>
    </Pane>
  );
}

function RuntimeTextList({
  empty,
  label,
  values,
}: {
  empty: string;
  label: string;
  values: string[];
}) {
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 break-all text-sm text-muted-foreground">
        {values.length > 0 ? values.join(", ") : empty}
      </p>
    </div>
  );
}

function RuntimeNotes({
  notes,
}: {
  notes: NonNullable<NonNullable<DashboardState["runtimeContext"]>["runtime_notes"]>;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Runtime notes
      </p>
      {notes.length === 0 ? (
        <EmptyLine value="No runtime notes are retained in this snapshot." />
      ) : (
        <DataList density="compact">
          {notes.map((note, index) => (
            <DataListItem key={`${note.category}:${index}`}>
              <div className="flex flex-wrap items-center gap-2">
                <DataListLabel>{note.category}</DataListLabel>
                <Badge variant={note.inherited ? "info" : "outline"}>
                  {note.inherited ? "inherited" : "current"}
                </Badge>
              </div>
              <DataListMeta>{note.message}</DataListMeta>
              {note.source_session_id !== undefined && note.source_session_id !== null ? (
                <p className="mt-2 break-all text-xs text-muted-foreground">
                  source {note.source_session_id}
                </p>
              ) : null}
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  );
}

function ArtifactProvenance({
  artifacts,
}: {
  artifacts: NonNullable<
    NonNullable<NonNullable<DashboardState["runtimeContext"]>["artifact_context"]>["summaries"]
  >;
}) {
  return (
    <section>
      <p className="mb-2 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        Artifact provenance
      </p>
      {artifacts.length === 0 ? (
        <EmptyLine value="No artifact provenance is attached to this runtime context." />
      ) : (
        <DataList density="compact">
          {artifacts.map((artifact) => (
            <DataListItem key={`${artifact.artifact_kind}:${artifact.artifact_path}`}>
              <DataListLabel>{artifact.summary_kind}</DataListLabel>
              <DataListMeta>{artifact.summary}</DataListMeta>
              <p className="mt-2 break-all text-xs text-muted-foreground">
                {artifact.source_tool_name} · {artifact.provenance_class} · {artifact.freshness} ·{" "}
                {artifact.artifact_path}
              </p>
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  );
}
