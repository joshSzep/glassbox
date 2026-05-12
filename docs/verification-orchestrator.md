# Verification Orchestrator Contract

The v16 verification orchestrator treats verification as a local, reviewable
workflow. Planning may recommend checks, explain why they matter, and name
evidence gaps. Planning must not claim a command has run, passed, or been
approved.

## Lifecycle States

Verification plan entries use `VerificationPlanLifecycleState`:

- `proposed`: a planner found a useful check, but the operator has not selected
  it.
- `selected`: the operator or profile selected the check for this plan.
- `running`: command execution has started and should be backed by canonical
  task verification events.
- `passed`: retained evidence says the selected check passed.
- `failed`: retained evidence says the selected check failed.
- `skipped`: the check was intentionally skipped and must not be represented as
  passing.
- `stale`: prior evidence exists, but changed inputs or freshness policy make it
  insufficient.
- `superseded`: a newer verification entry replaces this one.
- `accepted-risk`: the operator accepted residual risk instead of requiring a
  fresh pass.
- `manual-only`: the required evidence is manual, browser, accessibility, live
  provider, or another non-command check.
- `blocked`: the check cannot proceed until a prerequisite is resolved.

## Entry Fields

`VerificationPlanEntry` remains compatible with existing task verification
events and adds:

- `lifecycle_state`
- `target`
- `command_recipe`
- `selection_rationale`
- `release_surfaces`
- `evidence_references`
- `stale_reasons`
- `manual_evidence_required`
- `execution_requires_approval`
- `superseded_by_verification_id`

Existing `command`, `source`, `rationale`, eval IDs, changed paths, timeout, and
expected-exit-code fields remain valid.

## Planning Versus Execution

Planning may read local inventory, repository intelligence, eval metadata,
command recipes, readiness state, and stale evidence. It may produce proposed or
selected plan entries and explain limitations. It may not run commands, mutate
workspace files, mark a check passed, or accept risk.

Execution requires the normal command policy path and, when applicable,
operator approval. A skipped check remains skipped. Accepted risk must name its
rationale and scope through canonical evidence. Manual-only checks require
manual evidence and must stay separate from deterministic command results.

## Preview Generation

`glassbox changeset verification-plan CHANGESET_ID --cwd .` now returns a
preview-only plan with explicit `plan_entries` and `skipped_checks` beside the
existing readiness summary, recommended commands, eval profiles, recipes,
release surfaces, stale evidence, limitations, safe next actions, and
non-claims. The corresponding dashboard/API route exposes the same plan-entry
lifecycle, source, command recipe, evidence references, stale reasons, changed
paths, eval target IDs, release surfaces, and manual-evidence posture.

Operators can also preview an unpersisted changed-path set with repeated
`--path` arguments:

```bash
glassbox changeset verification-plan --path src/glassbox/runtime/foo.py --cwd .
```

Path previews are planning-only. They may use repository intelligence, eval
metadata, command recipes, and advisory/manual-evidence heuristics, but they do
not create a changeset, record events, run commands, select checks, mark checks
passed, or approve any command. Persisted changeset previews remain the
reviewable route when retained inventory, review feedback, manual evidence, and
handoff posture matter.

## Scale Behavior

Verification plan previews cap generated entry summaries to 50 rows. When more
candidate checks are available, the preview records a skipped-check row with
reason `plan-entry-limit` so the operator can see that the plan is truncated
instead of mistaking it for exhaustive evidence. Skipped advisory checks are
also bounded; if that list exceeds the retained preview rows, Glassbox records
`skipped-check-limit`.

The cap applies to preview and dashboard payloads only. It does not approve,
run, pass, fail, or discard underlying commands. Operators can inspect
repository recommendations or use narrower changed-path scopes when they need
to review additional candidate checks.

The repository-owned `glassbox performance budgets` output includes a v16
verification plan generation row and a verification plan preview payload row.
Budget failures should be addressed by keeping preview entries bounded and
moving expanded recommendation detail behind explicit inspection commands.

## Local Dispositions

Once a changeset preview names a `verification_id`, operators can persist local
decisions about that entry:

```bash
glassbox changeset verification-select CHANGESET_ID --verification VERIFICATION_ID --cwd .
glassbox changeset verification-skip CHANGESET_ID --verification VERIFICATION_ID --reason "why skipped" --cwd .
glassbox changeset verification-accept-risk CHANGESET_ID --verification VERIFICATION_ID --reason "why accepted" --risk "remaining risk" --cwd .
glassbox changeset verification-supersede CHANGESET_ID --verification OLD_ID --replacement NEW_ID --reason "why replaced" --cwd .
```

These commands append canonical task verification events for task-backed
changesets. Selection records `TaskVerificationPlanned`; skips add
`TaskVerificationSkipped`; accepted risk adds
`TaskVerificationResidualRiskAccepted`; superseding records retry/supersede
evidence and plans the replacement. They do not execute commands, treat skipped
checks as passed, publish evidence, or grant release approval.

## Selected Command Execution

After inspecting and selecting a command-backed plan entry, operators can run
exactly that entry with explicit confirmation:

```bash
glassbox changeset verification-run CHANGESET_ID --verification VERIFICATION_ID --confirm --cwd .
```

`verification-run` only accepts task-backed changesets with a selected command
entry. It applies the existing hard command-risk blocklist before execution, so
publish, deploy, destructive, and remote git mutation commands are recorded as
policy-blocked verification failures instead of being run. Allowed commands run
through the local command tool, stream `TaskVerificationStreamed` events, retain
the captured output artifact, and append tool-attempt heartbeat evidence with
command purpose, environment summary, and retry guidance. Passing commands record
`TaskVerificationCompleted`; failed or timed-out commands record
`TaskVerificationFailed`. This remains local verification evidence, not reviewer
approval, publication, deployment, or release authorization.

## Plan Lifecycle Story

Changeset detail, verification-plan previews, review briefs, handoff readiness,
and dashboard API responses now include the same bounded verification plan
lifecycle summary. The summary reports selected, running, passed, failed,
skipped, stale, manual-only, and accepted-risk counts plus compact per-check
rows with command identity, artifact references, stale reasons, and risk
dispositions. It deliberately omits raw command logs; those remain in retained
artifacts and command-evidence views. A passed plan summary is local evidence
only and does not imply reviewer acceptance, publication readiness, deployment,
or release approval.
