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

## Change-Impact Recommendations

GBX-340 defines the operator contract for choosing replay and eval scope from a
change set before the recommendation command itself exists.

The model stays advisory.

- Glassbox should recommend relevant existing cases and profiles after a change; it should not pretend it has proved the only correct verification set.
- Every recommendation should explain why it was chosen in terms of touched paths, owner metadata, capability coverage, or verification-stage rules.
- If the evidence is weak, Glassbox should say that directly and fall back to the smallest deterministic smoke surface or to no confident recommendation.

The recommendation steps are:

1. Start from repository-relative changed paths such as `src/glassbox/runtime/replay_execution.py` or `evals/coverage.json`.
2. Resolve those paths through repository-owned impact rules that map stable path globs or subsystem anchors to owner IDs, capability IDs, and optional direct case or profile hints.
3. Expand through existing eval metadata:
  - case manifests contribute `release_contract.owner`, `capabilities`, and `verification_stages`
  - `evals/coverage.json` contributes capability-to-case expectations and stage criticality
  - `evals/profiles.json` contributes stage-specific profile recommendations, deterministic-versus-canary track, and budget expectations
4. Rank and explain recommendations by confidence rather than flattening them into one opaque list.

Recommendation confidence should be visible in output:

- `direct`: the touched path matched a rule that named the case, capability, or profile explicitly
- `owner-derived`: the touched path mapped to one owner and the case carries the same owner in its release-contract metadata
- `capability-derived`: the touched path mapped to one capability and the case came from coverage expectations or case capability metadata
- `stage-derived`: the profile was recommended because impacted capabilities or cases participate in that verification stage
- `fallback`: no stronger deterministic mapping was available

Practical operator expectations:

- changes to `evals/cases/*.json` should recommend the touched case directly plus any deterministic profiles that include its verification stages
- changes to `evals/profiles.json` should recommend the affected profiles themselves and explain that the change is profile-governance metadata, not a behavior-specific product signal
- changes to `evals/coverage.json` should recommend `eval audit` plus the deterministic profiles or cases named by the affected capabilities
- changes to runtime, tool, CLI, or dashboard code should resolve through impact rules into owners and capabilities first, then expand outward to cases and profiles
- documentation-only changes outside replay or eval governance surfaces may legitimately produce no strong replay recommendation

Examples:

- A change under `src/glassbox/runtime/replay_*.py` should usually map to owner `runtime.replay`, then to replay portability or smoke capabilities, then to the deterministic profiles that carry those cases.
- A change under `src/glassbox/runtime/context_*.py` should usually map to owner `runtime.context`, then to `context_inheritance`, `context_drift_detection`, or `artifact_backed_context`, then to the cases and stages that cover those capabilities.
- A change only to `evals/coverage.json` should explain that the primary follow-up is contract-audit validation, not product-behavior replay alone.

The first version should not try to do any of the following:

- infer a perfect minimal test set from whole-program semantics
- mix `live-provider-canary` profiles into deterministic release recommendations
- auto-run or auto-refresh cases without an operator seeing the reasoning first
- treat low-confidence guesses as if they were release-bearing evidence

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
