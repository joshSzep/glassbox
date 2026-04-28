# v6 Dashboard Accessibility And Responsive Review

This review records the `GBX-692` dashboard evidence for the v6
release-candidate track. It reuses the v4 screenshot archive infrastructure and
the v6 manual QA convention in [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md).

## Review Scope

Reviewed viewport families:

| Viewport | Evidence |
| --- | --- |
| Desktop `1440x900` | v4 screenshot archive default desktop captures |
| Narrow desktop / tablet `1024x768` family | v4 screenshot archive narrow-desktop and tablet captures |
| Portrait tablet `768x1024` family | tablet archive captures for live, failed, approval, compare, artifact, and large-transcript states |
| Mobile `390x844` | v4 screenshot archive default mobile captures and Playwright narrow viewport workflow |

Reviewed operator states:

- empty workspace and all-queues triage
- live, historical, failed, pending approval, and pending question sessions
- branched sessions, lineage, compare, evidence, runtime, and timeline tabs
- projection-degraded and artifact-backed verification cues
- large transcript state with active tool, approval, evidence, and runtime notes
- action failure feedback and inspect-only historical session behavior

## Keyboard And Accessibility Notes

Claims supported by this review:

- Queue navigation, session selection, tab selection, prompt, answer, approval,
  fork, compare, evidence, and recovery/degraded states are covered by frontend
  component tests, Playwright keyboard workflows, or screenshot archive states.
- The primary console frame remains reachable in a narrow viewport.
- The screenshot archive checks representative responsive states for wrapping,
  action discoverability, and route correctness.
- Status and priority indicators use text labels alongside visual treatment in
  the reviewed states.

Non-claims:

- This is not a formal WCAG certification.
- This is not a full screen-reader audit across every browser and assistive
  technology pairing.
- The screenshot archive is review evidence, not a pixel-perfect visual
  regression baseline.

## Validation Run

Commands run from the repository root:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend test:e2e
pnpm --dir frontend screenshots:v4-audit
```

Results:

- lint passed after removing two stale unused icon imports
- typecheck passed
- Vitest passed: `14` files, `79` tests
- Playwright e2e passed: `12` tests
- screenshot archive passed: `67` captures

Generated screenshots are local artifacts under:

```text
frontend/test-results/v4-audit-screenshots/
```

Do not commit screenshot binaries by default; link or attach them from the v6
manual evidence directory when a release candidate needs visual signoff.

## Follow-Up Issues

No blocking dashboard UX issue was found in this pass. The only code cleanup was
removing unused icon imports surfaced by lint.
