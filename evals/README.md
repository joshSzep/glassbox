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

1. Export a replayable session into `evals/bundles/CASE_ID.json`.
2. Add `evals/cases/CASE_ID.json` with the stable case metadata and expected invariants.
3. Review bundle and case updates together whenever a baseline is intentionally refreshed.

Run the resulting suite with:

```text
glassbox eval run
glassbox eval run --profile commit-smoke
glassbox eval run CASE_ID
glassbox eval run --tag smoke --json
glassbox eval run --output-dir .glassbox/evals/manual
```

Named profiles live in `evals/profiles.json` and make stage intent explicit for
automation and local verification. Additional `CASE_ID` arguments and repeated
`--tag` flags still work as narrower filters inside a selected profile.

The commit-time smoke hook uses the same tagged suite with a stable local output
directory:

```text
pre-commit run eval-smoke --all-files
glassbox eval run --profile commit-smoke --output-dir .glassbox/evals/pre-commit --refresh-output-dir
```

That managed output directory is refreshed in place on each hook run so the
latest blocked commit leaves behind one stable `summary.json` plus the current
per-case artifacts without accumulating stale JSON from earlier runs.

Push confirmation uses the same `smoke` tag set from
the `push-confirmation` profile from `.github/workflows/push-smoke-evals.yml`
and uploads the remote run output from
`.glassbox/evals/push-smoke/` as a GitHub Actions artifact named
`push-smoke-evals-SHA`.

Profile manifest shape:

```json
{
  "manifest_version": 1,
  "profiles": [
    {
      "profile_id": "commit-smoke",
      "title": "Commit-time smoke gate",
      "verification_stage": "commit-time",
      "tags": ["smoke"],
      "blocking": true
    }
  ]
}
```

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
2. `behavioral_drift` on a `selected_invariants` case can still be a pass when
  the case artifact reports only `ignored_mismatches`. This is how
  `context.artifact` and `context.artifact-relaxed` tolerate known transcript
  or event-family noise while still failing if approvals, tool calls, final
  state, or context manifests drift.
3. `event_families drift` on `run_tests`-backed cases currently comes from live
  `ToolOutputChunk` events that offline replay does not reproduce. That drift
  is expected for the artifact cases and should not be mistaken for context
  source drift.

Troubleshooting flows:

1. Commit blocked by replay/eval drift:
  rerun `pre-commit run eval-smoke --all-files`, inspect
  `.glassbox/evals/pre-commit/summary.json`, then inspect the failing per-case
  JSON artifact in the same directory.
2. Push confirmation failed after local success:
  read the GitHub Actions job summary first, then download the
  `push-smoke-evals-SHA` artifact only if the summary does not already explain
  the failing case.
3. Intentional baseline refresh:
  update the checked-in bundle and case manifest together, then rerun the
  targeted case or tagged suite before committing.
