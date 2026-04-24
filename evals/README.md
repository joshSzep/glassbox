# Replay-Backed Eval Layout

Glassbox eval cases live under `evals/` so replay baselines can be curated in the
repository instead of being tied to a local SQLite session database.

Default layout:

```text
evals/
  README.md
  bundles/
    CASE_ID.json
  cases/
    CASE_ID.json
```

Promotion workflow:

1. Promote a replayable session into a curated case with `glassbox eval promote SESSION_ID CASE_ID --title ...`.
2. Review the generated bundle, case manifest, and review artifact together.
3. Refresh an existing case with `glassbox eval refresh CASE_ID SESSION_ID --reason ...` whenever a baseline change is intentional.

Run the resulting suite with:

```text
glassbox eval run
glassbox eval run --profile commit-smoke
glassbox eval run CASE_ID
glassbox eval run --tag smoke --json
glassbox eval profiles
glassbox eval profiles --track live-provider-canary --json
glassbox eval run --output-dir .glassbox/evals/manual
glassbox eval report release-candidate advisory-context
glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/release-signoff
glassbox eval promote SESSION_ID CASE_ID --title "Case title"
glassbox eval refresh CASE_ID SESSION_ID --reason "Why this baseline changed"
```

Named profiles live in `evals/profiles.json` and make stage intent explicit for
automation and local verification. Additional `CASE_ID` arguments and repeated
`--tag` flags still work as narrower filters inside a selected profile.

Profiles also now declare a `track`. The default `deterministic` track feeds the
normal replay, eval, budget, and release-signoff workflow. The separate
`live-provider-canary` track is reserved for future optional live-provider
comparison work and must remain advisory and non-blocking.

Use `glassbox eval profiles` to inspect the repository-owned profile catalog and
`glassbox eval profiles --track live-provider-canary` to find the non-blocking
canary scaffold without mixing it into deterministic release commands.

Profiles can now also declare a reviewable `budget` block with size and
determinism guardrails such as maximum selected case count,
maximum selected-invariant case count, a recorded-model-call cost proxy,
case-artifact byte limits, allowance for advisory or unsupported cases, and
promotion or demotion policy text for deciding when a case belongs in a
stricter stage.

Capability coverage expectations live in `evals/coverage.json`. Use
`glassbox eval audit` to report which product behaviors are covered,
which release-critical behaviors still lack a curated case, and which selected
cases are not mapped to a declared product contract.

The `eval` pre-commit hook runs the full curated eval suite with a stable
local output directory:

```text
pre-commit run eval --all-files
glassbox eval run --output-dir .glassbox/evals/pre-commit --refresh-output-dir
```

That managed output directory is refreshed in place on each hook run so the
latest blocked commit leaves behind one stable `summary.json` plus the current
per-case artifacts without accumulating stale JSON from earlier runs.

Push confirmation uses the same `smoke` tag set from
the `push-confirmation` profile from `.github/workflows/push-smoke-evals.yml`
and uploads the remote run output from
`.glassbox/evals/push-smoke/` as a GitHub Actions artifact named
`push-smoke-evals-SHA`.

Release sign-off can now aggregate one or more named profiles into one retained
report directory:

```text
glassbox eval report release-candidate advisory-context
glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/release-signoff
```

That command writes:

- per-profile retained evidence under `profiles/PROFILE_ID/`
- `release-signoff.json` as the machine-readable contract summary
- `release-signoff.md` as the concise human-readable release note for terminal or CI summaries

The release sign-off status is intentionally not the same thing as an individual
suite exit code:

- `passed` means the selected blocking profiles passed, no blocking profile was
  skipped, and no selected release-critical capability remained uncovered.
- `warning` means the retained evidence is usable but still includes
  non-blocking concerns such as advisory drift or a skipped non-blocking
  profile.
- `failed` means the curated release contract was not met because of a blocking
  failure, a skipped blocking profile, or uncovered release-critical coverage.

Per-profile sign-off rows may also say `skipped` when the requested report
filters leave that profile with no selected cases. That skip is recorded in the
report instead of being inferred from missing output.

