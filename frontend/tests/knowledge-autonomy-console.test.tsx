import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { KnowledgeAutonomyConsole } from "@/components/console/knowledge-autonomy-console";
import type { components } from "@/generated/api-types";
import type { MemoryInspectorState, RepositoryInspectorState } from "@/stores/dashboard-stores";

type MemoryEntry = components["schemas"]["WorkspaceMemoryEntryResponse"];
type RepositoryEntry = components["schemas"]["RepositoryIndexEntryResponse"];
type RepositoryStatus = components["schemas"]["RepositoryIndexStatusResponse"];
type RepositoryOverview = NonNullable<RepositoryInspectorState["overview"]>;
type RepositoryPathInspection = NonNullable<RepositoryInspectorState["pathInspection"]>;
type RepositoryVerification = NonNullable<RepositoryInspectorState["verification"]>;
type RepositoryMemoryCandidate = RepositoryInspectorState["memoryCandidates"][number];

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
    expect(markup).toContain("Intelligence Status");
    expect(markup).toContain('aria-label="Search repository intelligence"');
    expect(markup).toContain("Repository path inspector");
    expect(markup).toContain("Command Recipes");
    expect(markup).toContain("Memory Facts");
    expect(markup).toContain("repository index has not been built");
    expect(markup).toContain("Refresh Intelligence");
    expect(markup).toContain("UsefulThing");
    expect(markup).toContain("src/sample.py");
    expect(markup).toContain("static_analysis");
    expect(markup).toContain("session session-...");
  });

  it("renders repository map, path verification, recipes, and memory candidates", () => {
    const markup = renderToStaticMarkup(
      React.createElement(KnowledgeAutonomyConsole, {
        anchorSessionId: "session-123456789",
        memory: idleMemory,
        repository: {
          ...idleRepository,
          commandRecipes: makeCommandRecipes(),
          memoryCandidates: [makeRepositoryMemoryCandidate("candidate-1")],
          overview: makeRepositoryOverview(),
          pathInspection: makeRepositoryPathInspection(),
          pathQuery: "src/sample.py",
          status: makeRepositoryStatus({
            command_recipe_count: 1,
            package_boundary_count: 1,
            release_surface_count: 1,
            source_root_count: 1,
            status: "fresh",
            subsystem_count: 1,
          }),
          statusState: "loaded",
          verification: makeRepositoryVerification(),
        },
        surface: "repository",
      }),
    );

    expect(markup).toContain("Repository Map");
    expect(markup).toContain("1 packages, 1 subsystems, 1 release-sensitive surfaces.");
    expect(markup).toContain("src/sample.py");
    expect(markup).toContain("package:fixture");
    expect(markup).toContain("Runtime");
    expect(markup).toContain("@runtime-team");
    expect(markup).toContain("Release Gate");
    expect(markup).toContain("uv run pytest tests");
    expect(markup).toContain("Review candidate · repository intelligence");
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
  commandRecipes: [],
  error: null,
  freshness: null,
  items: [],
  memoryCandidates: [],
  overview: null,
  pathInspection: null,
  pathQuery: "",
  query: "",
  rebuild: null,
  searchState: "idle",
  selectedEntry: null,
  selectedEntryId: null,
  status: null,
  statusState: "idle",
  verification: null,
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
    memory_reference_count: 0,
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

function makeRepositoryOverview(overrides: Partial<RepositoryOverview> = {}): RepositoryOverview {
  return {
    doc_roots: [],
    generated_paths: [],
    index: makeRepositoryStatus({ status: "fresh" }),
    limitations: [],
    memory_references: [
      {
        confirmed_at: "2026-04-23T00:00:00Z",
        confirmed_by: "operator",
        confidence: "high",
        kind: "command",
        limitations: [],
        memory_id: "memory-1",
        provenance: {},
        redacted: false,
        reference_id: "memory-reference-1",
        source_label: "operator note",
        summary: "Backend tests use uv",
        tags: ["repository-intelligence"],
      },
    ],
    package_boundaries: [
      {
        confidence: "high",
        doc_roots: [],
        generated_paths: [],
        kind: "python",
        limitations: [],
        manifest_paths: ["pyproject.toml"],
        name: "fixture",
        package_id: "package:fixture",
        provenance: [],
        root: ".",
        source_roots: ["src"],
        test_roots: ["tests"],
      },
    ],
    policy_sensitive_paths: [],
    release_surfaces: [
      {
        command_recipe_ids: ["recipe:pytest"],
        confidence: "high",
        kind: "release_candidate",
        limitations: [],
        name: "Release Gate",
        provenance: [],
        scope_paths: ["scripts", "docs"],
        surface_id: "release:v15",
      },
    ],
    source_manifests: [],
    source_roots: [
      {
        confidence: "high",
        hint_id: "source-root:src",
        kind: "source_root",
        language: "python",
        limitations: [],
        package_id: "package:fixture",
        path: "src",
        provenance: [],
      },
    ],
    subsystems: [
      {
        confidence: "high",
        limitations: [],
        name: "Runtime",
        owner_hint_ids: ["owner:runtime"],
        package_ids: ["package:fixture"],
        provenance: [],
        release_surface_ids: ["release:v15"],
        scope_paths: ["src"],
        subsystem_id: "subsystem:runtime",
        tags: ["runtime"],
      },
    ],
    test_roots: [],
    topology: null,
    ...overrides,
  };
}

function makeCommandRecipes() {
  return [
    {
      command: "uv run pytest tests",
      confidence: "high",
      limitations: [],
      name: "Backend tests",
      provenance: [],
      purpose: "test",
      recipe_id: "recipe:pytest",
      review_relevance: "direct",
      risk: "read_only",
      scope_paths: ["src", "tests"],
      timeout_seconds: null,
      toolchain: "uv",
    },
  ] satisfies RepositoryPathInspection["command_recipes"];
}

function makeRepositoryPathInspection(
  overrides: Partial<RepositoryPathInspection> = {},
): RepositoryPathInspection {
  const overview = makeRepositoryOverview();
  return {
    command_recipes: makeCommandRecipes(),
    next_actions: ["glassbox repo recommend src/sample.py"],
    ownership_hints: [
      {
        confidence: "high",
        hint_id: "owner:runtime",
        limitations: [],
        owner_label: "@runtime-team",
        provenance: [],
        scope_paths: ["src"],
        subsystem: "Runtime",
      },
    ],
    packages: overview.package_boundaries,
    path: "src/sample.py",
    path_hints: overview.source_roots,
    release_surfaces: overview.release_surfaces,
    snapshot_status: "fresh",
    subsystems: overview.subsystems,
    ...overrides,
  };
}

function makeRepositoryVerification(
  overrides: Partial<RepositoryVerification> = {},
): RepositoryVerification {
  return {
    detail: null,
    next_actions: ["uv run pytest tests"],
    paths: ["src/sample.py"],
    report: null,
    status: "ok",
    ...overrides,
  };
}

function makeRepositoryMemoryCandidate(
  candidateId: string,
  overrides: Partial<RepositoryMemoryCandidate> = {},
): RepositoryMemoryCandidate {
  return {
    candidate_id: candidateId,
    content: "Use uv run pytest tests for backend checks.",
    created_at: "2026-04-23T00:00:00Z",
    kind: "command",
    provenance: makeMemoryEntry("memory-1").provenance,
    redacted: false,
    session_id: "session-1",
    source_label: "repository intelligence",
    summary: "Backend test command",
    tags: ["repository-intelligence"],
    ...overrides,
  };
}
