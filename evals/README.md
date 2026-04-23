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
glassbox eval run CASE_ID
glassbox eval run --tag smoke --json
glassbox eval run --output-dir .glassbox/evals/manual
```

The commit-time smoke hook uses the same tagged suite with a stable local output
directory:

```text
pre-commit run eval-smoke --all-files
glassbox eval run --tag smoke --output-dir .glassbox/evals/pre-commit --refresh-output-dir
```

That managed output directory is refreshed in place on each hook run so the
latest blocked commit leaves behind one stable `summary.json` plus the current
per-case artifacts without accumulating stale JSON from earlier runs.

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
  "expectation": {
    "mode": "exact_match"
  }
}
```

For targeted cases, `expectation.mode` may be `selected_invariants` with an
explicit `invariants` list such as `final_state` or `transcript`. Omitting the
expectation keeps the default strict behavior.
