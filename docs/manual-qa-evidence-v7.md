# v7 Manual QA Evidence Archive

This document defines the manual release-candidate evidence shape for v7. It extends the v6 archive with named accessibility pairings, onboarding/package smoke, v7 release-gate evidence, dashboard evidence cues, and provider capability review.

## Directory Convention

Keep manual evidence in the same local release directory as the automated v7 gate summary:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v7-gate/
  summary.json
  manual-validation.md
  accessibility/
  terminal/
  dashboard/
  onboarding/
  packaging/
  recovery/
  provider-canary/
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
# v7 Manual Validation

- Release candidate: <version-or-commit>
- Reviewer: <name-or-initials>
- Date: <YYYY-MM-DD>
- Automated summary: ./summary.json
- Status: passed | failed | blocked | partial

## Named Accessibility Pairings

- Evidence directory: ./accessibility/
- Terminal pairing reviewed: <terminal emulator>, <OS/version>, <shell>, <size>, <keyboard>, <screen reader/accessibility tool or not run>
- Dashboard pairing reviewed: <browser/version>, <OS/version>, <viewport>, <keyboard>, <screen reader/accessibility tool or not run>
- Claims supported: <precise claims>
- Non-claims: <what was not reviewed>
- Blocking issues: <none or links>

## Terminal Review

- Evidence directory: ./terminal/
- Workflows reviewed: long session, approvals, questions, cancellation, daemon attach, fallback/plain mode
- Keyboard-only workflows: passed | failed | partial
- Blocking issues: <none or links>

## Dashboard Review

- Evidence directory: ./dashboard/
- Workflows reviewed: long session, compare, metrics, policy evidence, provider cues, mobile, keyboard navigation
- Viewports reviewed: <list>
- Semantic/landmark notes: <claims and non-claims>
- Blocking issues: <none or links>

## Onboarding And Packaging Review

- Evidence directory: ./onboarding/ and ./packaging/
- First-run help/provider diagnostics/profile examples: passed | failed | partial
- Installed-package smoke: passed | failed | skipped
- Source-builder smoke: passed | failed | skipped
- Blocking issues: <none or links>

## Recovery And Maintenance Review

- Evidence directory: ./recovery/
- Workflows reviewed: observability, projections, artifacts, backup, daemon, eval, installed dashboard
- Blocking issues: <none or links>

## Provider Canary Review

- Evidence directory: ./provider-canary/
- Status: run | skipped
- Provider/model if run: <provider/model>
- Reason if skipped: <credential/policy reason>
- Advisory interpretation: <non-blocking unless promoted by release policy>
- Redaction note: <what was removed>

## Attachments

- Screenshots: <relative links or none>
- Terminal recordings: <relative links or none>
- Command transcripts: <relative links or none>
- Redacted logs: <relative links or none>

## Release Decision Notes

- Blocking issues: <none or links>
- Accepted residual risks: <explicit list>
- Follow-up tasks: <links or none>
```

## Redaction Rules

- Never store API keys, tokens, secret-like environment variables, raw credential-provider output, private prompts, or unredacted provider responses.
- Prefer event families, state transitions, command names, viewport names, pairing names, and pass/fail notes over full logs.
- Store only the minimum command transcript needed to explain a release decision.
- Keep provider canary evidence advisory unless a documented release policy explicitly promotes it.

## Accessibility Claims Rule

Accessibility claims must name the terminal, browser, OS, viewport or terminal size, keyboard path, and assistive technology pairing that was actually reviewed. If a screen reader or accessibility tool was not run, say that directly and keep the claim limited to keyboard, semantics, and automated evidence.
