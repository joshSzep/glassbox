# v8 Dashboard Autonomy Accessibility Review

This review records the `GBX-886` autonomy-console accessibility and long-session UX evidence for the v8 track. It extends the bounded dashboard claims from [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md) to the task, memory, repository-index, and branch-search autonomy surfaces.

## Named Pairings

| Pairing                                                                        | Status                                                              | Evidence                                                                                                                                                                                          |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Chromium through Playwright on macOS, keyboard-only, desktop `1440x900` family | Reviewed through routed dashboard workflows and component semantics | `frontend/e2e/operator-workflows.spec.ts`, `frontend/tests/task-autonomy-console.test.tsx`, `frontend/tests/knowledge-autonomy-console.test.tsx`, `frontend/tests/branch-search-console.test.tsx` |
| Chromium through Playwright on macOS, keyboard-only, mobile `390x844` family   | Reviewed through selected-session and branch-search drill-in smoke  | `mobile operator can drill into a session, act, and return to queues`, `mobile operator can select a branch-search candidate from the keyboard`                                                   |
| Chromium through Playwright role and accessible-name queries                   | Reviewed as an automation proxy for named regions and controls      | task controls, memory detail, repository detail, branch-search list, branch-search candidates, evidence regions                                                                                   |
| macOS VoiceOver, NVDA, Narrator, Orca, Safari, Firefox                         | Not executed in this environment                                    | Non-claim; requires retained manual reviewer evidence before screen-reader or cross-browser claims                                                                                                |

## Review Scope

Reviewed v8 autonomy areas:

- task queue filters, selected task inspector, plan steps, task controls, budget mode/step controls, task event history, and why-this-action evidence
- memory filters, memory search, memory detail provenance, confirm, invalidate, preview-prune, and prune actions
- repository index status, repository search, keyboard-selectable index rows, selected entry detail, and rebuild action
- branch-search list, candidate comparison table, candidate evidence cards, and select/review/reject metadata actions
- mobile branch-search selection and existing mobile selected-session drill-in

## Fixes From This Pass

- Repository index rows now expose a keyboard-selectable button for selecting an index entry.
- Memory and repository search inputs now have explicit accessible names.
- Branch-search list and candidate action buttons now have stable accessible names.
- Branch candidate reject uses the destructive button treatment, separating it from select/review metadata actions.

## Validation Commands

Focused review commands:

```bash
pnpm --dir frontend exec vitest run \
  tests/task-autonomy-console.test.tsx \
  tests/knowledge-autonomy-console.test.tsx \
  tests/branch-search-console.test.tsx

pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts \
  -g "task controls|memory and repository|branch-search candidate"
```

Release evidence path for a candidate run:

```text
.glassbox/releases/<candidate>/dashboard-autonomy-accessibility/manual-validation.md
```

Full frontend validation used for the task commit:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts
```

## Supported Claims

- The reviewed Chromium/Playwright autonomy-console workflows are keyboard-operable for start, pause, resume, cancel, budget review, memory confirmation/invalidation/prune review, repository rebuild, and branch candidate selection.
- The reviewed autonomy surfaces expose named regions and controls for Playwright role queries and browser accessibility-tree naming.
- Destructive actions are text-labeled and visually distinguished in the reviewed surfaces.
- The reviewed mobile viewport can reach session drill-in and branch-search candidate selection without horizontal overflow.

## Non-Claims And Residual Risks

- This is not formal WCAG, VPAT, or screen-reader certification.
- VoiceOver and other screen-reader pairings were not executed.
- Browser zoom, high-contrast mode, non-Chromium browsers, and long real-world task queues remain manual review items.
- Dense tables remain optimized for operator scanning; a future pass should review row/column narration with a real screen reader before making broader claims.
