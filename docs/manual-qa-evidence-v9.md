# v9 Manual QA Evidence Archive

This document defines the manual release-candidate evidence shape for v9. It
extends the v8 archive with first-run readiness, command discovery, dashboard
cockpit attention, provider freshness, promoted eval evidence, package smoke,
dogfooding disposition, and recovery cues.

## Directory Convention

Keep manual evidence in the same local release directory as the automated v9
gate summary whenever practical:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v9-gate/
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

The `.glassbox/` directory is local workspace state and ignored by git. Commit
small deterministic summaries when they help future reviewers, but do not
commit screenshots, terminal recordings, provider transcripts, private logs, or
credential-bearing command output by default.

## Manual Validation Manifest

Use this file inside the evidence directory:

```text
manual-validation.md
```

Recommended shape:

```markdown
# v9 Manual Validation

- Release candidate: <version-or-commit>
- Reviewer: <name-or-initials>
- Date: <YYYY-MM-DD>
- Automated summary: ./summary.json
- Status: passed | failed | blocked | partial

## First-Run And Terminal Checklist

- First-run readiness: passed | failed | partial | not run
- Chat startup summary: passed | failed | partial | not run
- Supported TTY: passed | failed | partial | not run
- Plain fallback: passed | failed | partial | not run
- Approvals/questions: passed | failed | partial | not run
- Cancellation: passed | failed | partial | not run
- Daemon attach: passed | failed | partial | not run
- Long output: passed | failed | partial | not run

## Dashboard Cockpit Checklist

- Workspace attention summary: passed | failed | partial | not run
- Task evidence drill-down: passed | failed | partial | not run
- Recovery cues: passed | failed | partial | not run
- Provider evidence cue: passed | failed | partial | not run
- Keyboard flow: passed | failed | partial | not run
- Mobile layout: passed | failed | partial | not run
- Branch comparison: passed | failed | partial | not run

## Recovery And Package Checklist

- Projection health: passed | failed | partial | not run
- Artifact pressure: passed | failed | partial | not run
- Daemon state: passed | failed | partial | not run
- Background jobs: passed | failed | partial | not run
- Repository index freshness: passed | failed | partial | not run
- Provider freshness: passed | failed | partial | not run
- Package build and installed smoke: passed | failed | partial | not run

## Named Accessibility Pairings

- Terminal pairing reviewed: <terminal emulator>, <OS/version>, <shell>, <size>, <keyboard>, <screen reader/accessibility tool or not run>
- Dashboard pairing reviewed: <browser/version>, <OS/version>, <viewport>, <keyboard>, <screen reader/accessibility tool or not run>
- Claims supported: <precise claims>
- Non-claims: <what was not reviewed>
- Blocking issues: <none or links>

## Release Decision Notes

- Blocking issues: <none or links>
- Accepted residual risks: <explicit list>
- Go/no-go recommendation: go | no-go | provisional go
- Follow-up tasks: <links or none>
```

## Redaction Rules

- Never store API keys, tokens, secret-like environment variables, raw
  credential-provider output, private prompts, or unredacted provider responses.
- Prefer command names, state summaries, viewport names, pairing names, and
  pass/fail notes over full logs.
- Store only the minimum command transcript needed to explain a release
  decision.
- Keep provider canary and live provider recommendation evidence advisory unless
  a documented release policy explicitly promotes it.
- Summarize large JSON outputs in committed docs and retain the JSON under
  `.glassbox/releases/...`.

## Accessibility Claims Rule

Accessibility claims must name the terminal, browser, OS, viewport or terminal
size, keyboard path, and assistive technology pairing that was actually
reviewed. If a browser, screen reader, or accessibility tool was not run, say
that directly and keep the claim limited to automated component evidence,
keyboard-path tests, semantics, and prior retained evidence.
