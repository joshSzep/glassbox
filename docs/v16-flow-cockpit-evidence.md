# V16 Flow Cockpit Advisory Evidence

This note records the `GBX-1654` advisory browser and accessibility evidence for
the v16 flow cockpit surfaces. It follows
[browser-accessibility-evidence.md](./browser-accessibility-evidence.md) and is
local review evidence only.

## Browser Walkthrough

- Date: 2026-05-12
- Environment: frontend Playwright fixture, local Next.js dev server
- Browser: Playwright Chromium, desktop viewport `1280x900`, mobile viewport
  `390x844`
- Route coverage:
  - `/app` with the `projection-degraded` fixture
  - `/app/changesets/changeset-1`
- Observed:
  - the unified operator queue rendered the `Maintenance` lane with the
    advisory `Inspect stale projection` cue
  - the changeset evidence graph rendered summary counts, claim support,
    missing evidence, stale command evidence, and bounded graph limitations
  - the verification plan rendered deterministic checks, skipped advisory live
    evidence, the disabled run/retry/risk controls, and the explicit `Select`
    action
  - selecting the verification entry called
    `/changesets/changeset-1/record-verification` and reloaded the cockpit
    state with the retained-selection message
  - the changeset evidence graph remained inspectable after resizing to
    `390x844`, with no horizontal document overflow in the Playwright check

## Accessibility Pairing Notes

- Keyboard focus: Playwright interacted with the verification `Select` button
  through the same accessible button surface used by keyboard users; existing
  operator workflow tests retain broader keyboard navigation coverage for
  queue filters, session tabs, task controls, memory, repository, and branch
  search surfaces.
- Focus-visible state: the queue rows, deep links, and evidence graph node
  anchors use visible focus ring styles from the shared console controls.
- Responsive layout: the retained mobile check covered the changeset evidence
  graph and verification plan after a desktop walkthrough; text-heavy graph
  nodes and command strings use wrapping or truncation containers.
- Long-path and command text: the walkthrough covered changed-path links,
  command text, stale evidence summaries, and advisory safe-action copy.
- Assistive technology: no screen reader, VoiceOver, NVDA, Narrator, Orca,
  Safari, Firefox, touch, or contrast-tool pairing was run. The fixture retains
  an explicit skipped accessibility evidence row for the missing screen-reader
  pairing.

## Validation

```bash
env WATCHPACK_POLLING=true \
  pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts \
  -g "operator can inspect v16 cockpit evidence surfaces"
```

Also retained for the same task:

```bash
pnpm --dir frontend test -- workspace-overview.test.ts changeset-console.test.ts dashboard-stores.test.ts
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend format:check
```

## Limitations And Non-Claims

- This evidence is advisory and does not replace deterministic unit,
  integration, API, replay, eval, package, or release-gate evidence.
- This pass does not claim WCAG conformance, accessibility certification,
  screen-reader compatibility, cross-browser support, mobile touch coverage, or
  reviewer approval.
- Fixture-backed Playwright data proves route behavior against the fixture only;
  live workspace data should be rechecked before release signoff if the
  cockpit contract changes.
- Browser and accessibility evidence remains non-blocking unless a later task
  promotes a specific deterministic fixture into a release gate.