`glassbox eval report` is intentionally deterministic-only. If a requested
profile belongs to the `live-provider-canary` track, the command fails early so
optional canary research cannot be mistaken for deterministic release evidence.

Profile manifest shape:

```json
{
  "manifest_version": 1,
  "profiles": [
    {
      "profile_id": "commit-smoke",
      "title": "Commit-time smoke gate",
      "verification_stage": "commit-time",
      "track": "deterministic",
      "tags": ["smoke"],
      "blocking": true,
      "budget": {
        "max_selected_case_count": 2,
        "max_selected_invariant_case_count": 0,
        "max_recorded_model_call_count": 4,
        "max_case_artifact_bytes": 100000,
        "allow_unsupported_cases": false,
        "allow_advisory_cases": false,
        "promotion_policy": "Promote only deterministic, low-cost smoke cases.",
        "demotion_policy": "Demote cases that become noisy or too expensive for commit-time use."
      }
    },
    {
      "profile_id": "live-provider-canary",
      "title": "Live-provider canary scaffold",
      "verification_stage": "advisory",
      "track": "live-provider-canary",
      "tags": ["live-provider"],
      "blocking": false
    }
  ]
}
```

Coverage manifest shape:

```json
{
  "manifest_version": 1,
  "capabilities": [
    {
      "capability_id": "branching",
      "title": "Branching and fork lineage",
      "kind": "operator_workflow",
      "criticality": "release-critical",
      "verification_stages": ["commit-time", "push-time", "release-candidate"],
      "expected_case_ids": ["context.branch-inherited"],
      "coverage_mode": "single_case"
    },
    {
      "capability_id": "artifact_backed_context",
      "title": "Artifact-backed context contracts",
      "kind": "product_behavior",
      "criticality": "important",
      "verification_stages": ["advisory"],
      "expected_case_ids": ["context.artifact", "context.artifact-relaxed"],
      "coverage_mode": "multi_case"
    }
  ]
}
```

`coverage_mode` is the typed convention for capabilities that need more than
one curated case. `single_case` expects at most one mapped case. `multi_case`
expects at least two explicitly listed cases because different runtime paths or
selected-invariant contracts matter independently.

Guided baseline updates:

- `glassbox eval promote` exports the replay bundle into `evals/bundles/`,
  creates `evals/cases/CASE_ID.json`, and records an initial `baseline_history`
  entry inside the case manifest.
- `glassbox eval refresh` reuses the existing case manifest and bundle path,
  requires `--reason`, appends a `baseline_history` entry, and writes a
  diff-friendly review artifact under `.glassbox/evals/baseline-updates/` by
  default.
- Blocking or `release-candidate` cases require both release-discipline
  metadata such as `owner` and `capabilities` and an explicit
  `--acknowledge-policy` flag before refresh is allowed.
- The refresh artifact summarizes bundle metric changes, manifest field changes,
  and expectation or release-contract changes before the refreshed baseline is
  accepted.

That workflow also writes a GitHub Actions job summary with selected-case
counts, pass/fail totals, outcome counts, per-case severity, and retained
artifact paths such as `.glassbox/evals/push-smoke/summary.json` and
`.glassbox/evals/push-smoke/CASE_ID.json`.

Choose tags with the local-first workflow in mind:

- `smoke` cases are the blocking commit-time barrier and should stay small,
  stable, and cheap to rerun.
- `context.branch-inherited` is part of `smoke`, so the existing commit-time and
  push-time smoke workflows now exercise branch-inherited context without any
  hook changes.
- Broader tags are better for advisory or push-time confirmation until their
  value is high enough to justify blocking every commit.
- If a post-push failure keeps finding the same class of regression, promote the
  relevant case or tag into `smoke` so it fails earlier.

Current context-focused cases:

- `context.branch-inherited`: exact-match replay coverage for inherited
  transcript, inherited runtime notes, and branch lineage.
- `context.artifact`: selected-invariant coverage for artifact-backed pytest
  failure digests while ignoring known `event_families drift` from replayed
  `run_tests` output chunks.
