# V13 Review-Loop UX Audit

This audit closes `GBX-1380`. It reviews the terminal chat, plain
interactive, command-palette, dashboard, feedback, evidence, lifecycle-brief,
handoff, and commit-preparation surfaces after the v13 review-loop model
landed through `GBX-1372`.

The goal is to choose the in-session review-loop vocabulary before adding TUI,
plain-mode, or dashboard shortcuts. This document does not add product
behavior by itself.

## Summary

Glassbox should use `/review` as the primary in-session review-loop command.
The command should open a review-loop namespace rather than a creation-only
shortcut:

- `/review create` should create a local changeset from the current workspace
  diff and current session by default
- `/review status` should inspect current changeset review posture
- `/review refresh` should refresh structured inventory
- `/review brief` should generate the lifecycle brief
- `/review verify` should preview verification recommendations
- `/review handoff` should inspect final handoff posture
- `/review dashboard` should open or copy the dashboard review surface

`/changeset` should remain a compatibility alias for operators who know the
CLI noun, but it should route into the same review-loop commands. The primary
palette titles should say "Review" rather than "Changeset" when the action is
about the full lifecycle.

This choice fits the v13 model better than `/changeset`, `/review-change`, or
separate `/feedback` and `/evidence` roots because v13 is no longer just
changeset creation. It includes feedback, response state, manual evidence,
browser/accessibility observations, stale verification, lifecycle briefs,
handoff readiness, and publication boundaries.

## Evidence Sources

- `src/glassbox/cli/tui/commands.py` defines the current command-palette and
  slash registry. It has dashboard, status, copy, approval, answer,
  interrupt, and view toggles, but no review-loop entry point.
- `src/glassbox/cli/tui/app.py` routes slash commands by exact alias before
  ordinary prompt submission. That makes `/review ...` feasible without
  changing model prompts or freeform chat behavior.
- `src/glassbox/cli/tui/app_commands.py` handles contextual disabled states
  and action feedback. Review actions should reuse this pattern so unavailable
  runtime, dashboard, repository, or selected changeset states are visible.
- `src/glassbox/cli/interactive_session.py` supports plain `/status`, `/help`,
  `/approve`, `/deny`, and `/exit`. It currently treats unknown slash commands
  as local errors, so plain-mode parity needs explicit parser support instead
  of relying on normal prompt submission.
- `src/glassbox/cli/parser_changesets.py` exposes the stable lower-level
  review-loop commands: `changeset create`, `show`, `refresh`,
  `verification-plan`, `brief`, `feedback`, `evidence`,
  `handoff-readiness`, and `commit-prep`.
- `frontend/components/console/changeset-console.tsx` already shows feedback,
  manual evidence, inventory, topology, verification, handoff, and commit
  preparation, with brief and refresh actions.
- `docs/review-feedback.md`, `docs/review-responses.md`,
  `docs/manual-evidence.md`, `docs/browser-accessibility-evidence.md`,
  `docs/review-briefs.md`, `docs/publication-boundary.md`, and
  `docs/commit-preparation.md` define the v13 review-loop vocabulary and
  non-claims.

## Surface Findings

### Terminal Chat

The full-screen TUI is the right primary entry point for review-loop shortcuts
because it already has the current session ID, workspace, dashboard URL, and
contextual action feedback. Today an operator must leave the chat and run
separate `glassbox changeset ...` commands, which is exactly the v13 gap.

Target behavior:

- default `/review create` to `source_kind=workspace-diff`
- default session scope to the active chat session
- print the created changeset ID, retained evidence limitations, and safe next
  inspection commands
- never auto-run tests, stage, commit, push, open pull requests, merge, deploy,
  or publish

### Command Palette

The current palette has good disabled-state ergonomics but only general
session actions. Add review actions only after each one can explain what local
state is missing.

Recommended palette actions:

- `Review: Create Changeset`
- `Review: Refresh Inventory`
- `Review: Open Dashboard`
- `Review: Generate Lifecycle Brief`
- `Review: Preview Verification`
- `Review: Inspect Handoff`
- `Review: Show Feedback Status`

Disabled reasons should name concrete inspection gaps such as "repository
unavailable", "dashboard unavailable", "no selected changeset", "runtime
historical-only", or "changeset creation needs an active workspace".

### Plain Interactive Mode

Plain mode should gain a compatible subset rather than becoming TUI-only.
Because it is used for unsupported terminals, debugging, redirected streams,
and CI-like environments, commands must print exact lower-level CLI commands
when an action cannot be completed safely inline.

Minimum parity:

