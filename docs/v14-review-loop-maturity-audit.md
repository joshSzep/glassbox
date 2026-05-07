# V14 Review-Loop Maturity Audit

This audit completes `GBX-1401` from [tasks-v14.md](./tasks-v14.md). It maps
the v13 dogfooding follow-up candidates from
[v13-dogfooding-summary.md](./v13-dogfooding-summary.md) to current source
surfaces, v14 dispositions, and accepted non-goals.

The audit uses the v14 boundary from
[v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md):
improve local review-loop evidence ergonomics without adding hosted review,
review approval, automatic git mutation, pull request automation, publication
automation, or deterministic authority for live advisory evidence.

## Summary

Current implementation already has strong v13 foundations:

- local review feedback, response text, response status, manual evidence,
  browser/dashboard evidence, accessibility evidence, lifecycle briefs, handoff
  readiness, dashboard read surfaces, TUI entry points, deterministic evals,
  and a v13 release gate exist
- response-linked fixup inventory has a runtime service, event payload,
  artifact shape, SQLite projection, query path, and status derivation
- skipped browser/dashboard and accessibility evidence can be named in
  limitations or skipped-case fields
- v13 release-gate advisory rows already keep provider, browser/dashboard, and
  accessibility evidence non-blocking

The maturity gap is mostly operator ergonomics and summary resilience:

- lifecycle brief limitations are deduplicated but not capped or summarized
  before the artifact schema enforces a 20-item maximum
- fixup inventory is an internal capability rather than an obvious CLI,
  interactive, TUI, API, and dashboard action
- browser/dashboard evidence still requires concrete viewport dimensions even
  for intentionally skipped live passes
- dashboard evidence rows show advisory posture, but not a distinct skipped or
  not-run posture
- command-guide and in-session copy cover the v13 loop, but not the full v14
  happy path for fixup inventory and skipped advisory evidence

## Classification Legend

| Disposition | Meaning |
| --- | --- |
| Fix now | Implement during v14 because the finding directly affects the maturity outcomes. |
| Document only | Improve operator docs or command examples, but do not change behavior. |
| Accepted risk | Keep current behavior for v14 with explicit bounded risk language. |
| Not v14 | Out of scope for v14 because it would expand authority, hosting, automation, or release claims. |

## Audit Entries

### Lifecycle Brief Limitation Handling

Disposition: **Fix now**

Source anchors:

- `src/glassbox/runtime/changeset_review_brief_sections.py:716` collects
  limitations from sources, inventory, verification, command evidence, review
  response blockers, manual evidence, readiness, unresolved feedback, and stale
  responses, then only deduplicates with `dict.fromkeys`.
- `src/glassbox/runtime/review_briefs.py:127` caps `non_claims`,
  `reviewer_checklist`, and `safe_inspection_commands` at 20 items.
- `src/glassbox/runtime/review_briefs.py:138` caps `limitations` at 20 items.
- `src/glassbox/runtime/changeset_review_brief_service.py:103` assembles
  limitations before creating the `ReviewBriefArtifact`, so overflow fails
  artifact validation rather than producing a reviewer-safe summary.
- `tests/unit/test_review_briefs.py` covers brief generation and advisory live
  evidence, but does not yet characterize the dogfooding overflow.

Finding:

The v13 dogfooding changeset produced 22 limitations and failed brief
generation. The current runtime deduplicates but does not group, cap, preserve
overflow count, or add summary state before the artifact model validates the
brief. This is a product maturity defect because rich retained evidence can
make the reviewer-safe summary brittle.

V14 target:

`GBX-1410` should add a deterministic characterization for more than 20
limitations. `GBX-1411` should summarize limitations before artifact
validation, preserve raw evidence in canonical events and managed artifacts,
and avoid silently dropping high-severity blockers. `GBX-1412` should surface
summary count, overflow count, and summary reason through API, dashboard, and
exports if the brief model or generated responses change.

### Response-Linked Fixup Inventory Paths

Disposition: **Fix now**

Source anchors:

- `src/glassbox/runtime/review_fixup_actions.py:44` exposes
  `ReviewFeedbackFixupInventoryService.record_workspace_inventory`, which
  derives bounded fixup inventory from the current workspace diff.
- `src/glassbox/runtime/review_fixup_actions.py:114` persists
  `ReviewFeedbackFixupInventoryAttached` events with path summaries, source
  digest, freshness, artifact id, and changed-path counts.
