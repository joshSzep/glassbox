# Changeset Verification Readiness

Changeset verification readiness is the v12 review-time model for answering:
"what verification evidence supports this local change, and what is still
missing or stale?"

It is advisory posture, not proof. The model never runs commands, never stages
files, and never treats old passing checks as fresh when the change inventory is
stale.

## States

The model uses the changeset verification states already defined in canonical
events:

- `planned`: a command or check has been selected or recorded as intended, but
  no completed result is retained yet
- `missing`: a recommended or required check has no retained evidence
- `running`: retained task verification evidence says a check is currently
  running
- `passed`: retained evidence says the relevant check passed for the current
  requirement
- `failed`: retained evidence says a relevant check failed or was cancelled
- `stale`: the change inventory is stale or superseded, so verification cannot
  be treated as fresh for the current workspace
- `skipped`: retained evidence says a relevant check was skipped
- `accepted_with_risk`: retained evidence says residual verification risk was
  explicitly accepted
- `not_applicable`: no verification command is applicable, such as an inventory
  with no changed paths

Aggregation is conservative. `failed` outranks `stale`, then `running`,
`missing`, `planned`, `accepted_with_risk`, and `skipped`. Only when all
blocking requirements are passed does the aggregate state become `passed`.

## Inputs

The first implementation is deterministic and source-backed. It derives
requirements from:

- the latest change inventory artifact and its freshness
- changed paths, path risk, and inventory limitations
- task verification ledger entries
- eval recommendation reports, suggested commands, profiles, and verification
  recipes
- workspace profile eval defaults
- retained command evidence that records an intended verification command

Missing inputs degrade honestly. If inventory is missing, readiness is
`missing`. If inventory freshness is `unknown`, readiness names that gap and
starts with `glassbox changeset refresh <changeset-id> --cwd .`.

## Plan Preview And Evidence Capture

Operators can preview the intended verification plan without running anything:

```bash
glassbox changeset verification-plan <changeset-id> --cwd .
```

The preview names recommended commands, eval profiles, matching recipes,
reason groups, expected changed-path scope, retained verification artifact IDs,
affected topology components, and safe next actions. Commands are previews only;
execution remains an explicit shell or existing Glassbox workflow action.
Publish, deploy, push, and upload commands are filtered out of the changeset
verification plan.

When workspace topology has been built, the preview also includes
`topology_impacts`: affected component IDs, package/app/docs names, matched
paths, test roots, owner hints, dependency hints, topology freshness, and any
limitations. Stale topology remains visible with degraded posture and rebuild
guidance instead of being presented as current subsystem authority.

When a task verification ledger already contains the operator-selected evidence,
the posture can be recorded on the changeset:

```bash
glassbox changeset record-verification <changeset-id> \
  --verification <verification-id> --cwd .
```

This records a `ChangesetVerificationPostureUpdated` event from existing task
verification evidence. It does not run commands, stage files, commit, push, or
rewrite the verification ledger. Retained task output artifacts stay referenced
by artifact ID so later review surfaces can cite them without flattening raw
logs into the changeset summary.

## Ready-To-Review Surfacing

`glassbox changeset show <changeset-id> --cwd .` includes verification
readiness beside the retained verification posture. Text output lists the
aggregate state, failed/stale/missing/accepted-risk counts, the first
requirements, and safe next actions. JSON output includes a
`verification_plan` object with the same preview payload exposed through the
API.

The dashboard changeset detail view renders a verification panel from
`/changesets/{id}/verification-plan`. The panel keeps failed, stale, missing,
and accepted-risk states visible together with safe inspection or verification
commands. It also renders affected subsystems when topology evidence is
available, so reviewers can see which package, app, test roots, owners, or
dependency hints are implicated before choosing checks. Inventory freshness is
checked against the current workspace before rendering readiness, so a workspace
diff that changes after a recorded verification can make the displayed
readiness stale even when the latest recorded posture was previously `passed`.

## Stale Verification

The first stale-verification boundary is sequence- and path-aware. When a
passed task-ledger check predates the latest inventory refresh and the check's
recorded `changed_paths` overlap the current inventory paths, readiness marks
that requirement as `stale`. This prevents a check that passed before a relevant
file changed from making the changeset look review-ready.

When precise path mapping is unavailable, the model does not invent staleness.
Profile-level checks or command evidence without changed-path links remain
lower-confidence evidence until later v12 tasks add richer file digest or
source-range mapping.

## Readiness Versus Proof

Readiness answers whether the retained local evidence is enough to support
review posture. It does not prove that:

- a passing check covers every changed line
- a check is fresh when the inventory is stale
- a profile-level check without path links is fresh for every changed path
- a recommended command was safe to run
- skipped or accepted-risk evidence makes the change safe
- the changeset is ready to commit

Later v12 tasks attach dashboard-ready review posture, review briefs, and commit
readiness to this model.
