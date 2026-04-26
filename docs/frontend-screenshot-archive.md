# Frontend Screenshot Archive

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the v4 screenshot archive workflow for auditing and reviewing Glassbox dashboard UX changes.

## Purpose

The v4 screenshot archive is a repeatable Playwright capture of representative dashboard states. It exists to make UX hierarchy, responsive behavior, action placement, overflow, and visual regressions reviewable while the operator console is redesigned.

Screenshots are audit artifacts first. They are not strict pixel baselines unless a later task deliberately introduces a visual-regression gate.

## Generate The Archive

Run the full archive from the repository root:

```bash
pnpm --dir frontend screenshots:v4-audit
```

Run one scenario when refreshing a focused UX change:

```bash
pnpm --dir frontend screenshots:v4-audit -- --scenario pending-question
```

The archive is written to:

```text
frontend/test-results/v4-audit-screenshots/
```

That directory is ignored by git through the existing `frontend/test-results/` ignore rule. Do not commit screenshot binaries by default. Attach them to a review, publish them as CI artifacts, or keep them locally unless the repository explicitly chooses a committed artifact path.

Each run writes:

- `manifest.json`: machine-readable scenario, route, viewport, revision, and file metadata
- `index.md`: a compact review table linking every generated image
- `*.png`: full-page screenshots for each scenario and viewport

## Scenario Names

The v4 archive uses stable scenario names so before/after review stays easy:

- `empty-workspace`
- `all-queues`
- `live-session`
- `historical-session`
- `failed-session`
- `pending-approval`
- `pending-question`
- `branched-session`
- `compare-view`
- `projection-degraded`
- `artifact-drift`

The default viewport set is desktop `1440x900` and mobile `390x844`.

## Maintenance Rules

Refresh the relevant screenshot scenarios whenever a task changes visible UX, including:

- page or panel layout
- visual hierarchy, density, spacing, color, or typography
- queue rows, status chips, tabs, dialogs, sheets, or action controls
- operator-facing copy, empty states, loading states, error states, or action feedback
- responsive behavior or mobile navigation
- transcript, timeline, lineage, compare, runtime, evidence, verification, or drift surfaces

For pure transport, reducer, state-model, generated-type, or backend changes that do not affect rendered UX, note that the archive was reviewed and left unchanged.

## Review Checklist

When reviewing an archive, check:

- the first visible screen identifies workspace health and highest-priority operator work
- urgent approval and question states are visually stronger than passive diagnostics
- inspector tabs reduce clutter rather than rendering every pane at once
- transcript, timeline, runtime, evidence, lineage, compare, and verification surfaces are reachable without crowding the default view
- mobile captures have no horizontal scrolling and keep actions discoverable
- text fits inside buttons, rows, cards, tables, and panels
- status and health indicators do not rely on color alone
- advisory verification or drift cues do not visually read as runtime failures

## Relationship To v4 Tasks

[tasks-v4.md](./tasks-v4.md) treats this archive as a living artifact. Phase 49 creates the harness and captures the current SPA baseline. Later v4 tasks refresh the relevant screenshots as the frontend UX changes.