- `src/glassbox/runtime/review_responses.py:125` builds the bounded
  response-linked inventory artifact and names the non-claim that inventory is
  not reviewer acceptance.
- `src/glassbox/runtime/review_responses.py:189` derives response status from
  feedback, inventory records, paths, freshness, and verification ledger state.
- `src/glassbox/runtime/review_responses.py:394` blocks resolved or responded
  feedback when fixup inventory is missing, stale, failed, or stale against
  verification.
- `src/glassbox/cli/parser_changeset_feedback.py:104` exposes `feedback
  status`.
- `src/glassbox/cli/parser_changeset_feedback.py:116` exposes `feedback
  resolve`, but no `feedback fixup` or equivalent action.
- `tests/unit/test_review_responses.py` and
  `tests/integration/test_review_response_fixup_inventory.py` cover the
  internal fixup inventory and response status behavior.

Finding:

The durable model exists, but operators cannot reach it through the ordinary
terminal path discovered during dogfooding. `feedback resolve` can record
response text, and `feedback status` can report missing inventory, but there is
no first-class command that tells an operator "attach this changed-path
inventory to that feedback."

V14 target:

`GBX-1420` should publish the operator contract. `GBX-1421` should add the CLI
and plain interactive action while reusing the existing runtime service.
`GBX-1422` should add TUI, API, and dashboard parity if the dashboard needs a
mutation route. `GBX-1423` should refine response status copy and safe next
actions without implying reviewer approval.

### Skipped Browser And Dashboard Evidence

Disposition: **Fix now**

Source anchors:

- `src/glassbox/runtime/browser_evidence.py:16` models browser/dashboard
  evidence as advisory local evidence.
- `src/glassbox/runtime/browser_evidence.py:25` allows unknown browser names.
- `src/glassbox/runtime/browser_evidence.py:26` and
  `src/glassbox/runtime/browser_evidence.py:27` require positive viewport
  width and height.
- `src/glassbox/runtime/browser_evidence.py:43` allows skipped cases.
- `src/glassbox/cli/parser_changeset_evidence.py:102` defaults browser to
  `unknown`.
- `src/glassbox/cli/parser_changeset_evidence.py:103` makes `--viewport`
  required for browser and dashboard evidence.
- `src/glassbox/web/review_loop_api.py:191` mirrors the browser/dashboard API
  request shape, including required positive `viewport_width` and
  `viewport_height`.
- `src/glassbox/web/routes/changesets.py:277` attaches browser/dashboard
  evidence through the web route.

Finding:

The model can say a case was skipped, but it still requires fabricated or
irrelevant viewport dimensions for an intentionally skipped live dashboard pass.
That is the dogfooding friction: skipped evidence is legitimate, but current
request shapes make operators invent environment details when no live browser
was inspected.

V14 target:

`GBX-1430` should define an explicit skipped advisory evidence model with
unknown or not-applicable environment details. `GBX-1431` should add CLI/API
support and reject contradictory combinations such as skipped evidence with
passing console or keyboard claims. `GBX-1432` should make skipped posture
visible in dashboard, briefs, handoff, and exports.

### Skipped Accessibility Evidence

Disposition: **Fix now**

Source anchors:

- `src/glassbox/runtime/accessibility_evidence.py:31` models advisory
  accessibility observations.
- `src/glassbox/runtime/accessibility_evidence.py:35` requires an observation
  kind such as `keyboard_pass`, `screen_reader_note`, or `responsive_review`.
- `src/glassbox/runtime/accessibility_evidence.py:42` requires an observed
  issue, even when the evidence is a skipped or not-run advisory note.
- `src/glassbox/runtime/accessibility_evidence.py:47` records skipped cases.
- `src/glassbox/runtime/accessibility_evidence.py:101` keeps non-claims around
  certification, WCAG conformance, deterministic release authority, approval,
  and publication.
- `src/glassbox/cli/parser_changeset_evidence.py:166` exposes
  `changeset evidence accessibility`, including skipped-case fields.

Finding:

Accessibility evidence has strong advisory non-claims and can list skipped
cases, but the current shape is still oriented around an observation that
occurred. A deliberately not-run screen-reader or keyboard pairing should not
need a fake observed issue or a pass-like observation kind.

V14 target:

