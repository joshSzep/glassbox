# v9 Dogfooding Summary

This page records the sanitized GBX-981 dogfooding pass for Glassbox v9. Raw
command output, local SQLite databases, and provider canary artifacts are kept
under `.glassbox/dogfooding/v9/` and are not committed.

The pass follows [dogfooding.md](./dogfooding.md): retain only sanitized
summaries in docs, keep private workspace details local, and convert each
finding into a fix, docs update, eval or test candidate, accepted residual
risk, or post-v9 task during GBX-982.

## Pass Inventory

| Pass ID | Workflow | Provider Posture | Autonomy Mode | Dashboard Used | Outcome |
| --- | --- | --- | --- | --- | --- |
| `20260429-0930-repository-inspection` | Repository inspection and explanation | diagnostics ready; credential present, redacted | deterministic inspection | no | completed with repository-index finding |
| `20260429-1100-small-edit-verification` | Small docs/test edit with verification | credentialed streaming canary passed, advisory | manual edit with focused verification | no | completed with verification and provider findings |
| `20260429-1400-branch-search-plan` | Longer branch-search planning workflow | provider not needed for deterministic command flow | guided | no | completed with branch-search selection finding |

## Pass Notes

### Repository Inspection

Commands exercised:

```bash
uv run glassbox readiness check --json --cwd . --db-path .glassbox/dogfooding/v9/20260429-0930-repository-inspection/glassbox.sqlite3
uv run glassbox provider diagnostics --json --cwd . --db-path .glassbox/dogfooding/v9/20260429-0930-repository-inspection/glassbox.sqlite3
uv run glassbox repo index status --cwd . --db-path .glassbox/dogfooding/v9/20260429-0930-repository-inspection/glassbox.sqlite3
uv run glassbox repo index build --cwd . --db-path .glassbox/dogfooding/v9/20260429-0930-repository-inspection/glassbox.sqlite3
uv run glassbox repo index search turn_engine --cwd . --db-path .glassbox/dogfooding/v9/20260429-0930-repository-inspection/glassbox.sqlite3 --limit 3
uv run glassbox command guide --json
```

Sanitized result:

- Readiness returned `needs_attention` only because repository intelligence was
  stale.
- Provider diagnostics were ready for the default OpenAI model with credentials
  present and redacted.
- Repository index stale guidance gave concrete status and build commands.
- Rebuilding refreshed the index, and source-oriented search found relevant
  runtime entries.
- Searching for a docs-only term did not return docs results; that appears to
  be current repository-index scope, not a command failure.

### Small Edit With Verification

Commands exercised:

```bash
uv run glassbox eval recommend docs/dogfooding.md tests/unit/test_v9_dogfooding_docs.py --cwd .
uv run pytest tests/unit/test_v9_dogfooding_docs.py
uv run ruff check tests/unit/test_v9_dogfooding_docs.py
uv run glassbox provider canary run --scenario streaming-text --json --cwd . --db-path .glassbox/dogfooding/v9/20260429-1100-small-edit-verification/glassbox.sqlite3 --output-dir .glassbox/dogfooding/v9/20260429-1100-small-edit-verification/provider-canary
```

Sanitized result:

- Focused pytest and lint passed for the docs guardrail test.
- `eval recommend` returned no recommendations for the docs/test guardrail
  change. That is understandable for deterministic replay scope, but it leaves
  operators without a Glassbox-native hint for docs guardrail validation.
- The credentialed streaming provider canary passed and wrote redacted advisory
  evidence locally. Provider evidence remains non-blocking beside deterministic
  replay/eval contracts.
- The canary summary was internally confusing: the scenario outcome was
  `passed`, while the retained scenario final status was `running`.

### Branch-Search Plan

Commands exercised:

```bash
uv run glassbox session run --cwd . --db-path .glassbox/dogfooding/v9/20260429-1400-branch-search-plan/glassbox.sqlite3 --autonomy-mode guided --approval-mode review
uv run glassbox branch-search start <session-id> --objective "Compare v9 dogfooding follow-up approaches" --strategy "docs-only summary" --strategy "eval recommendation follow-up" --strategy "release residual-risk note" --max-candidates 3 --json --cwd . --db-path .glassbox/dogfooding/v9/20260429-1400-branch-search-plan/glassbox.sqlite3
uv run glassbox branch-search needs-review <search-id> <candidate-id> --reason "Candidate needs a concrete eval/test path before v9 signoff" --cwd . --db-path .glassbox/dogfooding/v9/20260429-1400-branch-search-plan/glassbox.sqlite3
uv run glassbox branch-search select <search-id> <candidate-id> --reason "Bounded docs summary best matches GBX-981 scope" --cwd . --db-path .glassbox/dogfooding/v9/20260429-1400-branch-search-plan/glassbox.sqlite3
uv run glassbox branch-search show <search-id> --cwd . --db-path .glassbox/dogfooding/v9/20260429-1400-branch-search-plan/glassbox.sqlite3
```

