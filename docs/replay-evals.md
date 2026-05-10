# Replay And Eval Workflows

Replay and eval answer a different question from the live session CLI.

- live session commands answer: what should this session do next?
- replay and eval answer: does the current codebase still reproduce the behavior I care about?

Use replay and eval as repository-owned behavioral contracts, not as a replacement for unit tests, integration tests, linting, or type checking.
When a replay bundle or eval summary is meant for human review, use
[reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) for redaction
and retention guidance before sharing or committing it.

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

## Repository Intelligence Context Drift

Repository intelligence context is replayed as a named enriched-context source:
`repository_intelligence`. Replay manifests fingerprint the bounded source
summary rather than raw repository artifacts. The fingerprint covers the
context status, schema version, source digest, included sources, excluded
sources, selected items, overflow counts, limitations, and safe next actions.

When repository intelligence changes, replay should report source-level
manifest drift such as:

- `recorded enriched context source drifted: repository_intelligence`
- `enriched context source missing: repository_intelligence`
- `enriched context source added: repository_intelligence`

Read those as context drift first, not behavior drift. Inspect the runtime
context snapshot, repository intelligence freshness, excluded stale sources,
and path-to-verification recommendations before refreshing a baseline.

Portable replay keeps older bundles compatible. If a recorded bundle predates
repository intelligence context, a newly available live
`repository_intelligence` source can be ignored for portable replay in the same
way live `repository_context` is ignored. Bundles that recorded repository
intelligence still compare it by source fingerprint so stale, missing, or
changed intelligence remains explainable.

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
change set before the recommendation command itself exists. The v15
[path-to-verification recommendation contract](./path-to-verification-recommendations.md)
extends this model with typed path impact, verification target, command recipe,
skipped-check, stale-evidence, provenance, freshness, confidence, and limitation
fields while preserving the same advisory boundary.

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

`eval recommend` first names the cheapest visible next command, then prints a
grouped explanation of why each row was selected. The JSON report keeps the same
shape with `cheapest_next_command`, `reason_groups`, and
`fallback_policy_commands` so downstream tools can distinguish inferred
evidence from manual policy fallback guidance.

The command also reads repository-owned verification recipes from
`evals/recipes.json`. Recipes are declarative change-family guidance: each row
matches touched paths with `path_globs` and prints commands the operator may run
for familiar work such as docs-only edits, release docs, release-gate scripts,
frontend dashboard changes, runtime event contracts, store schema changes,
provider posture, and packaging. Recipe commands are shown as guidance only;
`eval recommend --execute` still executes only planned deterministic eval cases
or profiles, never arbitrary recipe commands.

When `.glassbox/workspace-topology.json` exists, `eval recommend` also adds
topology-derived recipe rows for affected local components. Fresh topology can
name package-level checks such as related Python tests, `ruff`, `ty`, frontend
lint/typecheck/test/build commands, and docs guardrails from discovered
manifests, source roots, test roots, and package managers. Stale topology is
still shown, but those rows use degraded confidence and include rebuild
guidance; missing topology simply means no topology-derived rows are added.
These rows are advisory like repository recipes and are not executed by
`eval recommend --execute`.

The stable v11 recommendation contract has focused deterministic fixtures in
`evals/fixtures/recommendation_cases.json`. Those fixtures cover release-path
recommendation, frontend dashboard recommendation, provider-posture
recommendation, and the no-confident-match fallback path. They are exercised by
`tests/unit/test_eval_recommendations.py`. GBX-1190 also promotes the compact
`recommendation.release-path` replay fixture into the `release-candidate`
profile so release-path recommendation evidence participates in deterministic
sign-off while the broader matching matrix stays in focused tests.

`eval recommend` also prints a compact daily-development release-surface view for
`commit-time`, `push-time`, `release-candidate`, and `advisory`. Each row shows
whether that surface is impacted, which profiles and cases are recommended,
which blocking profiles are involved, and any profile-budget notes that matter
for local verification scope. Release-candidate rows can also include
`release_gate_commands`; those are full sign-off gates such as
`uv run python scripts/validate_v11_release_gate.py` or package-content
validation, not replay/eval profiles. Advisory rows may include deterministic
advisory profiles or live-provider canary profiles, but live-provider checks are
skipped from the executable verification plan unless the operator explicitly
includes that canary surface.

For long-running work, the same command also emits `long_run_surfaces` for
`immediate`, `checkpoint`, `pre-resume`, `pre-merge`, and `release-candidate`
verification. These rows do not execute anything by themselves; they tell an
operator when the recommended cases and profiles should be considered. Changes
to checkpoint, compaction, tool-attempt, provider-recovery, verification-drift,
or long-run cockpit paths add explicit long-run risk reasons so resume and
checkpoint decisions are not treated like ordinary short-turn commits.

