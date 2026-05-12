# V16 Dogfooding Summary

This document records the sanitized `GBX-1682` dogfooding pass for the v16
operator-flow milestone. The goal was to exercise the queue, evidence graph,
verification plan, changeset workup, maintenance cue, review feedback, and
reviewer-safe bundle surfaces on real local work before publishing the v16
release-candidate guide.

Retained local evidence was written under:

```text
.glassbox/releases/gbx-1682-v16-dogfooding/
```

Raw `.glassbox` state, local SQLite stores, changeset exports, and command
artifacts are intentionally local and uncommitted. Reviewer-safe outcomes,
friction findings, accepted risks, and bounded follow-ups are summarized here.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Local session seed | `uv run glassbox session run "Dogfood GBX-1682 v16 operator flow evidence" --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3 --model-name local-test-model --approval-mode review --autonomy-mode guided` | Passed | Created retained local session `0032535a-71d1-4dd6-b46b-9af802dc80ac` without live provider credentials. |
| Operator queue triage | `uv run glassbox queue list --view action-needed --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | The action-needed view was empty while the all-queue view retained four maintenance rows. This kept advisory maintenance from looking like blocking work. |
| Maintenance cue recovery | `uv run glassbox observability status --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed, degraded state retained | Surfaced stale or missing evidence for repository intelligence, provider canaries, backup posture, and artifact pressure. Safe next actions stayed inspection or rebuild oriented, including `glassbox repo index build`, `glassbox repo topology build`, `glassbox backup create`, and `glassbox artifacts prune --dry-run`. |
| Changeset workup preview | `uv run glassbox changeset workup-preview --session 0032535a-71d1-4dd6-b46b-9af802dc80ac --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Previewed the real local diff for `docs/v16-dogfooding-summary.md`; it stayed inspected-only, summary-only, and recommended docs-only validation plus a manual evidence note without staging or running commands. |
| Changeset create | `uv run glassbox changeset create --from workspace-diff --session 0032535a-71d1-4dd6-b46b-9af802dc80ac --objective "Dogfood GBX-1682 v16 operator flow evidence" --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Created local changeset `e38b433e-4e46-452c-b261-ce3061affefe`; limitations correctly named the running session and one changed path. |
| Changeset inventory refresh | `uv run glassbox changeset refresh e38b433e-4e46-452c-b261-ce3061affefe --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Created inventory artifact `6c92e3d2-6f04-4549-ad74-d4e2cbfd15d6` with fresh source digest and medium docs/missing-provenance risk. |
| Verification plan lifecycle | `uv run glassbox changeset verification-plan e38b433e-4e46-452c-b261-ce3061affefe --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed, not ready | Previewed three plan entries: two proposed docs-only checks and one manual-only advisory entry. The plan did not run commands and kept verification readiness missing until retained verification exists. |
| Changeset workup inspection | `uv run glassbox changeset workup --changeset e38b433e-4e46-452c-b261-ce3061affefe --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed, conservative | Confirmed handoff readiness stayed `needs_verification` because the workspace had untracked changes, retained docs validation was missing, no lifecycle brief existed yet, and one unresolved risk remained. |
| Evidence graph inspection | `uv run glassbox changeset evidence-graph e38b433e-4e46-452c-b261-ce3061affefe --summary --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Returned `graph:changeset:e38b433e-4e46-452c-b261-ce3061affefe` with one claim, six nodes, five edges, and no missing, stale, contradicted, manual-only, or accepted-risk claim count. |
| Review feedback fixup | `uv run glassbox changeset feedback add ...`, `uv run glassbox changeset feedback resolve ...`, and `uv run glassbox changeset feedback fixup ...` | Passed | Recorded local feedback `55125dbf-32bd-42e9-9bd4-8394229461fa`, resolved it locally with explicit residual risk, and attached fresh response-linked fixup inventory `5e57f54d-54c8-450e-9f1c-4e08c9315a28` for the sanitized summary path. |
| Reviewer-safe evidence bundle export | `uv run glassbox changeset export e38b433e-4e46-452c-b261-ce3061affefe .glassbox/releases/gbx-1682-v16-dogfooding/reviewer-safe-bundle.json --markdown-output .glassbox/releases/gbx-1682-v16-dogfooding/reviewer-safe-bundle.md --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Exported a reviewer-safe bundle and Markdown summary. `export-inspect` reported one evidence graph claim, eight evidence graph nodes, one feedback item, seven redaction reports, and non-claims for approval, publication, raw local evidence, and commit/push/PR/merge boundaries. |
| Feedback status | `uv run glassbox changeset feedback status e38b433e-4e46-452c-b261-ce3061affefe --json --cwd . --db-path .glassbox/releases/gbx-1682-v16-dogfooding/glassbox.sqlite3` | Passed | Reported one total feedback item, one responded item, zero open, zero unresolved, zero blocked, fresh fixup inventory, and no reviewer-approval claim. |
| V16 release gate dry run | `uv run python scripts/validate_v16_release_gate.py --dry-run --evidence-dir .glassbox/releases/gbx-1682-v16-dogfooding/v16-gate-dry-run` | Passed | Planned 93 blocking deterministic stages and separated advisory evidence as `skipped=1`, `recorded=2`, `planned=2`. |

## Findings

### Fix Now

- No product-code blocker was found during the dogfooding pass.
- The committed fix for this task is documentation and evidence hygiene:
  summarize the local evidence without committing raw SQLite, artifacts, or
  reviewer-safe export files, and name residual risks explicitly.

### Docs

- The dogfooding path is calmer than the earlier review-loop flow: the queue
  did not over-promote maintenance-only rows into action-needed work, and the
  workup/verification surfaces consistently said when they were preview-only.
- The summary should keep emphasizing that browser, accessibility, provider,
  dogfooding, and manual evidence are advisory unless promoted by a
  deterministic fixture or gate stage.
- The degraded maintenance state is useful release context: missing repository
  intelligence, missing backup archive, stale provider canary evidence, and
  artifact pressure all surfaced with inspection-first recovery commands.

### Tests And Evals

- Existing deterministic v16 eval fixtures already cover queue ranking,
  evidence graph support, verification plan lifecycle, skipped-check posture,
  workup preview, maintenance cues, and reviewer-safe bundles.
- The v16 gate dry run exercised the release planning path after those fixtures
  were promoted. No new eval case was needed from this pass.
- Focused docs validation remains required for this task because the changed
  path is `docs/v16-dogfooding-summary.md`.

### Accepted Risks

- Repository intelligence was intentionally missing in the isolated dogfooding
  store, which gave the pass a practical degraded-state cue. The safe next
  actions were rebuild-oriented and advisory, not release-blocking by
  themselves.
- Provider canary evidence was stale. That remains advisory and separate from
  deterministic release authority.
- Verification was not run by the workup or verification-plan commands. The
  changeset correctly stayed `needs_verification` until retained docs
  validation is available.
- Response-plan linking reported that the verification ledger was unavailable
  for the feedback response surface. The feedback fixup inventory itself was
  fresh and reviewer-safe, but not proof of verification.
- The exported reviewer-safe bundle is local evidence. It does not publish,
  stage, commit, push, open a pull request, merge, deploy, or claim reviewer
  approval.
- The pass made no staging, commit, push, pull request, merge, deploy, or
  publication claim.

### Post-V16 Follow-Ups

- Consider coalescing duplicate verification plan rows when the same command is
  recommended once by direct recipe matching and once by changeset readiness.
  The duplicate docs-only entries were clear but a little noisy.
- Consider a future deterministic fixture for response-linked verification
  ledger availability if feedback fixup plus selected verification becomes a
  supported release-candidate claim.
- Consider adding a compact maintenance recovery walkthrough to the release
  candidate guide so operators know that missing repository intelligence and
  stale provider canaries are advisory cues, not automatic blockers.

## Residual Risks

- The pass used a local test model and local SQLite store, not a live provider
  run.
- The browser and accessibility evidence remains the retained `GBX-1654`
  advisory cockpit evidence; this dogfooding pass did not run a new browser or
  assistive-technology sweep.
- The dogfooding changeset stayed intentionally unverified until focused docs
  validation runs after this summary is finalized.
- Handoff stayed not-ready because the workspace contained the in-progress
  dogfooding document and no lifecycle brief was generated.
- Local evidence can include sensitive prompts, paths, and artifacts. Only this
  sanitized summary should be committed.

## Disposition

The dogfooding pass found no v16 release blocker. It confirmed that the v16
operator flow is sharper than the older scattered review path: the queue kept
maintenance separate from action-needed work, the workup preview and
verification plan named their non-claims, the evidence graph stayed compact,
feedback fixup retained response-linked inventory without implying approval,
and reviewer-safe export preserved redaction and publication boundaries.

The remaining risks are advisory or documentation follow-ups, not blockers for
moving to the v16 release-candidate guide.
