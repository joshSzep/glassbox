import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { KnowledgeAutonomyConsole } from "@/components/console/knowledge-autonomy-console";
import type { components } from "@/generated/api-types";
import type { MemoryInspectorState, RepositoryInspectorState } from "@/stores/dashboard-stores";

type MemoryEntry = components["schemas"]["WorkspaceMemoryEntryResponse"];
type RepositoryEntry = components["schemas"]["RepositoryIndexEntryResponse"];
type RepositoryStatus = components["schemas"]["RepositoryIndexStatusResponse"];

describe("knowledge autonomy console", () => {
  it("renders memory filters, provenance, actions, and prune previews", () => {
    const entry = makeMemoryEntry("memory-1", { state: "stale" });
    const markup = renderToStaticMarkup(
      React.createElement(KnowledgeAutonomyConsole, {
        memory: {
          ...idleMemory,
          filter: "stale",
          items: [entry],
          loadState: "loaded",
          preview: { entry, reason: "cleanup", would_prune: true },
          selectedEntry: entry,
          selectedMemoryId: "memory-1",
        },
        repository: idleRepository,
        surface: "memory",
      }),
    );

    expect(markup).toContain("Memory Inspector");
    expect(markup).toContain("Memory Filters");
    expect(markup).toContain('aria-label="Search workspace memory"');
    expect(markup).toContain("Backend tests use uv");
    expect(markup).toContain("session_event session-");
    expect(markup).toContain("1 prompt use");
    expect(markup).toContain("Confirm");
    expect(markup).toContain("Invalidate");
    expect(markup).toContain("Preview Prune");
    expect(markup).toContain("This entry would be pruned");
  });

  it("renders repository index status, stale warnings, search rows, and detail", () => {
    const entry = makeRepositoryEntry("entry-1");
    const markup = renderToStaticMarkup(
      React.createElement(KnowledgeAutonomyConsole, {
        anchorSessionId: "session-123456789",
        memory: idleMemory,
        repository: {
          ...idleRepository,
          items: [entry],
          query: "UsefulThing",
          searchState: "loaded",
          selectedEntry: entry,
          selectedEntryId: "entry-1",
          status: makeRepositoryStatus({
            built_at: null,
            builder_version: null,
            detail: "repository index has not been built",
            schema_version: null,
            source_digest: null,
            status: "missing",
          }),
          statusState: "loaded",
        },
        surface: "repository",
      }),
    );

    expect(markup).toContain("Repository Index");
    expect(markup).toContain('aria-label="Search repository index"');
    expect(markup).toContain("repository index has not been built");
    expect(markup).toContain("Rebuild Index");
    expect(markup).toContain("UsefulThing");
    expect(markup).toContain("src/sample.py");
    expect(markup).toContain("static_analysis");
    expect(markup).toContain("session session-...");
  });
});

const page = { cursor: 0, has_more: false, limit: 100, next_cursor: null, returned_count: 0 };

const idleMemory: MemoryInspectorState = {
  error: null,
  filter: "active",
  items: [],
  loadState: "idle",
  page,
  preview: null,
  query: "",
  selectedEntry: null,
  selectedMemoryId: null,
};

const idleRepository: RepositoryInspectorState = {
  error: null,
  items: [],
  query: "",
  rebuild: null,
  searchState: "idle",
  selectedEntry: null,
  selectedEntryId: null,
  status: null,
  statusState: "idle",
};

function makeRepositoryStatus(overrides: Partial<RepositoryStatus> = {}): RepositoryStatus {
  return {
    built_at: null,
    builder_version: null,
    command_recipe_count: 0,
    detail: null,
    doc_root_count: 0,
    entry_count: 1,
    generated_path_count: 0,
    limitations: [],
    ownership_hint_count: 0,
    package_boundary_count: 0,
    path: "/tmp/.glassbox/repository-index.json",
    policy_sensitive_path_count: 0,
    release_surface_count: 0,
    schema_version: null,
    source_digest: null,
    source_manifest_count: 0,
    source_root_count: 0,
    status: "missing",
    subsystem_count: 0,
    test_root_count: 0,
    ...overrides,
  };
}

function makeMemoryEntry(memoryId: string, overrides: Partial<MemoryEntry> = {}): MemoryEntry {
  return {
    confirmed_at: "2026-04-23T00:00:00Z",
    confirmed_by: "operator",
    content: "Use uv run pytest for backend tests.",
    created_at: "2026-04-23T00:00:00Z",
    created_by: "operator",
    import_source: null,
    invalidated_at: null,
    invalidated_by: null,
    invalidation_reason: null,
    kind: "command",
    last_sequence: 2,
    last_used_at: "2026-04-23T00:01:00Z",
    memory_id: memoryId,
    provenance: {
      artifact_id: null,
      note: null,
      session_id: "session-1",
      source_label: null,
      source_sequence: 1,
      source_type: "session_event",
      task_id: null,
      tool_call_id: null,
    },
    prune_reason: null,
    pruned_at: null,
    pruned_by: null,
    redacted: false,
    session_id: "session-1",
    state: "active",
    summary: "Backend tests use uv",
    tags: ["tests"],
    updated_at: "2026-04-23T00:01:00Z",
    use_count: 1,
    ...overrides,
  };
}

function makeRepositoryEntry(
  entryId: string,
  overrides: Partial<RepositoryEntry> = {},
): RepositoryEntry {
  return {
    entry_id: entryId,
    kind: "symbol",
    language: "python",
    name: "UsefulThing",
    path: "src/sample.py",
    provenance: [
      {
        content_sha256: null,
        line_end: 1,
        line_start: 1,
        note: null,
        path: "src/sample.py",
        source_label: null,
        source_type: "static_analysis",
        tool_name: null,
      },
    ],
    summary: "Class UsefulThing",
    symbol: "UsefulThing",
    tags: ["source"],
    updated_at: "2026-04-23T00:00:00Z",
    ...overrides,
  };
}
