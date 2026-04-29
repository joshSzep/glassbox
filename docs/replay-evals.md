# Replay And Eval Workflows

Replay and eval answer a different question from the live session CLI.

- live session commands answer: what should this session do next?
- replay and eval answer: does the current codebase still reproduce the behavior I care about?

Use replay and eval as repository-owned behavioral contracts, not as a replacement for unit tests, integration tests, linting, or type checking.

## Pick The Right Workflow

- Use `status`, `attach`, `message`, `answer`, `approve`, and `deny` for live or paused sessions.
- Use `fork` when you want a new child session from a stable historical turn.
- Use `replay run` when you want to re-check one recorded session or portable bundle.
- Use `replay bundle export` when you want a portable replay bundle.
- Use `eval run` when you want curated checked-in regression cases.
- Use `eval audit` when you want coverage and contract-gap reporting.
- Use `eval recommend` when you want suggested replay cases or eval profiles for a changed path set.
- Use `eval report` when you want deterministic release-signoff evidence from named profiles.
- Use `eval profile list` when you want to inspect repository-owned profiles and tracks.

## Single-Session Replay

Replay one recorded session:

```bash
uv run glassbox replay run SESSION_ID --cwd .
```

Replay a portable bundle:

```bash
uv run glassbox replay bundle run evals/bundles/CASE_ID.json --cwd .
```

Inspect a portable bundle without running it:

```bash
uv run glassbox replay bundle inspect evals/bundles/CASE_ID.json --json
```

Export a portable bundle:

```bash
uv run glassbox replay bundle export SESSION_ID
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
uv run glassbox eval profile list --json --cwd .
uv run glassbox eval profile list --track live-provider-canary --json --cwd .
```

Inspect eval cases:

```bash
uv run glassbox eval case list --cwd .
uv run glassbox eval case show CASE_ID --json --cwd .
```

Recommend replay or eval follow-up from touched paths:

```bash
uv run glassbox eval recommend src/glassbox/runtime/replay_execution.py --cwd .
uv run glassbox eval recommend src/glassbox/runtime/context_builder.py evals/coverage.json --json --cwd .
```

Plan and optionally execute the deterministic recommendations:

```bash
uv run glassbox eval recommend src/glassbox/runtime/replay_execution.py --json --cwd .
uv run glassbox eval recommend src/glassbox/runtime/replay_execution.py --execute --cwd .
```

Dry-run JSON includes `verification_plan_entries`,
`skipped_verification_checks`, and `executed_verification_checks`. Fallback
confidence rows stay optional unless `--include-low-confidence` is passed, and
live-provider canary profiles stay skipped unless
`--include-live-provider-canary` is explicit.

Generate release-signoff evidence:

```bash
uv run glassbox eval report commit-smoke push-confirmation release-candidate \
  --output-dir .glassbox/evals/release-signoff \
  --cwd .
```

## Promotion And Refresh

Promote a recorded session into a checked-in eval case:

```bash
uv run glassbox eval case promote tooling.readme SESSION_ID \
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
uv run glassbox eval case refresh tooling.readme SESSION_ID \
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

Cancelled turns are normalized as cancellation evidence, not ordinary failures.
Replay bundles preserve `CancellationRequested`, `CancellationAcknowledged`,
`ToolExecutionCancelled`, `TurnCancelled`, and cancelled turn-output artifacts as
behavioral evidence. A bundle whose final recorded turn was intentionally
cancelled replays to the recorded cancellation baseline, because the operator's
wall-clock cancellation timing is not a deterministic provider behavior to
reproduce. If cancellation evidence changes, evals report `cancellations drift`
or `final_state drift` instead of timeout, provider failure, or generic tool
failure.

## Local-First Verification Policy

Glassbox assumes a direct-to-`main` workflow where the important regression barrier happens before `git commit`.

Use replay and eval verification in three layers:

1. Commit time: local blocking smoke checks in pre-commit.
2. Push time: broader confirmation and retained artifacts after push.
3. Release candidate: deterministic sign-off through `eval report` and the v6 release gate.
4. Advisory: optional non-blocking context and live-provider suites.

The expected split is:

- `smoke` tags are the commit-time blocking set
- broader tags remain advisory or push-time only until they are stable enough to move earlier
- packaging, installed-wheel, and live-provider checks stay outside deterministic eval profiles

See [release-check-alignment-v6.md](./release-check-alignment-v6.md) for the full local, push, release-candidate, and advisory check ladder.

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

`eval recommend` also prints a compact daily-development release-surface view for
`commit-time`, `push-time`, and `release-candidate`. Each row shows whether that
surface is impacted, which deterministic profiles and cases are recommended,
which blocking profiles are involved, and any profile-budget notes that matter
for local verification scope.

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

`eval recommend --execute` is the operator-approved path for turning the visible
recommendation rows into local verification. It runs planned deterministic eval
cases or profiles, writes the usual eval artifacts, and reports skipped checks
instead of silently expanding low-confidence or live-provider surfaces.

## Local Failure Triage

When commit-time eval fails:

1. Re-run `uv run pre-commit run eval --all-files` if you want a clean repro.
2. Open `.glassbox/evals/pre-commit/summary.json`.
3. Open the failing `.glassbox/evals/pre-commit/CASE_ID.json` artifact.
4. Fix the accidental drift or intentionally refresh the baseline.

Replay and eval triage now names the likely evidence surface before pointing at
raw JSON. Transcript, event-family, task-plan, budget, verification, memory,
repository-index, policy, provider-advisory, and final-state drift each carry a
targeted next-inspect hint. These are evidence-based summaries: they identify
the first divergent surface and recommended artifact/projection to inspect, but
they do not infer model intent.

For cancelled-turn cases, inspect the cancellation event family and the retained
turn-output artifact before refreshing. A matching cancellation outcome means the
operator interruption was preserved; missing cancellation evidence is drift.

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
See [provider-canary-policy-v6.md](./provider-canary-policy-v6.md) for when and
how live-provider canaries may be retained as advisory release evidence.
Manual release evidence should link the retained eval summary rather than paste
large generated JSON into docs. Use [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md)
for the release-candidate artifact shape.

## Related Files

- [../evals/README.md](../evals/README.md)
- [providers.md](./providers.md)
- [branching.md](./branching.md)
- [runtime-context.md](./runtime-context.md)
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md)