Sanitized result:

- A parent session can be created without submitting a provider prompt, which
  is useful for deterministic branch-search command testing.
- Branch-search start, review marking, selection, and final show output worked
  and retained candidate status transitions.
- The human output after selection says `Marked candidate ... as select`; the
  final show output uses `selected`. The workflow is correct, but the verb is a
  small copy polish candidate.

## Friction Findings

| Area | Finding | Severity | Candidate Disposition |
| --- | --- | --- | --- |
| onboarding | The daily command guide helped recover from the `repository` versus `repo` command-name mismatch, but the alias mismatch is easy to hit when reading prose aloud. | low | docs or accepted residual risk |
| terminal | Branch-search selection output says `as select` instead of `as selected`. | low | fix |
| dashboard | No dashboard/browser pass was retained in GBX-981; dashboard cockpit manual evidence remains for GBX-992. | medium | accepted residual risk for GBX-981, covered by GBX-992 |
| provider | Streaming provider canary passed with redacted evidence, but the scenario object reported `final_status` as `running` while `outcome` was `passed`. | medium | fix or test |
| verification | `eval recommend` produced no recommendation for docs plus docs-guardrail tests, leaving focused validation choice outside Glassbox guidance. | medium | docs or eval recommendation rule |
| memory/index | Repository-index stale next actions were clear. Source search worked after rebuild; docs terms were not indexed, which should be clearer if docs are intentionally out of scope. | low | docs |
| recovery | No stale daemon, failed job, projection rebuild, or artifact-pressure recovery path was triggered in these passes. | low | accepted residual risk for GBX-981, covered by GBX-992 |

## GBX-982 Triage And Dispositions

| Area | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| onboarding | `repo` versus `repository` is easy to guess wrong even though command discovery recovers well. | Accepted residual risk for v9; current command guide and quickstart use `repo index` consistently, and adding an alias would expand command surface late in v9. | `glassbox command guide --json`; [docs/daily-workflow-quickstart.md](./daily-workflow-quickstart.md) |
| terminal | Branch-search selection output said `as select` instead of `as selected`. | Fixed in GBX-982. | `src/glassbox/cli/branch_search_commands.py`; `tests/integration/test_cli_branch_search_commands.py::test_branch_search_select_reject_and_needs_review_are_projected` |
| dashboard | No browser/dashboard pass was retained in GBX-981. | Accepted residual risk for this dogfooding phase; dashboard cockpit evidence is explicitly covered by GBX-992 before release signoff. | [tasks-v9.md](./tasks-v9.md) GBX-992 |
| provider | Streaming provider canary passed but retained `final_status` as `running`. | Fixed in GBX-982 by deriving automated canary final status from terminal turn events before falling back to session state. | `src/glassbox/runtime/provider_canary.py`; `tests/integration/test_provider_mode_runtime.py::test_provider_canary_runs_default_multi_scenario_with_fake_provider` |
| verification | `eval recommend` produced no recommendation for docs plus docs-guardrail tests. | Documentation disposition for v9; deterministic replay/eval impact remains source/runtime oriented, and docs guardrail tests stay operator-selected until a future impact-rule task is scoped. | This summary and [dogfooding.md](./dogfooding.md) record docs/test validation expectations. |
| memory/index | Source search worked after rebuild, while docs-only terms were not returned even though the broader index contract names documentation. | Post-v9 task candidate unless release signoff finds a blocking docs-index gap; current v9 use can rely on explicit docs links and command docs. | Candidate below: repository-index docs scope. |
| recovery | No stale daemon, failed job, projection rebuild, or artifact-pressure path was triggered. | Accepted residual risk for GBX-981; recovery manual validation remains part of GBX-992 release evidence. | [tasks-v9.md](./tasks-v9.md) GBX-992 |

## Candidate Eval Or Test Cases

- Provider canary summary consistency: a passed automated scenario should not
  retain a `final_status` that reads as still running unless the field is
  explicitly documented as session runtime state. Covered by
  `tests/integration/test_provider_mode_runtime.py::test_provider_canary_runs_default_multi_scenario_with_fake_provider`.
- Branch-search decision copy: selection confirmation should use the same
  selected-state language as `branch-search show`. Covered by
  `tests/integration/test_cli_branch_search_commands.py::test_branch_search_select_reject_and_needs_review_are_projected`.
- Eval recommendation docs guardrail: either recommend docs-focused checks for
  docs and docs-test paths, or document that `eval recommend` only covers
  replay/eval-impact surfaces.
- Repository-index docs scope: document whether docs are intentionally excluded
  from repository index search, or add a test if docs should be discoverable.

## GBX-982 Outcome

GBX-982 fixed the two high-signal low-risk implementation findings, added
focused regression coverage, and left the remaining findings as explicit docs,
accepted-risk, or post-v9 dispositions. No new replay/eval case was added
because the repeated deterministic regressions found in this pass were covered
more directly by existing integration tests.
