# v8 Manual QA Evidence Archive

This document defines the manual release-candidate evidence shape for v8. It extends the v7 archive with auditable-autonomy workflows: durable task plans, autonomy budgets, background continuation, workspace memory, repository intelligence, verify-repair loops, branch search, provider recommendation, package smoke, and recovery review.

## Directory Convention

Keep manual evidence in the same local release directory as the automated v8 gate summary whenever practical:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v8-gate/
  summary.json
  manual-validation.md
  terminal/
  dashboard/
  recovery/
  packaging/
  provider-canary/
  provider-recommendation/
  accessibility/
  logs/
```

The `.glassbox/` directory is local workspace state and ignored by git. Commit small deterministic templates or summary docs when they help future reviewers, but do not commit screenshots, terminal recordings, provider transcripts, private logs, or credential-bearing command output by default.

## Manual Validation Manifest

Use this file inside the evidence directory:

```text
manual-validation.md
```

Recommended shape:

```markdown
# v8 Manual Validation

- Release candidate: <version-or-commit>
- Reviewer: <name-or-initials>
- Date: <YYYY-MM-DD>
- Automated summary: ./summary.json
- Status: passed | failed | blocked | partial

## Autonomy Workflow Checklist

- Terminal task planning: passed | failed | partial | not run
- Dashboard plan inspection: passed | failed | partial | not run
- Background continuation: passed | failed | partial | not run
- Pause/resume/cancel: passed | failed | partial | not run
- Budget exhaustion: passed | failed | partial | not run
- Memory confirmation/invalidation: passed | failed | partial | not run
- Repository index rebuild: passed | failed | partial | not run
- Verify-repair loop: passed | failed | partial | not run
- Branch-search comparison: passed | failed | partial | not run
- Provider recommendation: passed | failed | partial | not run
- Package smoke: passed | failed | partial | not run

## Named Accessibility Pairings

- Evidence directory: ./accessibility/
- Terminal pairing reviewed: <terminal emulator>, <OS/version>, <shell>, <size>, <keyboard>, <screen reader/accessibility tool or not run>
- Dashboard pairing reviewed: <browser/version>, <OS/version>, <viewport>, <keyboard>, <screen reader/accessibility tool or not run>
- Claims supported: <precise claims>
- Non-claims: <what was not reviewed>
- Blocking issues: <none or links>

## Terminal Review

- Evidence directory: ./terminal/
- Workflows reviewed: task planning, long task output, approvals/questions, cancellation, pause/resume, daemon attach, background job cues, plain fallback
- Supported TTY: passed | failed | partial | not run
- Plain fallback: passed | failed | partial | not run
- Keyboard-only workflows: passed | failed | partial | not run
- Blocking issues: <none or links>

## Dashboard Review

- Evidence directory: ./dashboard/
- Workflows reviewed: task console, plan inspector, budget controls, memory/index inspectors, branch comparison, evidence pane, mobile, keyboard
- Viewports reviewed: <list>
- Named accessibility pairings: <list>
- Semantic/landmark notes: <claims and non-claims>
- Blocking issues: <none or links>

## Recovery And Maintenance Review

- Evidence directory: ./recovery/
- Workflows reviewed: failed jobs, stale daemon, stale index, invalid memory, failed verification, projection rebuild, artifact pressure, backup/restore
- Blocking issues: <none or links>

## Provider Review

- Provider-canary evidence directory: ./provider-canary/
- Provider-recommendation evidence directory: ./provider-recommendation/
- Canary status: run | skipped
- Provider/model if run: <provider/model>
- Recommendation result: <posture and confidence>
- Reason if skipped or advisory: <credential/policy/evidence reason>
- Advisory interpretation: <non-blocking unless promoted by release policy>
- Redaction note: <what was removed>

## Package Smoke

- Evidence directory: ./packaging/
- Built package validation: passed | failed | skipped
- Installed-wheel smoke: passed | failed | skipped
- Dashboard static asset check: passed | failed | skipped
- Blocking issues: <none or links>

## Attachments

- Screenshots: <relative links or none>
- Terminal recordings: <relative links or none>
- Command transcripts: <relative links or none>
- Redacted logs: <relative links or none>

## Release Decision Notes

- Blocking issues: <none or links>
- Accepted residual risks: <explicit list>
- Go/no-go recommendation: go | no-go | provisional go
- Follow-up tasks: <links or none>
```

## Redaction Rules

- Never store API keys, tokens, secret-like environment variables, raw credential-provider output, private prompts, or unredacted provider responses.
- Prefer event families, state transitions, command names, viewport names, pairing names, and pass/fail notes over full logs.
- Store only the minimum command transcript needed to explain a release decision.
- Keep provider canary and live provider recommendation evidence advisory unless a documented release policy explicitly promotes it.
- Summarize large JSON outputs in committed docs and retain the JSON under `.glassbox/releases/...`.

## Accessibility Claims Rule

Accessibility claims must name the terminal, browser, OS, viewport or terminal size, keyboard path, and assistive technology pairing that was actually reviewed. If a screen reader or accessibility tool was not run, say that directly and keep the claim limited to keyboard, semantics, and automated evidence.
