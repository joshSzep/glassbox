# V15 Repository Intelligence Advisory Evidence

This summary completes `GBX-1554` from [tasks-v15.md](./tasks-v15.md). It
records bounded browser, keyboard, responsive, and accessibility-adjacent
evidence for the repository intelligence console and the changeset surfaces
that link into it.

- Date: May 9, 2026 America/Los_Angeles
- Operator: Codex
- Evidence posture: advisory local evidence
- Primary deterministic checks cited separately:
  `pnpm --dir frontend test`,
  `pnpm --dir frontend lint`,
  `pnpm --dir frontend typecheck`,
  `pnpm --dir frontend format:check`,
  `uv run pytest tests/integration/test_web_changeset_routes.py -q`,
  `uv run pytest tests/unit/test_release_candidate_docs.py -q`, and the
  repository pre-commit gate.
- Browser checks cited separately:
  `env WATCHPACK_POLLING=true pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts -g "reviewer can inspect a changeset and generate a brief"`
  and an in-app browser smoke check against
  `http://127.0.0.1:8765/app/changesets` plus
  `/app/repository-index?path=frontend/components/console/changeset-console.tsx`.

## Observed Coverage

| Scenario | Status | Evidence | Limitations |
| --- | --- | --- | --- |
| Repository map | observed | The repository index route rendered `Repository Index`, `Inspect Path`, and `Command Recipes` in the local browser. Unit/component tests cover the repository map, freshness, path inspector, recipe browser, and memory panels. | The local browser smoke check used the current workspace state, which had zero live changesets. Fixture-backed Playwright covers populated changeset data. |
| Path inspector deep link | observed | The changeset Playwright workflow clicked the changed-path link to `/app/repository-index?path=frontend%2Fcomponents%2Fconsole%2Fchangeset-console.tsx` and verified that the repository path input preloaded the changed path. | This is fixture-backed browser evidence, not proof that every possible path kind has a useful repository-intelligence snapshot. |
| Command recipes | observed | Repository command recipes rendered in the repository console and the changeset repository-intelligence panel exposed advisory command recipes and recommended next actions. | Recipes remain advisory until an explicit deterministic command runs and retains verification evidence. |
| Changeset links | observed | The changeset surface rendered `Repository Intelligence`, displayed advisory recommendations beside deterministic verification posture, and exposed changed-path links to the repository inspector. | Owner hints are routing context only; they are not reviewer assignment or approval authority. |
| Stale-intelligence states | partially observed | Component/store tests cover degraded or missing repository intelligence states, and the UI preserves partial-load errors as advisory state lines. | No live stale repository snapshot was forced during this pass. |

## Accessibility And Keyboard Notes

| Area | Status | Notes | Claims not made |
| --- | --- | --- | --- |
| Keyboard flow | observed | The existing operator Playwright workflow exercises the changeset route and repository inspector link with stable headings, links, and form labels. | No full keyboard-only manual transcript was retained for every panel. |
| Focus-visible state | covered by existing component styling | Repository and changeset links/buttons use the existing focus-visible ring and named controls. | No pixel-perfect focus audit or contrast certification is claimed. |
| Responsive layout | covered by existing e2e and component constraints | Repository and changeset panels use dense grids, wrapping text, and break-all handling for long paths and commands; existing mobile operator workflows remain in the Playwright suite. | No fresh manual mobile screenshot was retained for `GBX-1554`. |
| Long path wrapping | observed | Static markup and Playwright coverage include long changed paths and repository links; path labels use break-all or wrapped text. | No exhaustive path-length fuzzing was run. |
| Assistive technology | skipped | Screen-reader pairing was not run for this task. | No WCAG conformance, screen-reader compatibility, or accessibility certification claim. |

## Findings

| Area | Finding | Disposition |
| --- | --- | --- |
| Repository deep link | The first in-app browser smoke check showed that the route loaded but the path input did not visibly refresh after async path inspection. | Fixed by keying the repository path input on `repository.pathQuery`; the targeted Playwright workflow now verifies the preloaded path. |
| Local dashboard smoke | `/app/changesets` rendered correctly against the current workspace but had zero local changesets. | Kept as advisory shell evidence; populated changeset behavior is covered by the fixture-backed browser workflow. |
| Dev-server reliability | Local Playwright runs use `WATCHPACK_POLLING=true` to avoid macOS Watchpack `EMFILE` watcher startup issues seen in earlier dev-server attempts. | This is an environment note, not a product bug. |

## Non-Claims

- browser and dashboard evidence is advisory, not deterministic release
  authority
- repository intelligence is local, rebuildable evidence, not hosted code
  indexing or cloud retrieval
- command recipes and verification recommendations do not prove verification
  passed
- owner hints do not assign reviewers, approve changes, or authorize merge
- skipped accessibility evidence is not a pass
- no WCAG conformance, screen-reader compatibility, or accessibility
  certification is claimed
- Glassbox did not stage, commit, push, open a PR, merge, deploy, publish, or
  run commands from recipe text through these dashboard controls
