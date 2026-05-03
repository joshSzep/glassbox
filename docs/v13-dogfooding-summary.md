# V13 Dogfooding Summary

This document records the sanitized `GBX-1392` dogfooding pass for the v13
review-loop milestone. The goal was to use the new local review feedback,
manual evidence, advisory browser/accessibility evidence, lifecycle brief,
handoff readiness, and in-session review-loop surfaces on ordinary local work
before publishing the v13 release-candidate guide.

Retained local evidence was written under:

```text
.glassbox/releases/gbx-1392-dogfooding/
```

The evidence directory is intentionally local and uncommitted. Sanitized
results and friction findings are recorded here for review.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Dogfooding session seed | `uv run glassbox session run "Dogfood v13 review-loop evidence for GBX-1392" --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3 --model-name dogfood:local --approval-mode review --autonomy-mode guided` | Failed after retained session creation | Created session `7bd2ad7c-109c-449e-aabe-87af7b44850f`, then failed because `dogfood:local` is no longer an accepted provider prefix. This is useful friction for stale dogfooding commands. |
| Changeset from workspace diff | `uv run glassbox changeset create --from workspace-diff --session 7bd2ad7c-109c-449e-aabe-87af7b44850f --objective "Dogfood GBX-1392 v13 review-loop evidence" --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed with limitation | Created changeset `49519d64-a856-44f0-8dfd-5501fc9b784c`; the initial inventory honestly said the workspace had no local git diff because this summary had not been created yet. |
| Review feedback creation | `uv run glassbox changeset feedback add 49519d64-a856-44f0-8dfd-5501fc9b784c --kind requested_change --summary "Document dogfooding provider-prefix friction and empty initial diff" ... --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed | Created feedback `11780dcf-5f5e-44e2-b455-78e7821736b9` scoped to this summary. Output included non-claims that feedback is local evidence, not approval, and no git/publication action was performed. |
| Manual evidence redaction | `uv run glassbox changeset evidence attach ... --command "uv run python scripts/validate_v13_release_gate.py --dry-run --include-provider-canaries --evidence-dir /private/tmp/..." --json` | Rejected as designed | Evidence `87ef27d9-6091-493d-9017-cfef1a14e27b` was rejected for `absolute-path`, which kept raw local temp paths out of reviewer evidence. |
| Sanitized manual evidence | `uv run glassbox changeset evidence attach ... --command "uv run python scripts/validate_v13_release_gate.py --dry-run --include-provider-canaries --evidence-dir <local-temp-v13-gate-dry-run>" --json` | Passed | Attached evidence `f08126d7-4243-4285-957f-61fe0728e027` as external-check evidence with summary-first local provenance and explicit non-claims. |
| Dashboard advisory evidence | `uv run glassbox changeset evidence dashboard 49519d64-a856-44f0-8dfd-5501fc9b784c --route /app/changesets/49519d64-a856-44f0-8dfd-5501fc9b784c --viewport 1440x900 --console-not-checked ... --json` | Passed after correction | First attempt rejected `--viewport "not captured"` because the parser requires `WIDTHxHEIGHT`. Corrected evidence `a7262ed3-2b81-4f93-9c5d-d6ffb011b6a1` retained the skipped live-browser limitation. |
| Accessibility advisory evidence | `uv run glassbox changeset evidence accessibility 49519d64-a856-44f0-8dfd-5501fc9b784c --kind responsive_review --summary "accessibility pairing was documented as advisory and skipped" ... --json` | Passed | Attached evidence `6f0c86e4-e5c0-4831-9492-dde598dbd388` with `needs_follow_up`, not certification, not WCAG conformance, and not deterministic release authority. |
| In-session review-loop command coverage | `uv run pytest tests/unit/test_cli_interactive_session.py tests/integration/test_cli_tui_review_commands.py tests/integration/test_cli_interactive_commands.py -k review` | `7 passed` | This exercised the plain interactive and TUI review entry points added late in v13. No live full-screen TUI session was used in this dogfooding pass. |
| v13 release-gate dry run | `uv run python scripts/validate_v13_release_gate.py --dry-run --include-provider-canaries --evidence-dir <local-temp-v13-gate-dry-run>` | Passed | Dry-run output explained 62 planned blocking stages and advisory provider, browser, and accessibility evidence without running live providers or browser tooling. |
| Inventory refresh after summary creation | `uv run glassbox changeset refresh 49519d64-a856-44f0-8dfd-5501fc9b784c --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed | Refreshed inventory artifact `1ccd6fb8-c96f-4c60-b619-3cd8edafab43` and detected `docs/v13-dogfooding-summary.md` with medium docs/missing-provenance risk. |
| Feedback status before response | `uv run glassbox changeset feedback status 49519d64-a856-44f0-8dfd-5501fc9b784c --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed | Reported 1 open feedback item in `planned` state with missing response-linked fixup inventory. |
| Manual evidence list | `uv run glassbox changeset evidence list --changeset 49519d64-a856-44f0-8dfd-5501fc9b784c --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed | Listed 3 attached manual evidence items: external check, browser observation, and accessibility note. The rejected evidence remained excluded from the default list. |
| Verification preview | `uv run glassbox changeset verification-plan 49519d64-a856-44f0-8dfd-5501fc9b784c --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed | Recommended `release-candidate` eval coverage and docs-only contributor checks. Review-loop summary counted 1 feedback item, 4 manual evidence records including one rejected record, 1 browser item, 1 accessibility item, and missing response verification. |
| Lifecycle brief generation | `uv run glassbox changeset brief 49519d64-a856-44f0-8dfd-5501fc9b784c --format markdown --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Failed | Review brief artifact validation rejected 22 limitations because the schema allows at most 20. Retrying after feedback resolution produced the same failure. |
| Handoff readiness | `uv run glassbox changeset handoff-readiness 49519d64-a856-44f0-8dfd-5501fc9b784c --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed, not ready | Reported `needs_review_response`, untracked workspace, missing verification, missing lifecycle brief, unresolved risk, advisory manual evidence, and explicit non-publication claims. |
| Feedback response | `uv run glassbox changeset feedback resolve 11780dcf-5f5e-44e2-b455-78e7821736b9 --summary "Dogfooding summary now records provider-prefix, redaction, dashboard viewport, lifecycle brief, and handoff findings." --residual-risk "No response-linked fixup inventory CLI was available during this pass, so feedback status remains conservative." --json --cwd . --db-path .glassbox/releases/gbx-1392-dogfooding/glassbox.sqlite3` | Passed, conservative | Feedback disposition moved to `resolved_locally`, but response status remained blocked because no response-linked fixup inventory was attached. |
| Docs-only validation | `uv run pytest tests/unit/test_release_candidate_docs.py -q` | `57 passed` | Ran the docs validation recommended by the verification preview after adding this summary. |

