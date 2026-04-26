# Frontend Screenshot Archive

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the v4 screenshot archive workflow for auditing and reviewing Glassbox dashboard UX changes.

## Purpose

The v4 screenshot archive is a repeatable Playwright capture of representative dashboard states. It exists to make UX hierarchy, responsive behavior, action placement, overflow, and visual regressions reviewable while the operator console is redesigned.

Screenshots are audit artifacts first. They are not strict pixel baselines unless a later task deliberately introduces a visual-regression gate.

Archive captures should contain only Glassbox operator-console UI and deterministic fixture data. The screenshot command disables Next.js dev indicators during capture and checks for known dev-only overlay roots before writing images.

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
- `large-transcript`

The default viewport set is desktop `1440x900` and mobile `390x844`.

## Scenario Coverage Contract

The scenario fixtures are shared by component tests and Playwright route mocks
through `frontend/tests/fixtures/session-state.ts`. Keep scenario payloads typed
against generated OpenAPI schemas so fixture drift is caught by frontend
typecheck instead of by a late browser test.

| Scenario              | Expected Operator Decision                                                   | Archive Capture       | Critical Viewports              | Mobile Overflow Expectation                                                                                                     |
| --------------------- | ---------------------------------------------------------------------------- | --------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `empty-workspace`     | Confirm there is no current operator work.                                   | `empty-workspace`     | desktop, mobile                 | Workspace status and empty queue copy wrap without clipping.                                                                    |
| `all-queues`          | Pick the highest-priority pending approval before lower queues.              | `all-queues`          | desktop, narrow desktop, mobile | Queue rows expose next action and pending subject as stacked text with no horizontal scrolling.                                 |
| `live-session`        | Continue or answer the live session while preserving stream context.         | `live-session`        | desktop, tablet, mobile         | Composer, answer controls, and live output wrap before passive diagnostics.                                                     |
| `historical-session`  | Inspect a completed session without mistaking it for broken live work.       | `historical-session`  | desktop, mobile                 | Historical status and unavailable live actions wrap clearly.                                                                    |
| `failed-session`      | Decide whether the retryable failure needs inspection or recovery.           | `failed-session`      | desktop, tablet, mobile         | Failure summary and retry guidance appear before generic evidence and wrap cleanly.                                             |
| `pending-approval`    | Approve or deny the requested workspace write with risk context visible.     | `pending-approval`    | desktop, tablet, mobile         | Approval subject, reason, risk label, and approve/deny controls stay readable in the primary action area.                       |
| `pending-question`    | Answer the pending `ask_user` question before sending new prompts.           | `pending-question`    | desktop, tablet, mobile         | Question text and answer control stay above transcript or evidence detail.                                                      |
| `branched-session`    | Inspect child lineage and decide whether to fork from the latest boundary.   | `branched-session`    | desktop, mobile                 | Lineage rows, branch labels, and fork controls wrap without hiding branch context.                                              |
| `compare-view`        | Compare the selected session against its parent before branch triage.        | `compare-view`        | desktop, tablet, mobile         | Compare target, compared transcript, and long branch labels remain readable in stacked layouts.                                 |
| `projection-degraded` | Check projection health while preserving confidence in canonical events.     | `projection-degraded` | desktop, mobile                 | Projection detail and repair guidance wrap as advisory health copy.                                                             |
| `artifact-drift`      | Inspect artifact-backed drift cues without treating them as runtime failure. | `artifact-drift`      | desktop, tablet, mobile         | Artifact labels, summaries, artifact paths, and target paths wrap within evidence panels.                                       |
| `large-transcript`    | Keep the current action visible while scanning a noisy live session.         | `large-transcript`    | desktop, tablet, mobile         | Long transcript entries, active tool output, approval controls, and artifact cues do not widen the viewport or bury the action. |

The large-transcript fixture is intentionally noisy: it includes a pending
approval, active tool call, live SSE output, runtime notes, artifact-backed
context, working-set evidence, and a long transcript. Use it when a v4 change
risks making the action rail disappear under evidence or transcript volume.

When adding or changing a scenario, update this table, the shared fixture
metadata, and any focused component or Playwright expectations in the same
change. Do not hand-write payloads that bypass the shared builders unless a test
is deliberately validating malformed API data.

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

- no Next.js dev indicator or other tooling overlay is visible in the screenshot
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