- `/review create`
- `/review status CHANGESET_ID`
- `/review brief CHANGESET_ID`
- `/review verify CHANGESET_ID`
- `/review handoff CHANGESET_ID`
- `/review dashboard CHANGESET_ID`

Plain mode should keep compatibility for `/status`, `/help`, `/approve`,
`/deny`, and `/exit`.

### Dashboard Changeset Surface

The dashboard has the richest v13 read model, but it is still mostly reached
after copying a URL or navigating to `/app/changesets`. Terminal output should
hand off directly to the changeset detail route once one exists.

Dashboard quick actions should be evidence-only or read-only:

- refresh inventory
- generate lifecycle brief
- preview verification
- attach manual evidence
- inspect feedback status
- inspect handoff posture

Any action that records local evidence should show the created or updated
evidence ID. The dashboard must continue to avoid automatic staging,
committing, pushing, pull request creation, merging, deploying, or publishing.

### Feedback And Evidence Inbox

Feedback and manual evidence are mature enough for shortcuts, but creation
flows need careful language. Review feedback is not approval, and manual
evidence is not retained command proof. Shortcuts should prefer guided
prompts, forms, or exact command templates over overly terse aliases that hide
provenance.

Recommended first actions:

- show feedback status from `/review status`
- open feedback detail from dashboard
- attach manual evidence through dashboard or explicit lower-level CLI command
- defer freeform `/review note ...` until the parser can require source label,
  target kind, freshness, and local-only posture

### Lifecycle Briefs And Handoff

Lifecycle brief, handoff readiness, and commit preparation are the clearest
review-loop continuation actions. They should be surfaced together, in this
order:

1. inspect current review status
2. refresh inventory when stale
3. preview verification
4. generate lifecycle brief
5. inspect handoff readiness
6. inspect commit preparation

This preserves the publication boundary: handoff readiness and commit
preparation are advisory and do not perform final operator actions.

## Command Vocabulary Decision

Use `/review` as the primary slash command.

Rationale:

- it names the operator job instead of the storage object
- it includes feedback, evidence, verification, brief, and handoff workflows
- it leaves room for dashboard and plain-mode parity
- it avoids implying that creation is the only review-loop action
- it maps naturally to `Review:` command-palette titles

Compatibility:

- `/changeset` should remain an alias for `/review`
- lower-level `glassbox changeset ...` commands remain the scriptable API
- command help should show the lower-level CLI command behind each shortcut

Rejected primary names:

- `/changeset`: too narrow for response, evidence, handoff, and publication
  posture
- `/review-change`: too long and awkward for repeated terminal use
- `/feedback`: too narrow and would hide lifecycle brief, verification, and
  handoff actions
- `/handoff`: useful as a subcommand, but too late in the workflow to be the
  root

## Build Order

Implement the integrated UX in this order:

1. Add TUI registry IDs, slash aliases, command-palette actions, disabled
   reasons, and action feedback for review-loop commands.
2. Add the current-session default for TUI `/review create`, including
   workspace-diff source and safe post-create output.
3. Add TUI actions for refresh, lifecycle brief, verification preview, and
   handoff posture using existing changeset services.
4. Add plain interactive `/review` parsing with the same vocabulary and clear
   fallback commands.
5. Add dashboard route handoff and quick actions for the existing changeset
   review surface.
6. Update command guide, getting-started, interactive workflow, dashboard, and
   review-loop docs.
7. Promote stable behavior into deterministic v13 evals after TUI, plain, and
   dashboard parity exists.

## Non-Goals

The integrated UX must not:

- auto-run verification commands
- auto-stage files
- auto-commit
- auto-push
- auto-open pull requests
- auto-merge branches
- auto-deploy
- auto-publish packages
- imply reviewer approval
- imply publication happened

Every shortcut should either inspect state, record local evidence explicitly,
or print the exact safe next inspection command.

## GBX-1381 Target

`GBX-1381` should implement the TUI portion of this audit:

- `TerminalCommandId.REVIEW_CREATE_CHANGESET`
- `TerminalCommandId.REVIEW_REFRESH_INVENTORY`
- `TerminalCommandId.REVIEW_OPEN_DASHBOARD`
- `TerminalCommandId.REVIEW_GENERATE_BRIEF`
- `TerminalCommandId.REVIEW_PREVIEW_VERIFICATION`
- `TerminalCommandId.REVIEW_INSPECT_HANDOFF`
- `TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS`
- slash aliases rooted at `/review` with `/changeset` compatibility
- current-session defaulting for changeset creation
- post-create feedback with changeset ID, limitations, safe next actions, and
  dashboard URL when available

The implementation should continue to use lower-level changeset services as
the source of behavior, not duplicate review-loop state in terminal-only
memory.