Recommendation confidence should be visible in output:

- `direct`: the touched path matched a rule that named the case, capability, or profile explicitly
- `owner-derived`: the touched path mapped to one owner and the case carries the same owner in its release-contract metadata
- `capability-derived`: the touched path mapped to one capability and the case came from coverage expectations or case capability metadata
- `stage-derived`: the profile was recommended because impacted capabilities or cases participate in that verification stage
- `fallback`: no stronger deterministic mapping was available

Verification recipes have their own source and confidence:

- `direct`: repository-owned `evals/recipes.json` matched the changed path
- `topology`: a fresh workspace topology snapshot matched the changed path to a local component
- `degraded`: topology matched the path, but the snapshot is stale or otherwise degraded

Reason groups make the same signal easier to scan:

- `direct-path`: touched eval metadata or an impact rule directly named a case or profile
- `owner-derived-rule`: a path rule mapped to an owner and matching cases came from release-contract owner metadata
- `capability-derived-rule`: a path rule mapped to a capability and matching cases came from coverage or case capability metadata
- `stage-derived-profile`: deterministic profiles were selected because matched cases or capabilities affected their verification stage
- `release-gate-recommendation`: full release-gate commands were named separately from eval profiles
- `fallback-policy`: no confident mapping existed, so any suggested command is manual policy guidance rather than inferred evidence

Practical operator expectations:

- changes to `evals/cases/*.json` should recommend the touched case directly plus any deterministic profiles that include its verification stages
- changes to `evals/profiles.json` should recommend the affected profiles themselves and explain that the change is profile-governance metadata, not a behavior-specific product signal
- changes to `evals/coverage.json` should recommend `eval audit` plus the deterministic profiles or cases named by the affected capabilities
- changes to `scripts/validate_v*_release_gate.py`,
  `docs/v*-release-gate.md`, `docs/v*-release-candidate.md`,
  `docs/release-packaging.md`, or `scripts/validate_package_contents.py`
  should recommend the deterministic `release-candidate` eval profile and
  separately name the applicable full gate command
- changes to runtime, tool, CLI, dashboard, task, memory, repository-index, provider, or branch-search code should resolve through impact rules into owners and capabilities first, then expand outward to cases and profiles
- provider readiness changes may recommend `live-provider-canary`, but that profile remains advisory and skipped unless explicitly selected
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

## V11 Confidence Fixtures

The `release-candidate` profile includes five compact v11 confidence fixtures:

- `recommendation.release-path` for release recommendation sign-off visibility
- `context.compaction-cap-guidance` for friendly over-cap compaction guidance
- `checkpoint.absence-explanation` for historical/imported checkpoint absence
- `knowledge.posture-summary` for unified freshness, provenance, and next action
- `branch-search.decision-support` for candidate evidence, risk, cost, and
  verification recommendations without automatic merge behavior

These cases are fixture-backed deterministic eval evidence. They intentionally
do not replace focused unit/integration tests for the live derivation logic, and
they do not claim live browser, screen-reader, or provider behavior.

## V12 Reviewable-Change Fixtures

The `release-candidate` profile includes two compact v12 reviewable-change
fixtures:

- `changeset.reviewable-lifecycle` for changeset creation, inventory
  provenance, stale verification readiness, review brief generation, commit
  readiness, and command evidence classification
- `changeset.branch-candidate-adoption` for explicit selected-candidate
  adoption into changeset review evidence without automatic merge, commit,
  push, or PR behavior

These cases are deterministic release-candidate evidence for the reviewable
change contract. They are intentionally compact; focused runtime, CLI, API,
dashboard, export, redaction, and policy tests remain the stronger authority
for live derivation details.

## V15 Repository Intelligence Fixtures

The `release-candidate` profile includes five compact v15 repository
intelligence fixtures:

- `repository-intelligence.snapshot-rich` for rich local snapshot generation
  across roots, packages, generated paths, command recipes, ownership hints,
  release surfaces, freshness, provenance, confidence, and limitations
- `repository-intelligence.path-verification` for path-to-verification
  guidance that keeps likely tests, evals, recipes, stale-evidence posture, and
  safe next commands explainable
- `repository-intelligence.stale-degradation` for visible confidence
  degradation and rebuild guidance when repository intelligence is stale or
  missing
- `repository-intelligence.memory-command` for confirmed active memory shaping
  command recommendations only as provenance-backed, review-gated evidence
- `repository-intelligence.context-drift` for source-level replay drift of the
  bounded `repository_intelligence` context source

These cases make core v15 behavior part of deterministic release-candidate
evidence. They do not replace focused repository index, topology, memory,
context, eval recommendation, CLI/API, frontend, browser, accessibility, or
dogfooding checks.

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