## Findings

### Session Seed

- The stale `dogfood:local` provider prefix created a retained session but then
  failed the turn. The error message was clear and suggested supported provider
  prefixes, but the dogfooding recipe should avoid that prefix in future passes.
- Changeset creation could still use the retained failed session as local
  provenance, which was useful for continuing the pass without provider
  credentials.

### Review Feedback

- `changeset feedback add` created a scoped requested-change record with
  source, reviewer label, body, safe next actions, and non-claims.
- The output correctly distinguished local response tracking from review
  approval and from any git/publication behavior.

### Manual Evidence

- Absolute-path redaction worked: the first external-check evidence attachment
  was rejected before it could become reviewer evidence.
- The sanitized rerun accepted placeholder path language and retained the
  evidence as summary-first local provenance.
- The manual evidence output repeatedly reminded the operator that manual
  evidence is not retained command evidence or deterministic verification proof.

### Browser And Dashboard Evidence

- Dashboard evidence accepted a skipped live-browser case with explicit
  limitations and non-claims.
- The parser currently requires a concrete `WIDTHxHEIGHT` viewport even when a
  pass is explicitly skipped. That is safe, but it makes skipped live evidence a
  little clumsy to record.
- No browser was opened during this pass. Dashboard confidence remains
  deterministic frontend/release-gate evidence plus advisory skipped evidence.

### Accessibility Evidence

- Accessibility evidence captured `needs_follow_up` and made non-certification
  language explicit.
- No keyboard, responsive browser, or screen-reader pairing was run. This is an
  advisory gap to consider during release-candidate review, not a deterministic
  release blocker.

### Lifecycle, Verification, And Handoff

- Refresh after creating this summary correctly turned the changeset into a
  one-path docs changeset with medium risk from docs and missing provenance.
- Verification preview gave useful safe next actions and separated manual,
  browser, and accessibility evidence from retained verification proof.
- Lifecycle brief generation currently fails when review-loop limitations exceed
  the artifact schema cap of 20 items. The dogfooding changeset produced 22.
  This is a follow-up candidate, not something to fix inside the dogfooding
  slice.
- Handoff readiness stayed honest: even after local feedback resolution, it
  remained blocked by the untracked workspace, missing verification, missing
  lifecycle brief, unresolved risk, and missing response-linked fixup inventory.
- `feedback resolve` records response text, but this pass did not expose a CLI
  command for attaching response-linked fixup inventory. Feedback status
  therefore remained conservative and reported the response as blocked.

### In-Session UX

- Focused plain interactive and TUI review command tests passed and remain the
  deterministic coverage for `/review`, `/changeset`, and command-palette
  review-loop entry points.
- This dogfooding pass did not drive a live full-screen terminal session. The
  retained finding is that deterministic coverage is good, but real TUI
  ergonomics still need occasional manual use.

### Publication Boundary

- Every review-loop command used in this pass preserved the non-publication
  boundary: no staging, commit, push, pull request, merge, deploy, or publication
  action was taken.
- Handoff and release-gate language stayed advisory and inspection-first.

## Disposition

The dogfooding pass found no v13 release blocker. It found these follow-up
candidates:

- update future dogfooding recipes to avoid the stale `dogfood:local` provider
  prefix
- consider allowing an explicit skipped/unknown viewport mode for dashboard
  evidence that intentionally did not open a browser
- cap, deduplicate, or summarize lifecycle-brief limitations before artifact
  validation so rich review-loop evidence does not exceed the 20-item schema
  limit
- expose or document a CLI path for response-linked fixup inventory so
  `feedback resolve` can be paired with concrete changed-path evidence
- run a live browser and accessibility pairing pass during release-candidate
  review if the team wants fresh advisory UX evidence beside deterministic
  release authority

The remaining observations are bounded evidence limits:

- a failed retained session can still seed changeset provenance, but it should
  be described honestly
- manual evidence is useful only when source labels, redaction posture,
  limitations, freshness, and non-claims are preserved
- skipped browser and accessibility evidence is not a substitute for live review
- deterministic evals, package checks, command coverage, and the v13 release
  gate remain the release authority
