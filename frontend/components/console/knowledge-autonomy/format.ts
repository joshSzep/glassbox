import type { MemoryEntry, MemoryInspectorState, RepositoryInspectorState } from "./types";

export function memorySummary(memory: MemoryInspectorState): string {
  return `${memory.items.length} ${memory.filter} workspace memory entries with provenance, freshness, and usage evidence.`;
}

export function repositorySummary(
  repository: RepositoryInspectorState,
  anchorSessionId: string | null,
) {
  const anchor =
    anchorSessionId === null ? "no session anchor" : `session ${shortId(anchorSessionId)}`;
  return `${repository.status?.entry_count ?? 0} indexed entities; ${anchor} for background rebuilds.`;
}

export function memorySourceLabel(entry: MemoryEntry): string {
  const source = entry.provenance;
  const sourceType = source.source_type ?? "source";
  if (source.source_label != null) {
    return source.source_label;
  }
  if (source.session_id != null) {
    return `${sourceType} ${shortId(source.session_id)}#${source.source_sequence ?? 0}`;
  }
  if (source.artifact_id != null) {
    return `${sourceType} ${shortId(source.artifact_id)}`;
  }
  return sourceType;
}

export function memoryStateVariant(state: string) {
  if (state === "active") {
    return "success" as const;
  }
  if (state === "stale" || state === "imported") {
    return "warning" as const;
  }
  if (state === "invalidated" || state === "pruned") {
    return "destructive" as const;
  }
  return "muted" as const;
}

export function repositoryStatusVariant(status: string | undefined) {
  if (status === "fresh") {
    return "success" as const;
  }
  if (status === "missing" || status === "stale" || status === "building") {
    return "warning" as const;
  }
  if (status === "failed") {
    return "destructive" as const;
  }
  return "muted" as const;
}

export function formatMaybeDate(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return "not recorded";
  }
  return new Date(value).toLocaleString();
}

export function shortId(value: string): string {
  return value.length <= 10 ? value : `${value.slice(0, 8)}...`;
}
