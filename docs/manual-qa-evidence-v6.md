# v6 Manual QA Evidence Archive

This document defines the manual release-candidate evidence shape for v6. It
extends the automated evidence format in [v6-release-evidence.md](./v6-release-evidence.md)
without turning manual QA into a heavy process that maintainers avoid.

## Directory Convention

Keep manual evidence in the same local release directory as the automated gate
summary:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v6-gate/
  summary.json
  manual-validation.md
  terminal/
  dashboard/
  recovery/
  provider-canary/
  logs/
```

The `.glassbox/` directory is local workspace state and ignored by git. Commit
small deterministic templates or summary docs when they help future reviewers,
but do not commit large screenshot archives, terminal recordings, provider
transcripts, or private logs by default.

## Retention Policy

- Keep the final release-candidate evidence directory until the next release
  line supersedes it.
- Keep failed or superseded candidate directories only while they help explain a
  release decision, then prune them locally.
- Publish binary artifacts as CI or release-review attachments when needed;
  avoid repository churn from generated images and recordings.
- Treat `summary.json` as the automated index and `manual-validation.md` as the
  human signoff index.

## Manual Validation Manifest

Use this file inside the evidence directory:

```text
manual-validation.md
```

Recommended shape:

```markdown
# v6 Manual Validation

- Release candidate: <version-or-commit>
- Reviewer: <name-or-initials>
- Date: <YYYY-MM-DD>
- Automated summary: ./summary.json
- Status: passed | failed | blocked | partial

## Terminal Review

- Evidence directory: ./terminal/
- Sizes reviewed: 120x36, 100x30, 80x24, 60x20
- Keyboard-only workflows: passed | failed | partial
- Screen-reader/accessibility notes: <claims and non-claims>
- Blocking issues: <none or links>

## Dashboard Review

- Evidence directory: ./dashboard/
- Viewports reviewed: 1440x900, 1024x768, 768x1024, 390x844
- Keyboard-only workflows: passed | failed | partial
- Semantic/landmark notes: <claims and non-claims>
- Blocking issues: <none or links>

## Recovery And Maintenance Review

- Evidence directory: ./recovery/
- Workflows reviewed: observability, projections, artifacts, backup, replay/eval,
  daemon recovery, installed dashboard smoke
- Blocking issues: <none or links>

## Provider Canary Review

- Evidence directory: ./provider-canary/
- Status: run | skipped
- Reason if skipped: <credential/policy reason>
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

## Checklist Coverage

Terminal review should cover:

- terminal sizes `120x36`, `100x30`, `80x24`, and `60x20`
- prompt submit, multiline editing, paste-like input, command palette, details
  pane, approvals, questions, cancellation, attach, reconnect, and quit
- `--plain` or redirected non-TTY fallback
- screen-reader and terminal accessibility notes with explicit claims and
  non-claims

Dashboard review should cover:

- desktop `1440x900`, narrow desktop/tablet `1024x768`, portrait tablet
  `768x1024`, and mobile `390x844`
- queue navigation, session selection, tabs, prompt, answer, approval, fork,
  compare, evidence, recovery, and degraded states
- semantic landmarks, focus order, keyboard-only paths, visible focus, and text
  wrapping

Recovery review should cover:

- `observability status`
- `projection check` and `projection rebuild`
- `artifacts inspect` and artifact prune dry-run
- backup create, inspect, and restore in a temporary workspace
- replay run and eval report
- daemon stale-owner recovery
- installed dashboard smoke

Provider-canary review should cover:

- whether live-provider canaries ran or were skipped
- which provider family was used when run
- redaction applied to prompts, responses, environment, and logs
- whether canary results stayed advisory or revealed a release blocker

## Redaction Rules

- Never store API keys, tokens, secret-like environment variables, or raw
  credential-provider output.
- Redact provider prompts and responses when they include private user,
  repository, or business content.
- Prefer event families, state transitions, command names, and pass/fail notes
  over full logs.
- Store only the minimum command transcript needed to explain a release decision.

## Relationship To Existing Artifacts

- The v4 screenshot archive remains the dashboard screenshot generator. Its
  output belongs under `frontend/test-results/` or as a linked attachment from
  `manual-validation.md`.
- The v5 terminal review checklist remains the terminal workflow baseline. v6
  adds cancellation, recovery, provider-canary, and release-evidence signoff.
- The automated v6 release gate remains the blocking command surface; manual
  evidence records the operator workflows that are still impractical to prove
  entirely through automation.
