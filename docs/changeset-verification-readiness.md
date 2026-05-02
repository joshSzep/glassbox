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

## Readiness Versus Proof

Readiness answers whether the retained local evidence is enough to support
review posture. It does not prove that:

- a passing check covers every changed line
- a check is fresh when the inventory is stale
- a recommended command was safe to run
- skipped or accepted-risk evidence makes the change safe
- the changeset is ready to commit

Later v12 tasks attach stale-verification detection, plan preview, evidence
capture, CLI/API/dashboard surfacing, and commit readiness to this model.