- `context.artifact-relaxed`: the same artifact-backed session with an
  intentionally relaxed transcript baseline so transcript-only drift can be
  ignored without hiding context-source drift.

Each run writes one JSON artifact per case plus `summary.json` into the selected
output directory. If `--output-dir` is omitted, Glassbox creates a timestamped
directory under `.glassbox/evals/`.

The per-case artifact now includes compact triage fields such as
`triage_classification`, `triage_headline`,
`triage_first_relevant_change`, `triage_drift_sources`, and
`triage_recommended_inspection_path` alongside the full nested
`replay_result`. `summary.json` keeps the same per-case triage fields so
pre-commit and push-time automation can point directly to the right detailed
artifact without forcing full JSON archaeology first.

When a named profile has a `budget`, `summary.json` also includes a
`profile_budget` object with measured counts, configured limits, warning or
enforced status, and any violations. The terminal and GitHub Actions summary
renderers surface that budget health next to the replay outcomes so a suite can
fail because it became too broad or too noisy, even if each individual case
still replayed successfully.

`release-signoff.json` reuses the same capability, severity, budget, and case
metadata vocabulary instead of inventing a separate release-only schema. It
summarizes retained per-profile `summary.json` outputs, case artifact paths,
severity totals, aggregate capability coverage, advisory drift counts,
unsupported cases, skipped profiles, and baseline freshness cues such as the
latest and oldest retained baseline update timestamps.

The live-provider canary track deliberately does not reuse release-signoff
status or deterministic profile budgets as a source of shipping confidence.
It is a repository-owned place to stage future comparison work while keeping
the local-first deterministic contract honest.

End-to-end governed example:

```text
uv run glassbox run "Inspect the repository" --cwd .
uv run glassbox eval promote SESSION_ID tooling.readme --title "README inspection stays stable" --tag smoke --tag tooling --owner runtime.replay --capability repository_inspection --capability replay_portability --severity high --verification-stage commit-time --verification-stage push-time --reason "Initial promotion for repository inspection contract" --cwd . --db-path .glassbox/glassbox.sqlite3
uv run glassbox eval run --profile commit-smoke --output-dir .glassbox/evals/pre-commit --refresh-output-dir --cwd .
uv run glassbox eval refresh tooling.readme SESSION_ID --reason "Intentional baseline update after README contract change" --acknowledge-policy --cwd . --db-path .glassbox/glassbox.sqlite3
uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/release-signoff --cwd .
```

Use that flow when a replayable session should become a maintained repository
contract rather than a one-off local check.

Governance decisions:

- Add a new case when the behavior is important enough to protect across branches, CI runs, and contributors instead of only in one local session.
- Refresh an existing baseline only when the drift is intentional and the same underlying contract should continue to exist.
- Promote a case into a stricter profile when repeated advisory or push-time drift proves that the regression signal belongs earlier and the case fits the tighter budget.
- Demote a case out of a stricter profile when it becomes noisy, too expensive, or dependent on relaxed selected-invariant interpretation.

Severity guidance:

- `critical`: treat as release-signoff or operator-trust blocking until understood.
- `high`: important product or operator workflow that should normally block the deterministic stage it belongs to.
- `medium`: meaningful contract worth review, but not as central as the blocking core.
- `low`: exploratory or advisory signal that should not quietly become shipping confidence on its own.

Case manifest shape:

```json
{
  "manifest_version": 1,
  "case_id": "tooling.readme",
  "title": "README inspection stays stable",
  "bundle_path": "../bundles/tooling.readme.json",
  "tags": ["smoke", "tooling"],
  "notes": "Captured after replay bundle export stabilized.",
  "release_contract": {
    "owner": "runtime.replay",
    "capabilities": ["repository_inspection", "replay_portability"],
    "severity": "medium",
    "verification_stages": ["commit-time", "push-time"],
    "baseline_refresh_policy": "review_required"
  },
  "expectation": {
    "mode": "exact_match"
  }
}
```

