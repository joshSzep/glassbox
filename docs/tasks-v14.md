# Glassbox v14 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v14 task graph for maturing the v13 review loop after the first
release-candidate and post-v13 refactor passes.

## Purpose

This document defines Glassbox v14: review-loop maturity.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v13.md](./tasks-v13.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v13 milestone made local review feedback, fixup responses, manual evidence,
browser/dashboard evidence, accessibility evidence, lifecycle briefs, handoff
readiness, and in-session review entry points real product surfaces. The
post-v13 refactor then split the review-loop implementation into clearer
runtime, CLI, web, store, frontend, and release-gate owners.

The v14 goal is not to add hosted review, automatic pull requests, or a broader
publication workflow. The v14 goal is to make the existing local review loop
feel trustworthy in repeated real use: rich evidence should summarize cleanly,
response-linked fixups should be easy to record, skipped advisory evidence
should be honest without being clumsy, review-loop commands should be
discoverable from the places operators already work, and fresh advisory browser
or accessibility evidence should be practical to collect when the team wants
it.

The v14 work should optimize for seven outcomes:

- prevent rich lifecycle briefs from failing only because retained limitations
  exceed a display or artifact cap
- make response-linked fixup inventory a first-class operator path rather than
  a hidden internal capability
- let intentionally skipped browser, dashboard, and accessibility evidence
  record unknown or not-applicable environment details without inventing a live
  walkthrough
- improve command help, command-guide, TUI, plain interactive, dashboard, and
  docs copy around the review-loop happy path
- retain one fresh advisory live-browser/dashboard walkthrough and one fresh
  accessibility pairing pass without making them deterministic release
  authority
- promote only stable, deterministic review-loop maturity behavior into replay,
  eval, package, and release-gate coverage
- preserve v13's local-first, event-sourced, operator-controlled publication
  boundary

The v14 thesis is:

- v13's model is right, but the daily path needs less friction
- review-loop maturity means stronger evidence ergonomics, not stronger
  publication authority
- advisory evidence should be easier to record honestly, including skipped
  cases
- lifecycle summaries must degrade gracefully when evidence is rich
- response status should become more useful without claiming reviewer approval
- live browser and accessibility evidence can improve confidence while staying
  manual, bounded, local, and non-blocking
- every new claim should still be backed by canonical events, managed
  artifacts, typed responses, or deterministic eval fixtures

## Current Baseline Before V14 Execution

Treat the following as the starting point for every task in this document:

- [v13-release-candidate.md](./v13-release-candidate.md) records a GO decision
  for the v13 review-loop release candidate and the supported `0.10.0`
  operating model.
- [v13-dogfooding-summary.md](./v13-dogfooding-summary.md) records real-use
  friction around stale dogfooding provider prefixes, skipped browser evidence,
  lifecycle-brief limitation caps, response-linked fixup inventory discovery,
  and missing live browser/accessibility pairing evidence.
- [refactor-v13.md](./refactor-v13.md) records the completed post-v13
  review-loop refactor and the accepted product follow-up candidates that were
  intentionally not changed during refactor-only work.
- `glassbox changeset feedback resolve` records local response text, but a
  lower-friction CLI path for response-linked fixup inventory is still missing
  or too hard to discover.
- `glassbox changeset brief` can fail when rich review-loop evidence produces
  more limitations than the current artifact schema accepts.
- `glassbox changeset evidence dashboard` and related advisory evidence
  commands require concrete environment details even when the operator is
  deliberately recording a skipped or not-run case.
- The v13 release gate retains structured advisory skips for provider,
  browser/dashboard, and accessibility evidence by default.
- The dashboard and terminal review-loop surfaces exist, but real TUI and live
  browser ergonomics still need occasional manual use beside deterministic
  tests.
- Review feedback, manual evidence, browser evidence, accessibility evidence,
  lifecycle briefs, handoff readiness, and publication-boundary language remain
  local evidence surfaces, not approval or publication authority.

## V14 Review-Loop Maturity Findings

Treat these findings as evidence that should steer the first implementation
slices:

- Rich evidence should not make lifecycle brief generation brittle. When a
  changeset has many limitations or non-claims, the brief should cap,
  deduplicate, group, or summarize them before artifact validation.
- Fixup response tracking is only useful when an operator can easily attach the
  changed-path evidence that explains the response. A conservative blocked
  posture is honest, but it should tell the operator how to clear it.
- Skipped live evidence is legitimate evidence. The UX should let operators
  say "not run", "unknown viewport", or "not applicable" without fabricating a
  browser, viewport, console, keyboard, or screen-reader pass.
- Command discovery should make the review-loop happy path obvious:
  create or refresh a changeset, record feedback, attach evidence, preview
  verification, attach fixup inventory, resolve or accept risk, generate a
  brief, inspect handoff readiness.
- Fresh browser/dashboard and accessibility evidence should be retained during
  maturity dogfooding if the team wants UX confidence, but skipped evidence
  should remain acceptable for deterministic release gates.
- None of these fixes should weaken v13's non-publication boundary.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Review responses,
   response-linked fixup inventory, advisory skipped evidence, lifecycle brief
   summaries, handoff posture, and UX-triggered actions must be recorded in
   canonical events, retained artifacts, typed API responses, or explicitly
   rebuildable derived state.
3. Preserve local-first operation. Do not introduce hosted review state,
   hosted pull request authority, cloud workspace authority, remote worker
   fleets, or external service dependencies for v14 maturity.
4. Preserve one local mutation owner per workspace. Review-loop maturity may
   cite worktrees, branch candidates, manual edits, and browser observations,
   but Glassbox must still avoid simultaneous uncoordinated mutation of the
   same workspace state.
5. Preserve deterministic release blocking. Live-browser, accessibility,
   provider, manual review, and dogfooding evidence may strengthen confidence
   but must not replace deterministic replay/eval release authority unless a
   task explicitly defines a repeatable fixture-backed contract and failure
   policy.
6. Treat review feedback as evidence, not approval. A response-linked fixup
   inventory can explain what changed, but it does not prove a reviewer
   accepted the fix.
7. Do not auto-stage, auto-commit, auto-push, auto-open pull requests,
   auto-merge, auto-deploy, or auto-publish. v14 may improve safe next actions
   and handoff summaries; final mutation remains explicit operator intent.
8. Keep review-loop guidance concrete. If feedback is unresolved,
   verification is stale, evidence is manual-only, a live pass was skipped, or
   publication is not ready, terminal and dashboard surfaces should name the
   exact safe inspection or evidence command before any mutating action.
9. Keep reviewer artifacts redacted. Lifecycle briefs, evidence bundles,
   manual evidence attachments, browser evidence, accessibility evidence, and
   exports must follow existing path, secret, provider-output, artifact,
   local-state, and raw-log redaction rules.
10. Keep skipped evidence honest. Do not backfill skipped browser,
    dashboard, or accessibility evidence as passed, verified, accessible,
    certified, or deterministic proof.
11. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, TUI, web, replay,
      eval, daemon, store, policy, task, verification, provider, branch-search,
      changeset, review, manual evidence, browser evidence, accessibility
      evidence, publication-boundary, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when operator-visible behavior, release posture,
      review-loop posture, evidence posture, recovery behavior, policy
      behavior, or public workflow claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the changed behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, TUI command
  surfaces, or packaged static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- public docs are accurate against command help, API behavior, package
  contents, and release posture
- new review-loop maturity claims are backed by retained deterministic or
  manual evidence
- new guidance starts with safe inspection before mutation
- no meaningful review response, response-linked fixup inventory, manual
  evidence, browser evidence, accessibility evidence, lifecycle brief,
  handoff, or readiness state exists only in memory once a task claims
  durability
- reviewer-facing artifacts are redacted or explicitly documented as local-only
- manual evidence is labeled as manual and never backfilled as retained tool
  evidence
- browser, dashboard, accessibility, provider, and dogfooding evidence names
  bounded claims and non-claims
- skipped evidence is visible as skipped, unknown, not applicable, or not run
  rather than hidden under a passing posture
- the task does not leave placeholder code or hidden follow-up work outside
  this file

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task
IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
pyproject.toml
README.md
scripts/
src/glassbox/
src/glassbox/cli/
src/glassbox/cli/tui/
src/glassbox/core/
src/glassbox/runtime/
src/glassbox/services/
src/glassbox/store/
src/glassbox/web/
frontend/
frontend/components/console/
frontend/lib/api.ts
docs/
evals/
tests/
```

## Recommended Validation Commands

Use focused validation while implementing individual slices, then widen as the
task touches more surfaces:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest tests/unit/test_review_responses.py tests/unit/test_review_briefs.py tests/unit/test_manual_evidence.py
uv run pytest tests/integration/test_cli_changeset_commands.py tests/integration/test_web_changeset_routes.py
pnpm --dir frontend test -- changeset-console.test.tsx dashboard-stores.test.ts
```

For frontend route, generated-type, or packaged-dashboard changes:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run python scripts/validate_frontend_release_assets.py
```

For release-candidate confidence after the maturity slices land:

```bash
uv run pytest -n auto --dist loadfile
uv run pre-commit run --all-files
uv run python scripts/validate_v13_release_gate.py --dry-run
```

If v14 introduces its own release gate, add the v14 gate command here and keep
the inherited v13 gate as compatibility evidence until the new gate fully
supersedes it.

## Task Graph

---

## Phase 140: Review-Loop Maturity Contract And Dogfooding Follow-Up Map

### GBX-1400: Define The v14 Review-Loop Maturity Contract

- Status: `DONE`
- Depends on: none
- Goal: publish the operator and contributor contract for review-loop maturity
  without expanding Glassbox into approval or publication automation
- Deliverables:
  - `docs/v14-review-loop-maturity-contract.md`
  - contract sections for scope, vocabulary deltas, supported workflow set,
    evidence expectations, advisory evidence boundaries, release authority,
    safety rules, and non-goals
  - explicit mapping back to [v13-review-loop-contract.md](./v13-review-loop-contract.md)
    and [v13-dogfooding-summary.md](./v13-dogfooding-summary.md)
  - docs hub updates if v14 becomes the active planning track
- Implementation notes:
  - preserve v13 language around local evidence, non-approval, manual evidence,
    advisory browser/accessibility evidence, lifecycle briefs, handoff
    readiness, and publication boundaries
  - introduce "response-linked fixup inventory", "skipped advisory evidence",
    and "summarized lifecycle limitations" only as maturity terms, not as new
    publication authority
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - focused docs link review
- Done when:
  - contributors can read one contract and know which v13 friction points v14
    intends to mature, which claims remain bounded, and which behaviors are
    still deliberate non-goals

### GBX-1401: Audit V13 Dogfooding Findings Against Current Implementation

- Status: `DONE`
- Depends on: `GBX-1400`
- Goal: turn the accepted v13 product follow-up candidates into source-linked
  implementation targets and accepted non-goals
- Deliverables:
  - `docs/v14-review-loop-maturity-audit.md`
  - source-linked audit of lifecycle brief limitation handling, response-linked
    fixup inventory paths, skipped browser/dashboard evidence, skipped
    accessibility evidence, command discovery, dashboard review-loop surfaces,
    and release-gate advisory evidence posture
  - explicit "fix now", "document only", "accepted risk", and "not v14"
    dispositions
- Implementation notes:
  - inspect runtime, CLI, TUI, web, store, frontend, eval, and docs surfaces
    before choosing implementation slices
  - do not treat refactor-only pressure points as product defects unless the
    audit connects them to a real review-loop maturity outcome
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - targeted import or characterization tests if the audit adds guardrails
- Done when:
  - every v13 dogfooding follow-up candidate has a v14 disposition and the task
    graph below can be executed without re-litigating scope

### GBX-1402: Refresh Review-Loop Vocabulary And Safe Command Copy

- Status: `DONE`
- Depends on: `GBX-1400`, `GBX-1401`
- Goal: make the maturity language consistent across docs, CLI help, dashboard
  copy, API descriptions, tests, and eval fixtures
- Deliverables:
  - vocabulary updates in the v14 contract and affected operator docs
  - command help language that distinguishes response-linked fixup inventory
    from review approval
  - dashboard and API copy that distinguishes skipped advisory evidence from
    passed evidence
  - safe next actions that name exact inspection commands before mutation
- Implementation notes:
  - avoid "approved", "passed", "verified", "accessible", "PR-ready", or
    "published" unless retained evidence supports the exact claim
  - keep command names stable unless the audit proves a rename is worth the
    compatibility cost
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k help`
  - frontend tests when dashboard copy changes
- Done when:
  - review-loop maturity terms read consistently across terminal, dashboard,
    API, docs, and tests

---

## Phase 141: Lifecycle Brief Rich-Evidence Resilience

### GBX-1410: Characterize Lifecycle Brief Limitation Overflow

- Status: `DONE`
- Depends on: `GBX-1401`
- Goal: reproduce and lock down the rich-evidence lifecycle brief failure found
  during v13 dogfooding
- Deliverables:
  - focused unit coverage for a changeset with more retained limitations than
    the current artifact schema allows
  - integration or CLI coverage showing the current failure mode before the fix
    is applied
  - explicit expected behavior for cap, dedupe, grouping, and overflow summary
- Implementation notes:
  - prefer a deterministic fixture over large copied dogfooding state
  - keep the characterization narrow enough that the next task can change the
    behavior intentionally
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k brief`
- Done when:
  - the current brittle behavior is covered and the desired replacement
    behavior is unambiguous

### GBX-1411: Summarize Lifecycle Brief Limitations Before Artifact Validation

- Status: `DONE`
- Depends on: `GBX-1410`
- Goal: make lifecycle brief generation degrade gracefully for rich
  review-loop evidence
- Deliverables:
  - runtime helper that deduplicates, groups, caps, or summarizes limitations
    and non-claims before artifact validation
  - lifecycle brief artifact fields that retain enough overflow context for a
    reviewer without exceeding schema limits
  - CLI/API output that names when limitations were summarized
  - docs update explaining the summarization contract
- Implementation notes:
  - do not silently drop high-severity blockers
  - preserve raw retained evidence in canonical events and managed artifacts;
    this task only changes brief assembly
  - keep summary ordering deterministic so replay/eval artifacts stay stable
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k brief`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k brief`
- Done when:
  - a rich review-loop changeset can generate a reviewer-safe lifecycle brief
    and still names summarized limitations honestly

### GBX-1412: Surface Rich-Evidence Summary State In Dashboard And Exports

- Status: `DONE`
- Depends on: `GBX-1411`
- Goal: make summarized lifecycle limitations visible to dashboard and export
  consumers instead of hiding the compression behind the artifact
- Deliverables:
  - API response fields or existing model fields populated with summary count,
    overflow count, and summary reason
  - dashboard changeset detail copy for summarized limitations
  - reviewer-safe export coverage for summarized lifecycle limitations
  - generated OpenAPI and frontend API types if models change
- Implementation notes:
  - use existing changeset detail and brief sections where possible
  - avoid adding a separate dashboard card if the current changeset detail
    section can show the state clearly
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend test -- changeset-console.test.tsx generated-api-types.test.ts`
  - `pnpm --dir frontend typecheck`
- Done when:
  - an operator can see that a lifecycle brief summarized rich evidence and can
    still inspect the underlying changeset evidence

---

## Phase 142: Response-Linked Fixup Inventory Operator Path

### GBX-1420: Define Response-Linked Fixup Inventory UX Contract

- Status: `DONE`
- Depends on: `GBX-1401`, `GBX-1402`
- Goal: define the concrete operator path for attaching changed-path evidence
  to a review response
- Deliverables:
  - docs section in `docs/review-responses.md` or a v14 maturity doc
  - command contract for adding fixup inventory to one feedback record or all
    eligible feedback on a changeset
  - API and dashboard contract for inspecting response-linked inventory
  - error and safe-next-action language for stale, missing, or mismatched
    inventory
- Implementation notes:
  - prefer extending the existing `changeset feedback` family over inventing a
    separate top-level command
  - support both explicit path input and derived inventory from refreshed
    changeset evidence when safe
  - do not claim the fixup was approved
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/unit/test_command_guide.py`
- Done when:
  - the product contract answers how an operator records "this changed in
    response to that feedback" without staging or publishing anything

### GBX-1421: Add CLI And Plain Interactive Fixup Inventory Actions

- Status: `DONE`
- Depends on: `GBX-1420`
- Goal: make response-linked fixup inventory easy to record from terminal
  workflows
- Deliverables:
  - `glassbox changeset feedback fixup` or equivalent reviewed subcommand
  - JSON and human output with feedback id, changeset id, path summaries,
    stale-verification posture, safe next actions, and non-claims
  - plain interactive `/review` or `/changeset` route for the same action if
    appropriate
  - command-guide updates
- Implementation notes:
  - reuse existing review fixup inventory services and repository projections
    where possible
  - validate feedback-to-changeset ownership before recording inventory
  - keep path summaries bounded and redacted
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k feedback`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`
  - `uv run pytest tests/unit/test_command_guide.py`
- Done when:
  - an operator can attach response-linked fixup inventory without discovering
    an internal service or editing events manually

### GBX-1422: Add TUI And Dashboard Fixup Inventory Parity

- Status: `DONE`
- Depends on: `GBX-1421`
- Goal: expose the same response-linked fixup inventory path in the paired
  operator surfaces
- Deliverables:
  - TUI command-palette action or review command entry point
  - dashboard action or detail affordance for feedback records that need fixup
    inventory
  - API route support if the CLI-only path does not already cover dashboard
    mutations
  - frontend state, action status, and error handling
- Implementation notes:
  - keep dashboard actions explicit and inspect-first
  - do not hide unresolved feedback after attaching inventory unless response
    status derivation says it is resolved or accepted with risk
  - preserve route deep links for the feedback detail
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py -k review`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k feedback`
  - `pnpm --dir frontend test -- changeset-console.test.tsx dashboard-stores.test.ts`
  - `pnpm --dir frontend typecheck`
- Done when:
  - terminal, TUI, API, and dashboard surfaces agree on how response-linked
    fixup inventory is recorded and inspected

### GBX-1423: Improve Response Status With Fixup Inventory Evidence

- Status: `DONE`
- Depends on: `GBX-1422`
- Goal: make feedback response status more useful once response-linked fixup
  inventory exists
- Deliverables:
  - response-status derivation that distinguishes missing inventory, stale
    inventory, attached inventory with stale verification, accepted risk, and
    ready-for-handoff posture
  - CLI/API/dashboard copy for each state
  - stale-verification recommendations connected to changed paths
  - deterministic tests for reopened and accepted-risk edge cases
- Implementation notes:
  - keep conservative posture when inventory is missing or stale
  - a resolved feedback record with fixup inventory is still not approval
  - safe next actions should name verification and handoff inspection commands
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py`
  - `uv run pytest tests/integration/test_review_response_fixup_inventory.py`
  - frontend tests when status copy or dashboard state changes
- Done when:
  - `feedback status` explains what changed, what remains stale, and what safe
    command should run next

---

## Phase 143: Skipped Advisory Evidence UX

### GBX-1430: Define Skipped Browser, Dashboard, And Accessibility Evidence Model

- Status: `DONE`
- Depends on: `GBX-1401`, `GBX-1402`
- Goal: make intentionally skipped advisory evidence a first-class, bounded
  local evidence shape
- Deliverables:
  - model and docs contract for `not_run`, `unknown`, or `not_applicable`
    environment details
  - redaction and validation rules for skipped evidence
  - API and CLI request-shape decisions for viewport, browser, console,
    keyboard, screen-reader, and responsive fields
  - non-claims for skipped evidence
- Implementation notes:
  - prefer extending manual evidence artifact payloads without breaking
    existing records
  - keep skipped evidence distinct from failed evidence and passed evidence
  - do not require fake viewport dimensions for intentionally skipped browser
    work
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_browser_evidence.py tests/unit/test_accessibility_evidence.py`
  - `uv run pytest tests/unit/test_manual_evidence.py`
- Done when:
  - the evidence model can represent "we intentionally did not run this live
    pass" without pretending to have observed a browser or assistive technology

### GBX-1431: Add Skipped Evidence CLI And API Support

- Status: `TODO`
- Depends on: `GBX-1430`
- Goal: let operators record skipped advisory evidence without awkward
  placeholder values
- Deliverables:
  - CLI flags for skipped or unknown browser/dashboard/accessibility evidence
  - API request fields for skipped evidence posture
  - validation that rejects contradictory combinations such as `--skipped` plus
    passing console or keyboard claims
  - JSON output that names skipped cases, limitations, non-claims, and safe next
    actions
- Implementation notes:
  - preserve compatibility for existing `WIDTHxHEIGHT` viewport input
  - make unknown/skipped state explicit in artifacts and projections
  - ensure generated API types refresh if web models change
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k evidence`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k evidence`
  - `uv run pytest tests/unit/test_manual_evidence.py`
- Done when:
  - the dogfooding skipped-dashboard case can be recorded without a fabricated
    viewport while still producing honest evidence

### GBX-1432: Surface Skipped Evidence Clearly In Dashboard, Briefs, And Handoff

- Status: `TODO`
- Depends on: `GBX-1431`
- Goal: make skipped advisory evidence visible wherever review-loop evidence is
  summarized
- Deliverables:
  - dashboard evidence rows that show skipped/not-run posture distinctly
  - lifecycle brief sections for skipped browser/dashboard/accessibility cases
  - handoff readiness signals that separate skipped evidence from blockers and
    deterministic verification gaps
  - reviewer-safe export representation for skipped evidence
- Implementation notes:
  - skipped evidence may be a limitation, not necessarily a blocker
  - avoid visual or textual treatment that reads as a pass
  - keep advisory evidence beside deterministic verification posture
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend test -- changeset-console.test.tsx verification-cues.test.ts`
- Done when:
  - a reviewer can tell which live evidence was skipped, why it was skipped,
    and which claims remain unmade

---

## Phase 144: Review-Loop Command Discovery And Operator Ergonomics

### GBX-1440: Refresh Command Guide Around The Review-Loop Happy Path

- Status: `TODO`
- Depends on: `GBX-1421`, `GBX-1431`
- Goal: make the ordinary review-loop sequence discoverable from
  `glassbox command guide`, command help, and docs
- Deliverables:
  - command-guide section for review-loop maturity
  - examples for create/refresh, feedback add, evidence attach, verification
    preview, fixup inventory, feedback resolve or accept-risk, brief, and
    handoff-readiness
  - stale provider-prefix dogfooding recipe cleanup
  - docs updates for `review-feedback.md`, `review-responses.md`,
    `manual-evidence.md`, `browser-accessibility-evidence.md`, and
    `daily-workflow-quickstart.md` as needed
- Implementation notes:
  - examples should avoid stale provider prefixes and absolute local paths
  - command guide should start with safe inspection before any mutating command
  - keep advanced flows available without making the happy path noisy
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run glassbox command guide`
- Done when:
  - an operator can find the review-loop maturity path without reading the
    implementation or copying old dogfooding commands

### GBX-1441: Improve In-Session Review Guidance For Missing Evidence

- Status: `TODO`
- Depends on: `GBX-1423`, `GBX-1432`, `GBX-1440`
- Goal: make `/review`, `/changeset`, TUI palette actions, and plain
  interactive mode explain missing evidence and safe next actions directly
- Deliverables:
  - in-session guidance for missing fixup inventory, skipped live evidence,
    stale verification, missing brief, and handoff blockers
  - TUI command-palette copy and command result formatting updates
  - plain interactive routing and output parity
  - focused tests for review command flows
- Implementation notes:
  - avoid modal flows that require hidden state
  - prefer short, exact next commands over prose-only guidance
  - preserve terminal-first operation for non-dashboard users
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py -k review`
  - `uv run pytest tests/unit/test_cli_tui_commands.py`
- Done when:
  - in-session review surfaces tell operators what is missing and how to record
    it without leaving the conversation flow unnecessarily

### GBX-1442: Polish Dashboard Review-Loop Action States

- Status: `TODO`
- Depends on: `GBX-1422`, `GBX-1432`
- Goal: make dashboard review-loop actions feel complete and understandable
  under pending, success, failed, skipped, stale, and blocked states
- Deliverables:
  - dashboard changeset feedback/evidence action states for fixup inventory and
    skipped evidence
  - route state and deep-link behavior for selected feedback and evidence
  - toast or inline error copy that preserves non-claims
  - responsive and keyboard checks for the changed controls
- Implementation notes:
  - keep the dashboard dense and operator-focused
  - do not add marketing-style explanation panels
  - use existing console design system and avoid nested cards
- Tests and validation included in task:
  - `pnpm --dir frontend test -- changeset-console.test.tsx operator-actions.component.test.tsx`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - targeted Playwright or screenshot evidence if layout changes are material
- Done when:
  - dashboard review-loop actions show accurate state, recover gracefully on
    errors, and remain usable at desktop and mobile operator widths

---

## Phase 145: Fresh Advisory Browser And Accessibility Evidence

### GBX-1450: Define A Repeatable Advisory Evidence Protocol For V14

- Status: `TODO`
- Depends on: `GBX-1432`, `GBX-1442`
- Goal: define how v14 collects fresh live browser/dashboard and accessibility
  evidence without making it blocking release authority
- Deliverables:
  - `docs/v14-advisory-review-evidence.md`
  - scenario list for dashboard changeset detail, feedback status, skipped
    evidence display, fixup inventory action state, and handoff readiness
  - browser, viewport, keyboard, responsive, console, and accessibility pairing
    fields
  - skipped-case and non-claim template
  - retained-evidence directory convention under `.glassbox/releases/`
- Implementation notes:
  - keep manual and live evidence clearly advisory
  - name which checks are not screen-reader certification or WCAG conformance
  - design the protocol so it can be run manually even if Playwright is not
    available
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - docs link review
- Done when:
  - a reviewer can run the advisory UX evidence pass and know exactly what
    claims it does and does not make

### GBX-1451: Run Fresh Dashboard Browser Walkthrough Evidence

- Status: `TODO`
- Depends on: `GBX-1450`
- Goal: retain one fresh advisory browser/dashboard walkthrough for the
  matured review-loop surfaces
- Deliverables:
  - local retained evidence under `.glassbox/releases/`
  - sanitized summary in a docs file or v14 dogfooding summary
  - browser/dashboard evidence records attached to a dogfooding changeset when
    practical
  - skipped-case notes for anything not covered
- Implementation notes:
  - use production build or a stable local server path when practical
  - record browser, viewport, route, console status, observed issue, and
    limitations
  - do not expand the claim beyond what was actually inspected
- Tests and validation included in task:
  - `pnpm --dir frontend build`
  - targeted Playwright or manual browser evidence per the v14 protocol
  - focused frontend tests for changed dashboard surfaces
- Done when:
  - the v14 maturity work has fresh advisory dashboard evidence or an explicit
    retained skip with bounded reasons

### GBX-1452: Run Fresh Accessibility Pairing Evidence

- Status: `TODO`
- Depends on: `GBX-1450`
- Goal: retain one fresh advisory accessibility pairing pass for the matured
  review-loop surfaces
- Deliverables:
  - local retained evidence under `.glassbox/releases/`
  - sanitized summary covering keyboard, focus, responsive layout, contrast or
    screen-reader pairing when performed, skipped checks, and limitations
  - accessibility evidence records attached to a dogfooding changeset when
    practical
- Implementation notes:
  - do not claim certification, full accessibility, or WCAG conformance
  - record skipped assistive-technology checks explicitly
  - file follow-up tasks for any material usability issue instead of hiding it
    in advisory evidence
- Tests and validation included in task:
  - `pnpm --dir frontend test -- changeset-console.test.tsx`
  - manual or paired accessibility evidence per the v14 protocol
- Done when:
  - the v14 maturity work has fresh advisory accessibility evidence or an
    explicit retained skip with bounded reasons

---

## Phase 146: V14 Eval, Gate, Dogfooding, And Release Signoff

### GBX-1460: Add Deterministic V14 Review-Loop Maturity Eval Cases

- Status: `TODO`
- Depends on: `GBX-1412`, `GBX-1423`, `GBX-1432`, `GBX-1441`
- Goal: promote stable review-loop maturity behavior into replay/eval coverage
  without making live advisory evidence blocking
- Deliverables:
  - eval cases for lifecycle brief rich-evidence summarization,
    response-linked fixup inventory, and skipped advisory evidence posture
  - coverage manifest updates for v14 maturity capabilities
  - profile updates if release-candidate coverage should select the new cases
  - baseline review artifacts for any intentional drift
- Implementation notes:
  - keep cases compact and deterministic
  - do not encode live browser or accessibility observations as deterministic
    pass/fail unless a narrow fixture-backed contract is explicitly created
  - map each case to a named capability in `evals/coverage.json`
- Tests and validation included in task:
  - `uv run glassbox eval case list`
  - `uv run glassbox eval run --profile release-candidate`
  - `uv run glassbox eval audit --profile release-candidate --cwd .`
  - `uv run pytest tests/unit/test_runtime_eval_coverage.py`
- Done when:
  - deterministic eval coverage protects the maturity behaviors that are stable
    enough to block a release

### GBX-1461: Add A V14 Release Gate Or V13 Gate Extension

- Status: `TODO`
- Depends on: `GBX-1460`
- Goal: collect v14 maturity evidence in an automated gate while preserving
  advisory evidence boundaries
- Deliverables:
  - `scripts/validate_v14_release_gate.py` or a documented v13 gate extension
  - blocking stages for deterministic v14 evals, focused CLI/API/frontend
    tests, generated types, package contents, and installed smoke if package
    expectations change
  - advisory rows for fresh browser/dashboard and accessibility evidence
  - summary JSON with blocking and advisory sections
  - tests for dry-run output and summary shape
- Implementation notes:
  - keep live browser/accessibility evidence optional and advisory unless a
    deterministic fixture-backed contract is promoted
  - avoid duplicating all inherited v13 helper logic if a small helper layer can
    compose the old gate safely
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_v14_release_gate.py`
  - `uv run python scripts/validate_v14_release_gate.py --dry-run`
  - package-content tests if new scripts or docs must ship
- Done when:
  - release reviewers can run one command that reports v14 maturity evidence
    without confusing advisory UX evidence with release authority

### GBX-1462: Run V14 Review-Loop Maturity Dogfooding

- Status: `TODO`
- Depends on: `GBX-1461`
- Goal: use the matured review-loop path on real local work and record friction
  before release signoff
- Deliverables:
  - retained local evidence under `.glassbox/releases/`
  - `docs/v14-dogfooding-summary.md`
  - dogfooding passes for lifecycle brief rich evidence, response-linked fixup
    inventory, skipped advisory evidence, dashboard action states, handoff
    readiness, and command discovery
  - dispositions for fixes, docs, tests/evals, accepted risks, and post-v14
    follow-ups
- Implementation notes:
  - dogfood with current supported provider prefixes or local deterministic
    model names only
  - do not expand scope during dogfooding; file follow-up tasks instead
  - keep raw `.glassbox` state local and summarize only reviewer-safe evidence
- Tests and validation included in task:
  - focused tests for any dogfooding fix
  - v14 release gate dry run after dogfooding fixes
  - docs validation for the summary
- Done when:
  - v14 maturity has been exercised against realistic review-loop work and the
    findings are triaged

### GBX-1463: Publish V14 Review-Loop Maturity Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1462`
- Goal: publish the operator-facing v14 maturity guide and final milestone
  decision
- Deliverables:
  - `docs/v14-release-candidate.md`
  - guide covering supported operating model, validation path, evidence
    expectations, advisory evidence, residual risks, deliberate non-goals,
    release decision, and related files
  - docs hub and root README updates if v14 becomes the active implementation
    track
  - retained release evidence under `.glassbox/releases/`
- Implementation notes:
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming review approval, publication readiness, provider
    reliability, accessibility coverage, browser evidence, automatic git
    mutation, or automatic PR behavior
  - keep package version policy aligned with
    [version-release-policy.md](./version-release-policy.md)
- Tests and validation included in task:
  - `uv run python scripts/validate_v14_release_gate.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - final docs link review
  - package contents validation if release docs are packaged
- Done when:
  - the v14 release candidate has a coherent guide, retained evidence,
    accepted residual-risk list, and explicit GO/NO-GO decision

## V14 Release-Candidate Readiness Checklist

Before treating a build as the v14 release candidate, complete this list:

- The v14 review-loop maturity contract and audit are published and linked
  from the docs hub.
- Lifecycle briefs summarize rich limitations deterministically without
  artifact validation failures.
- Response-linked fixup inventory can be recorded from CLI, plain interactive,
  TUI, API, and dashboard surfaces where applicable.
- Feedback response status explains missing, stale, attached, accepted-risk,
  and ready-for-handoff fixup evidence without implying approval.
- Skipped browser, dashboard, and accessibility evidence can be recorded
  honestly without fabricated environment details.
- Dashboard, brief, export, and handoff surfaces show skipped evidence as
  skipped rather than passed.
- Command guide, help text, and workflow docs show the review-loop happy path.
- Fresh advisory dashboard browser evidence is retained or explicitly skipped
  with bounded reasons.
- Fresh advisory accessibility pairing evidence is retained or explicitly
  skipped with bounded reasons.
- Deterministic v14 eval cases and coverage mappings pass in the selected
  release-candidate profile.
- The v14 release gate, or documented v13 gate extension, passes and writes
  retained `summary.json` with blocking and advisory sections.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v14 follow-ups.
- Raw `.glassbox` state is not committed; reviewer-safe lifecycle summaries are
  used for handoff and release review.

## Deliberate V14 Non-Goals

v14 deliberately does not introduce:

- hosted code review
- hosted review comment synchronization
- cloud workspace authority
- remote worker fleets
- simultaneous multi-writer mutation
- automatic review approval
- automatic staging
- automatic commits
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic rebase, force-push, or history rewriting
- automatic deploys or package publishing
- automatic provider failover as release authority
- accessibility certification or broad WCAG conformance claims
- turning skipped browser or accessibility evidence into passing evidence
- hidden provider-side memory
- cross-repository memory sync
- indefinite unattended autonomy

These may be revisited in future milestones only with a new product contract,
safety model, evidence policy, remote-collaboration model, and explicit
operator semantics.
