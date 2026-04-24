# Replay And Eval Workflows

Replay and eval answer a different question from the live session CLI.

- live session commands answer: what should this session do next?
- replay and eval answer: does the current codebase still reproduce the behavior I care about?

Use replay and eval as repository-owned behavioral contracts, not as a replacement for unit tests, integration tests, linting, or type checking.

## Pick The Right Workflow

- Use `status`, `attach`, `message`, `answer`, `approve`, and `deny` for live or paused sessions.
- Use `fork` when you want a new child session from a stable historical turn.
- Use `replay` when you want to re-check one recorded session.
- Use `replay-export` when you want a portable replay bundle.
- Use `eval run` when you want curated checked-in regression cases.
- Use `eval audit` when you want coverage and contract-gap reporting.
- Use `eval report` when you want deterministic release-signoff evidence from named profiles.
- Use `eval profiles` when you want to inspect repository-owned profiles and tracks.

## Single-Session Replay

Replay one recorded session:

```bash
uv run glassbox replay SESSION_ID --cwd .
```

Replay a portable bundle:

```bash
uv run glassbox replay --bundle evals/bundles/CASE_ID.json --cwd .
```

Export a portable bundle:

```bash
uv run glassbox replay-export SESSION_ID
```

## Eval Suite Commands

Run one case:

```bash
uv run glassbox eval run CASE_ID --cwd .
```

Run the smoke tag set:

```bash
uv run glassbox eval run --tag smoke --cwd .
```

Run a named profile:

```bash
uv run glassbox eval run --profile commit-smoke --cwd .
```

Inspect profiles:

```bash
uv run glassbox eval profiles --json --cwd .
uv run glassbox eval profiles --track live-provider-canary --json --cwd .
```

Generate release-signoff evidence:

```bash
uv run glassbox eval report commit-smoke push-confirmation release-candidate \
  --output-dir .glassbox/evals/release-signoff \
  --cwd .
```

## Promotion And Refresh

Promote a recorded session into a checked-in eval case:

```bash
uv run glassbox eval promote SESSION_ID tooling.readme \
  --title "README inspection stays stable" \
  --tag smoke \
  --tag tooling \
  --owner runtime.replay \
  --capability repository_inspection \
  --capability replay_portability \
  --severity high \
  --verification-stage commit-time \
  --verification-stage push-time \
  --reason "Initial promotion for repository inspection contract" \
  --cwd . \
  --db-path .glassbox/glassbox.sqlite3
```

Refresh an existing baseline intentionally:

```bash
uv run glassbox eval refresh tooling.readme SESSION_ID \
  --reason "Intentional baseline update after README contract change" \
  --acknowledge-policy \
  --cwd . \
  --db-path .glassbox/glassbox.sqlite3
```

## Replay Result Categories

- `exact match`: the recorded baseline was reproduced
- `behavioral drift`: replay ran, but the normalized behavior changed
- `manifest drift`: the recorded prompt, context, or tool manifest no longer matches current preparation
- `unsupported session`: the replay artifact or bundle schema is unsupported
- `replay failure`: the baseline could not be replayed at all

## Local-First Verification Policy

Glassbox assumes a direct-to-`main` workflow where the important regression barrier happens before `git commit`.

Use replay and eval verification in three layers:

1. Commit time: local blocking smoke checks in pre-commit.
2. Push time: broader confirmation and retained artifacts after push.
3. Later scheduled coverage: optional non-blocking advisory suites.

The expected split is:

- `smoke` tags are the commit-time blocking set
- broader tags remain advisory or push-time only until they are stable enough to move earlier

## Local Failure Triage

When commit-time eval fails:

1. Re-run `uv run pre-commit run eval --all-files` if you want a clean repro.
2. Open `.glassbox/evals/pre-commit/summary.json`.
3. Open the failing `.glassbox/evals/pre-commit/CASE_ID.json` artifact.
4. Fix the accidental drift or intentionally refresh the baseline.

When GitHub pre-commit fails after local success:

1. Open the failed `Pre-commit` run for the pushed commit.
2. Compare it against a fresh local `uv run pre-commit run --all-files` run.
3. Inspect `.glassbox/evals/pre-commit/summary.json` if the failure is in the eval hook.
4. Fix the regression or update the baseline intentionally, then rerun the full local pre-commit flow.

## Deterministic Vs Canary Tracks

The repository-owned profile manifest carries two explicit tracks:

- `deterministic` profiles participate in replay, eval, budgets, and release sign-off
- `live-provider-canary` profiles are advisory and non-blocking

`glassbox eval report` is intentionally deterministic-only.

## Related Files

- [../evals/README.md](../evals/README.md)
- [providers.md](./providers.md)
- [branching.md](./branching.md)
- [runtime-context.md](./runtime-context.md)
