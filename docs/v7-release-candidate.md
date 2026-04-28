# Glassbox v7 Release Candidate

This page is the operator and contributor guide for the Glassbox v7 release-candidate track. It names the supported operating model, validation path, evidence expectations, residual risks, non-goals, and current go/no-go decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v7 deepens the v6 local-first agent harness for larger and more realistic local use. The release track strengthens deterministic eval coverage, advisory provider evidence, larger-session scale checks, daemon and live-transport reliability, dashboard evidence surfaces, policy governance, accessibility review pairings, and first-run/package onboarding.

The primary product shape remains unchanged:

- terminal chat is the primary operator surface
- the dashboard is the paired inspection console
- SQLite canonical events remain the source of truth
- one local mutation owner controls a workspace at a time
- deterministic replay and eval evidence remain release authority
- provider canaries remain advisory unless a future policy promotes a specific scenario

The canonical command inventory is exposed by:

```bash
uv run glassbox command tree
```

The v7 automated release-candidate gate is:

```bash
uv run python scripts/validate_v7_release_gate.py
```

The retained evidence directory used for the current focused manual pass is:

```text
.glassbox/releases/20260428T181210Z-v7-gate/
```

That directory contains `summary.json`, `manual-validation.md`, provider-canary evidence, observability status, and projection-check output. It is local workspace state and is not committed to git.

## Supported Operating Model

- **Terminal chat**: `glassbox session chat` launches the full-screen TUI in supported interactive terminals. `--plain` remains the explicit compatibility path for unsupported terminals, redirected streams, and CI-like environments.
- **Dashboard**: `session chat` starts a co-hosted dashboard by default, while `glassbox dashboard serve` runs the standalone operator console. The v7 dashboard surfaces verification cues, policy evidence, provider capability cues, metrics, comparison, and larger-session inspection affordances.
- **Runtime ownership**: a foreground chat process or `glassbox daemon start` owns live mutation for one workspace. Local observers may attach, but concurrent mutation owners remain out of scope.
- **Live transport**: daemon-backed session attach, reconnect, event replay from cursors, and multi-observer delivery preserve persisted event authority.
- **Cancellation and operator actions**: message, answer, approve, deny, cancel, fork, resume, export, and import workflows remain explicit state-driven commands.
- **Replay and eval**: deterministic eval profiles cover release-critical v7 capabilities, including release-candidate and v7 workflow advisory profiles.
- **Provider diagnostics**: first-run diagnostics and provider canaries write redacted advisory evidence and capability rows without becoming deterministic signoff.
- **Recovery**: observability, projection, artifact, backup, daemon, eval, and installed-dashboard workflows have explicit recovery commands and retained manual evidence.
- **Package onboarding**: built wheels include static dashboard assets, v7 release docs, first-run provider diagnostics, eval profiles, and source-builder guidance.
- **Release evidence**: automated and manual evidence should live under one `.glassbox/releases/...` directory per candidate.

## Primary Operator Flows

### Start A Terminal Session

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
```

Use the dashboard URL from the TUI header or command output when you need queue triage, evidence inspection, replay/eval details, metrics, provider cues, or comparison views.

### Attach Through The Workspace Daemon

```bash
uv run glassbox daemon start --cwd .
uv run glassbox daemon status --cwd . --json
uv run glassbox session attach SESSION_ID --cwd .
uv run glassbox daemon stop --cwd .
```

Daemon ownership keeps local mutation serialized while preserving local-first runtime state.

### Resolve Paused Or Interrupted Work

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session answer SESSION_ID QUESTION_ID "answer" --cwd .
uv run glassbox session approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session deny SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session cancel SESSION_ID --reason "operator requested stop" --cwd .
```

Use `status` before mutating a session when you need the next valid operator action.

### Inspect Provider Readiness

```bash
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary run \
  --cwd . \
  --output-dir .glassbox/releases/v7-rc-candidate/provider-canary \
  --json
```

Provider evidence is useful for operational confidence, but deterministic eval and package evidence remain the release authority.

### Recover Or Audit Workspace State

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --cwd . --all
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox artifacts prune --cwd . --dry-run --json
uv run glassbox backup create .glassbox/backups/v7-candidate.zip --cwd . --json
```

Run rebuild, restore, and non-dry-run prune only after the read-only command output matches the intended recovery action.

### Verify A Release Candidate

```bash
uv run python scripts/validate_v7_release_gate.py \
  --evidence-dir .glassbox/releases/v7-rc-candidate
