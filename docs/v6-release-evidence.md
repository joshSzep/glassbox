# v6 Release Evidence Artifacts

This document defines the retained local evidence shape for the v6 release gate and manual release-candidate signoff. It supports `GBX-643` in [tasks-v6.md](./tasks-v6.md).

The goal is simple: after a gate run or manual signoff pass, a maintainer should be able to inspect one local directory and understand what ran, what passed, what failed, what was skipped, and what still needs human review.

## Evidence Directory

The default automated evidence directory is:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v6-gate/
```

The v6 gate also accepts an explicit directory:

```bash
uv run python scripts/validate_v6_release_gate.py --evidence-dir .glassbox/releases/manual-v6-check
```

The directory is local workspace state. Do not use it for secrets, unredacted provider responses, or permanent cloud storage.

## Automated Summary

Every v6 gate run writes:

```text
summary.json
```

The summary schema is versioned. Version 1 contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | Evidence schema version. |
| `gate` | Gate identifier, currently `v6-release`. |
| `status` | `dry_run`, `running`, `passed`, or `failed`. |
| `started_at` | ISO timestamp for the gate start. |
| `ended_at` | ISO timestamp for the gate end. |
| `evidence_dir` | Directory where the summary was written. |
| `command` | Command used to start the script. |
| `environment` | Workspace path, Python version, and platform. |
| `options` | Gate options such as dry-run and provider-canary inclusion. |
| `stages` | Ordered stage records. |
| `advisory` | Advisory checks that ran, failed, or were skipped without blocking by default. |
| `artifacts` | Pointers to related local artifacts such as `dist/`, eval summaries, wheel path, and manual evidence notes. |
| `next_actions` | Human-readable next actions after the run. |

Each stage record contains:

| Field | Meaning |
| --- | --- |
| `label` | Human-readable stage name. |
| `command` | Command tokens for the stage. |
| `status` | `planned`, `passed`, or `failed`. |
| `exit_code` | Process exit code, or `null` for dry-run planned stages. |
| `started_at` | ISO timestamp for stage start, or `null` for dry-run planned stages. |
| `ended_at` | ISO timestamp for stage end, or `null` for dry-run planned stages. |

## Related Artifact Pointers

The summary should point to local artifacts rather than embedding large outputs.

Use these conventions:

- package artifacts remain under `dist/`
- eval summaries remain under `.glassbox/evals/`
- frontend Playwright and screenshot artifacts remain under `frontend/test-results/`
- daemon owner logs remain under `.glassbox/runtime-owner.*.log`
- manual validation notes live under the same release evidence directory using the manifest in [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md)

## Manual Evidence Manifest

Use the final manual QA manifest in [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md) inside the same evidence directory:

```text
manual-validation.md
```

Required review areas:

- terminal review notes and terminal sizes
- dashboard review notes and viewport sizes
- screen-reader and accessibility claims/non-claims
- installed package smoke notes
- daemon lifecycle smoke notes
- recovery and maintenance smoke notes
- provider canary run or skip reason
- blocking issues and accepted residual risks

Manual artifacts such as screenshots, terminal transcripts, and redacted logs should be linked from that manifest using local relative paths.

## Redaction Rules

- Do not store API keys, tokens, or secret-like environment variables.
- Redact provider prompts and responses when they contain private repository or user content.
- Prefer summaries, event families, and state transitions over full live-provider text.
- Keep command logs focused on release diagnostics.

## Pass And Failure Use

A passing automated summary does not by itself approve the release candidate. It means the automated blocking gate passed and manual release evidence can be attached.

A failing automated summary should show the failed stage and next action. Fix the blocker, rerun the gate, and keep the new summary as the candidate evidence.

## Related Files

- [tasks-v6.md](./tasks-v6.md)
- [v6-release-hardening.md](./v6-release-hardening.md)
- [v6-release-inventory.md](./v6-release-inventory.md)
- [release-packaging.md](./release-packaging.md)
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md)