Handle browser/dashboard and accessibility skipped evidence together in
`GBX-1430` through `GBX-1432`, with explicit `not_run`, `unknown`, or
`not_applicable` posture and copy that avoids certification or conformance
claims.

### Command Discovery And In-Session Guidance

Disposition: **Fix now**

Source anchors:

- `src/glassbox/cli/command_guide_review.py:6` defines the current
  review-loop command-guide section.
- `src/glassbox/cli/command_guide_review.py:21` starts with
  `changeset show`, then verification preview, feedback status, evidence
  attach, and handoff readiness.
- `src/glassbox/cli/tui/commands.py:153` through
  `src/glassbox/cli/tui/commands.py:204` define `/review` and `/changeset`
  TUI actions for create, refresh, dashboard, brief, verification, handoff,
  and feedback status.
- `src/glassbox/cli/interactive_review_commands.py` routes the plain
  interactive `/review` and `/changeset` family to the same review actions.
- `tests/unit/test_command_guide.py`,
  `tests/integration/test_cli_tui_review_commands.py`, and
  `tests/integration/test_cli_interactive_commands.py` cover current review
  command discovery.

Finding:

The v13 review-loop path is discoverable, but the v14 happy path is not yet
complete: command guide examples do not show response-linked fixup inventory,
skipped advisory evidence, or the full inspect-before-mutate sequence from
changeset refresh to brief and handoff readiness. TUI and plain interactive
copy also need missing-evidence guidance once fixup inventory and skipped
evidence actions exist.

V14 target:

`GBX-1440` should refresh command-guide, help, and docs examples after CLI
support lands. `GBX-1441` should improve in-session guidance for missing fixup
inventory, skipped live evidence, stale verification, missing briefs, and
handoff blockers.

### Dashboard Review-Loop Surfaces

Disposition: **Fix now**

Source anchors:

- `src/glassbox/web/routes/changesets.py:221` returns feedback detail with
  response status.
- `src/glassbox/web/changeset_api_builders.py:671` builds response status
  fields for the dashboard API.
- `frontend/components/console/changeset/evidence.tsx:159` renders the manual
  evidence inbox.
- `frontend/components/console/changeset/evidence.tsx:179` counts live
  evidence.
- `frontend/components/console/changeset/evidence.tsx:202` labels
  browser/dashboard evidence as advisory and local-only.
- `frontend/components/console/changeset/evidence.tsx:209` labels
  accessibility evidence as advisory.
- `frontend/components/console/changeset/evidence.tsx:225` shows evidence
  commands, including the current required `--viewport WIDTHxHEIGHT` path.

Finding:

Dashboard copy preserves non-publication and advisory boundaries, but skipped
evidence is not visually distinct from live advisory evidence. There is also no
dashboard action path for response-linked fixup inventory yet. Existing action
states cover refresh, brief, feedback inspection, handoff inspection,
verification preview, and manual evidence attachment, but not the v14 maturity
actions.

V14 target:

`GBX-1422` should add dashboard parity for fixup inventory where a route is
needed. `GBX-1432` should surface skipped evidence distinctly. `GBX-1442`
should polish action states, deep links, error copy, responsive layout, and
keyboard behavior for the new maturity controls.

### Release-Gate Advisory Evidence Posture

Disposition: **Document only now; extend later in GBX-1461**

Source anchors:

- `scripts/v13_release_gate_helpers.py:168` records v13 browser/dashboard and
  accessibility advisory evidence.
- `scripts/v13_release_gate_helpers.py:188` writes structured advisory entries
  with status `skipped`, `blocking: False`, `freshness_status:
  not_collected`, and `required_for_release: False`.
- `docs/v13-release-gate.md` documents provider, browser/dashboard, and
  accessibility evidence as advisory by default.
- `tests/unit/test_v13_release_gate.py` asserts dry-run advisory labels and
  skipped browser/accessibility structure.

Finding:

The deterministic release boundary is already correct for v13. v14 should not
make fresh browser or accessibility evidence blocking by default. The only
change needed before late release work is documentation alignment; a v14 gate
or v13 extension can add v14 maturity checks later.

V14 target:

Keep this as document-only until `GBX-1461`, then add a v14 gate or documented
v13 extension with blocking deterministic maturity checks and advisory rows for
fresh or skipped UX evidence.

### Stale Dogfooding Provider Prefixes

Disposition: **Document only**

Source anchors:

- `docs/v13-dogfooding-summary.md` records the stale `dogfood:local` provider
  prefix failure.