`release_contract` is optional for older cases, but curated cases should now use
it so the suite can surface ownership and release intent explicitly.

Current metadata conventions:

- `owner`: normalized repository-owned area identifier such as `runtime.replay`,
  `runtime.context`, or `tools.policy`
- `capabilities`: one or more normalized operator-facing behaviors protected by
  the case, such as `branching`, `approval_flow`, `context_inheritance`, or
  `replay_portability`
- `severity`: one of `critical`, `high`, `medium`, or `low`
- `verification_stages`: one or more of `commit-time`, `push-time`,
  `release-candidate`, or `advisory`
- `baseline_refresh_policy`: one of `review_required`, `intentional_only`, or
  `advisory`

Backwards compatibility is preserved for older manifests that omit
`release_contract`. They default to an advisory, medium-severity case with no
declared owner or capability metadata.

For targeted cases, `expectation.mode` may be `selected_invariants` with an
explicit `invariants` list such as `final_state` or `transcript`. Omitting the
expectation keeps the default strict behavior.

Reading context-related failures:

1. `manifest_drift` with text such as `recorded enriched context source drifted:
  pytest_failure_digest` means replay detected a semantic change in one
  specific context source. Treat that as a replay-contract failure, not as a
  generic transcript mismatch.
1. Failure artifacts now distinguish the replay `outcome` from the more precise
  triage `classification`. For example, a replay may still report
  `manifest_drift` while classifying the case as `context_source_drift` with a
  drift source such as `runtime_notes` or `pytest_failure_digest`.
2. `behavioral_drift` on a `selected_invariants` case can still be a pass when
  the case artifact reports only `ignored_mismatches`. This is how
  `context.artifact` and `context.artifact-relaxed` tolerate known transcript
  or event-family noise while still failing if approvals, tool calls, final
  state, or context manifests drift.
2. The selected-invariant artifact now records a
  `selected_invariant_interpretation` string so the operator can tell at a
  glance whether ignored drift was acceptable or whether one of the curated
  dimensions actually failed.
3. `event_families drift` on `run_tests`-backed cases currently comes from live
  `ToolOutputChunk` events that offline replay does not reproduce. That drift
  is expected for the artifact cases and should not be mistaken for context
  source drift.
4. `unsupported_session` means the retained baseline itself needs migration or
   refresh work before deterministic replay can be trusted again.
5. Profile-budget violations are governance failures about suite shape,
   determinism, or artifact volume. They can block a stage even when every
   individual case technically replayed successfully.

Troubleshooting flows:

1. Commit blocked by replay/eval drift:
  rerun `pre-commit run eval --all-files`, inspect
  `.glassbox/evals/pre-commit/summary.json`, then inspect the failing per-case
  JSON artifact in the same directory.
1. Commit blocked by profile budget:
  inspect the `profile_budget` section in `.glassbox/evals/pre-commit/summary.json`
  or the terminal `Profile budget:` block to see whether selected case count,
  selected-invariant count, recorded model calls, artifact volume, or advisory
  eligibility exceeded the profile guardrails.
1. Release sign-off warning or failure:
  inspect `release-signoff.md` first, then open `release-signoff.json` if the
  machine-readable profile, capability, or freshness details are needed before
  drilling into `profiles/PROFILE_ID/summary.json` or the retained per-case
  artifacts.
1. Live-provider canary exploration:
  use `glassbox eval profiles --track live-provider-canary` to discover the
  reserved canary scaffold, but keep that work out of deterministic
  `glassbox eval report` runs because canary evidence is intentionally not part
  of release sign-off.
2. Push confirmation failed after local success:
  read the GitHub Actions job summary first, then download the
  `push-smoke-evals-SHA` artifact only if the summary does not already explain
  the failing case.
3. Intentional baseline refresh:
  use `glassbox eval refresh CASE_ID SESSION_ID --reason ...`, review the
  generated `.glassbox/evals/baseline-updates/CASE_ID.json` artifact alongside
  the checked-in bundle and case manifest changes, then rerun the targeted case
  or tagged suite before committing.