```

Use `--dry-run` only to preview the gate or record a planned-stage summary. A dry run is not a release pass.

Use live provider canaries only in a credentialed release environment:

```bash
uv run python scripts/validate_v7_release_gate.py \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v7-rc-candidate
```

## Release-Readiness Checklist

Before treating a build as the v7 release candidate, complete this list:

- `uv run glassbox command tree` matches the documented command surface.
- `uv run python scripts/validate_v7_release_gate.py` passes and writes `summary.json`.
- Manual validation exists in the same evidence directory as the automated summary.
- The `release-candidate` eval profile passes.
- The `v7-workflow-advisory` eval profile runs and any advisory gaps are recorded.
- Provider diagnostics and provider canaries either run with retained redacted evidence or record explicit skip reasons.
- Larger-session scale and dashboard evidence checks pass or name accepted residual risks.
- Terminal review evidence covers long sessions, approvals, questions, cancellation, daemon attach, and fallback.
- Dashboard review evidence covers larger sessions, comparison, metrics, policy evidence, provider cues, mobile, and keyboard workflows.
- Recovery review evidence covers observability, projections, artifacts, backups, daemon, eval, and installed dashboard workflows.
- Package artifacts include static dashboard assets, v7 docs, provider onboarding, eval profiles, and source-builder guidance.
- Named accessibility pairings are recorded before making stronger accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Current Evidence Summary

The current retained v7 evidence shows:

- v7 gate dry run: passed and wrote planned-stage `summary.json`
- focused terminal tests: `52 passed`
- focused dashboard evidence tests: `14` Vitest tests passed
- focused dashboard Playwright workflow: `1 passed`
- package contents validation: passed for rebuilt wheel and sdist
- compact installed-wheel onboarding/package smoke: passed for provider diagnostics and eval profile listing
- recovery smoke: observability status and projection check outputs retained
- provider canary: OpenAI `streaming-text` advisory scenario passed for `openai:gpt-5.4`; tool-call, approval, ask-user, cancellation, dashboard, and daemon-attach canaries were retained as preflight-only advisory skips
- manual validation: no blocking issue recorded in the focused GBX-784 pass

## Known Residual Risks

- The full blocking v7 gate has not yet been run in the retained evidence directory; the current automated evidence is a dry-run plan plus focused checks.
- Provider-specific remote cancellation may not stop remote computation immediately, even when local cancellation state is recorded correctly.
- Live-provider workflow canaries beyond `streaming-text` remain preflight-only advisory rows.
- Accessibility claims remain limited to the named terminal and dashboard pairings already reviewed; no broad assistive-technology certification is claimed.
- Larger-session and performance checks can vary by local machine and should be interpreted with retained command output.
- Plain fallback remains necessary for unsupported terminals, redirected streams, and CI-like environments.

## Deliberate Non-Goals

v7 does not introduce a hosted control plane, remote multi-user orchestration, cloud authority for session ownership, browser-native code editing, plugin marketplaces, remote policy enforcement, replacement of deterministic evals with live-provider canaries, or removal of the plain terminal fallback.

Multiple local observers are in scope. Multiple concurrent mutation owners are not.

## Release Decision

Decision: HOLD for v7 release candidate publication.

Decision date: 2026-04-28.

Candidate build reviewed: `c3a352e`.

Retained evidence:

```text
.glassbox/releases/20260428T181210Z-v7-gate/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v7 gate | not passed | `.glassbox/releases/20260428T181210Z-v7-gate/summary.json` is dry-run planned-stage evidence only |
| Manual validation | passed focused review | [manual-v7-release-validation.md](./manual-v7-release-validation.md) and local `manual-validation.md` |
| Provider canary policy | passed advisory run | local `provider-canary/provider-canary-summary.json` |
| Package smoke | passed focused review | [release-packaging.md](./release-packaging.md) and [manual-v7-release-validation.md](./manual-v7-release-validation.md) |
| Daemon/live transport smoke | passed focused task evidence | [v7-live-transport-contract.md](./v7-live-transport-contract.md) and v7 gate stage inventory |
| Scale smoke | passed focused task evidence | [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) and v7 performance budget gate stage |
| Accessibility review | passed named pairings with non-claims | [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md) and [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md) |
| Residual risk review | accepted for hold decision | known residual risks listed above |

No manual blocker remains open in the focused evidence. The publication blocker is procedural and objective: run the full non-dry-run `scripts/validate_v7_release_gate.py` in the release evidence directory, retain the passing `summary.json`, and update this decision from `HOLD` to `GO` only if no deterministic blocker remains open.

## Related Files

- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md)
- [v7-release-gate.md](./v7-release-gate.md)
- [manual-v7-release-validation.md](./manual-v7-release-validation.md)
- [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md)
- [release-packaging.md](./release-packaging.md)
- [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md)
- [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md)
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md)
- [v7-live-transport-contract.md](./v7-live-transport-contract.md)
- [tasks-v7.md](./tasks-v7.md)
