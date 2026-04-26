# v4 UX Release Gate

This gate decides whether the v4 dashboard is ready to be treated as the
baseline operator console. It is stricter than parity: the console must help an
operator scan queues, choose safe actions, inspect evidence, and recover context
across desktop and mobile workflows.

## Release Command

Run the automated gate from the repository root:

```sh
pnpm --dir frontend validate:v4-ux
```

The command runs frontend format, lint, typecheck, unit/component tests,
Playwright workflows, the v4 screenshot archive, static export, and the Python
web/dashboard integration tests.

## Checklist

- Attention queues: approvals, questions, failures, degraded sessions, active work, historical sessions, and all sessions are visible and routeable.
- Selected-session overview: status, stream state, projection health, next action, recent narrative, decision context, and health attention are visible before passive diagnostics.
- Inspector tabs: overview, transcript, timeline, actions, lineage, compare, runtime, evidence, metrics, and events are direct-linkable and keyboard reachable.
- Priority actions: answer, approval approve/deny, prompt submit, and fork creation show pending, success, conflict, validation, network, and unavailable-runtime feedback.
- Narrative and timeline: transcript turns, timeline jumps, fork boundaries, active turns, pending interventions, metrics, and live output remain readable.
- Runtime and evidence: working set, runtime notes, artifact provenance, event evidence, projection details, raw metrics, and verification cues are preserved behind progressive panes.
- Lineage and compare: parent, child, forkable turns, compare target opening, compare clearing, and child opening are covered.
- Verification cues: blocking evidence, advisory drift, verified artifacts, missing artifacts, and inherited working-set evidence are distinguishable without relying on color alone.
- Mobile drill-in: queue browsing, selected-session inspection, action completion, and return-to-queue navigation work without horizontal scrolling.
- Accessibility: pointer-free operation covers queue selection, session opening, tab changes, transcript/timeline jumps, composer submit, answer submit, approval decisions, fork dialog, lineage targets, compare targets, and mobile return.
- Visual density: shared surface, row-height, chip, focus, and status tokens produce a dense operator console rather than nested decorative panels.

## Automated Coverage Map

| Requirement                                        | Primary automated evidence                                                                                                     |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Attention queues and priority row triage           | `frontend/tests/workspace-overview.test.ts`, `frontend/e2e/operator-workflows.spec.ts`                                         |
| Selected-session overview and priority actions     | `frontend/tests/session-inspector.test.ts`, `frontend/tests/operator-actions.component.test.tsx`                               |
| Keyboard and focus behavior                        | `frontend/tests/operator-actions.component.test.tsx`, keyboard-only Playwright workflow                                        |
| Browser action workflows                           | `frontend/e2e/operator-workflows.spec.ts`                                                                                      |
| Lineage and compare                                | `frontend/tests/session-inspector.test.ts`, lineage/compare Playwright workflows                                               |
| Runtime, evidence, metrics, verification cues      | `frontend/tests/session-inspector.test.ts`, `frontend/tests/verification-cues.test.ts`, artifact/degraded Playwright workflows |
| Visual density and design tokens                   | `frontend/tests/design-system.test.ts`, v4 screenshot archive                                                                  |
| Desktop, narrow desktop, tablet, and mobile layout | `frontend/e2e/v4-audit-screenshots.spec.ts`                                                                                    |
| Static export and FastAPI serving path             | `pnpm --dir frontend build`, `tests/integration/test_web_spa_static.py`                                                        |
| API/SSE/dashboard backend contract                 | Python web/dashboard integration tests listed by `validate:v4-ux`                                                              |

## Screenshot Review

The archive lives at `frontend/test-results/v4-audit-screenshots/` after a gate
run. Review `index.md` and spot-check at least these states before approving a
release:

- all queues on desktop, narrow desktop, and mobile
- pending approval and pending question on desktop and mobile
- large transcript evidence/runtime panes on desktop, tablet, and mobile
- lineage and compare on desktop and mobile
- projection degraded and artifact drift evidence panes
- historical inspect-only state

The archive test fails on visible Next dev chrome, blank primary regions,
blank selected-session inspectors, and horizontal overflow. Visual review still
needs human judgment for hierarchy, copy clarity, and whether the next action is
obvious.

## Manual Validation

- Start local development with FastAPI and Next.js, then browse `/app`, filtered queues, and direct selected-session URLs.
- Build production assets with `pnpm --dir frontend build`, start `uv run glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765`, and smoke `/`, `/app`, and a selected-session URL from the served static dashboard.
- Use only the keyboard through queue selection, tab changes, answer submit, approval resolution, fork creation, lineage navigation, compare navigation, and mobile return-to-queue.
- Confirm reduced-motion mode does not hide status feedback and visible focus rings do not shift layout.
- Confirm replay/eval verification cues reference persisted artifact summaries and do not imply the browser executed replay or eval.

## Known Non-Blocking Gaps

- The screenshot archive records deterministic fixtures, not live provider sessions.
- Manual screen-reader review is still required before a public accessibility claim.
- The browser surfaces replay/eval artifact evidence but leaves execution and reproduction to CLI workflows.
- Pixel comparison is intentionally limited to stable layout invariants; screenshot review remains a human approval step.