- `src/glassbox/cli/command_guide_data.py` documents provider diagnostics,
  recommendations, canary evidence, and canary runs without requiring stale
  dogfooding provider names.
- `docs/providers.md` remains the provider configuration reference.

Finding:

The stale provider prefix was a dogfooding recipe problem, not a review-loop
runtime defect. v14 should clean command-guide and dogfooding examples so
operators use supported provider prefixes or deterministic local workflows.

V14 target:

`GBX-1440`, `GBX-1450`, and `GBX-1462` should avoid stale provider names in
examples and dogfooding protocols.

### Fresh Browser And Accessibility Evidence

Disposition: **Accepted risk now; fix with advisory protocol later**

Source anchors:

- `docs/browser-accessibility-evidence.md` defines the existing advisory
  browser/accessibility evidence posture.
- `scripts/v13_release_gate_helpers.py:168` records skipped advisory UX
  evidence by default in the deterministic gate.
- `frontend/e2e/v11-live-cockpit-evidence.spec.ts` and dashboard frontend
  tests provide deterministic or semi-deterministic dashboard confidence, but
  not a fresh v14 manual review pass.

Finding:

The lack of fresh live browser/accessibility evidence is an advisory confidence
gap, not a deterministic release blocker. It should be retained during v14
dogfooding if practical, but skipped evidence remains acceptable when reasons
and non-claims are explicit.

V14 target:

`GBX-1450` should define the repeatable advisory evidence protocol. `GBX-1451`
and `GBX-1452` should retain fresh evidence or an explicit bounded skip.

## Accepted Non-Goals

These are not v14 implementation targets:

- hosted review comment synchronization
- remote reviewer identity or approval state
- automatic review approval from response-linked fixup inventory
- automatic staging, commits, pushes, pull requests, merges, deploys, or
  package publication
- making live provider, browser, dashboard, accessibility, or dogfooding
  evidence deterministic release authority without a future fixture-backed
  contract
- screen-reader certification or broad WCAG conformance claims
- broad redesign of the dashboard information architecture unrelated to the
  maturity controls
- raw `.glassbox` state publication or committed local evidence directories

## Test Inventory

Current deterministic coverage relevant to the audited areas:

- `tests/unit/test_review_briefs.py`
- `tests/unit/test_review_responses.py`
- `tests/unit/test_browser_evidence.py`
- `tests/unit/test_accessibility_evidence.py`
- `tests/unit/test_manual_evidence.py`
- `tests/unit/test_command_guide.py`
- `tests/unit/test_v13_release_gate.py`
- `tests/integration/test_review_response_fixup_inventory.py`
- `tests/integration/test_cli_changeset_commands.py`
- `tests/integration/test_cli_tui_review_commands.py`
- `tests/integration/test_cli_interactive_commands.py`
- `tests/integration/test_web_changeset_routes.py`
- `frontend/tests/changeset-console.test.tsx`
- `frontend/tests/dashboard-stores.test.ts`

Coverage gaps to close during v14:

- rich lifecycle-brief limitation overflow characterization
- summarized lifecycle limitations and surfaced summary metadata
- first-class CLI/plain interactive fixup inventory action
- TUI/API/dashboard fixup inventory parity
- skipped browser/dashboard evidence without concrete viewport requirements
- skipped accessibility evidence without fake observation details
- dashboard/brief/handoff/export copy for skipped evidence posture
- command-guide and in-session missing-evidence guidance
- deterministic v14 eval cases for stable maturity behavior
- v14 release-gate dry-run summary shape

## Disposition

The v13 dogfooding findings map cleanly to the existing v14 task graph:

- `GBX-1410` through `GBX-1412`: lifecycle brief rich-evidence resilience
- `GBX-1420` through `GBX-1423`: response-linked fixup inventory operator path
- `GBX-1430` through `GBX-1432`: skipped advisory evidence UX
- `GBX-1440` through `GBX-1442`: review-loop command discovery and dashboard
  ergonomics
- `GBX-1450` through `GBX-1452`: fresh advisory browser and accessibility
  evidence protocol and retained evidence
- `GBX-1460` through `GBX-1463`: deterministic v14 evals, release gate,
  dogfooding, and release-candidate guide

No audited finding requires hosted review, automatic approval, automatic git
mutation, automatic pull request creation, publication automation, or stronger
release authority for live advisory evidence.
