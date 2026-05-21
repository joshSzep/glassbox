# V17 Dogfooding Summary

This document records the sanitized `GBX-1763` dogfooding pass for the v17
local-handoff milestone. The goal was to exercise recipient intent, redaction
preview, local-only inventory, import triage, custody decisions, guidance, and
release-signoff posture on real local handoff flows before publishing the v17
release-candidate guide.

Retained local evidence was written under:

```text
.glassbox/releases/gbx-1763-v17-dogfooding/
```

Raw `.glassbox` state, SQLite stores, package JSON, Markdown handoff summaries,
and release-gate summaries are intentionally local and uncommitted. The
reviewer-safe outcomes, friction findings, accepted risks, and bounded
follow-ups are summarized here.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Local session seed | `uv run glassbox session run "Dogfood GBX-1763 v17 local handoff evidence" --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3 --model-name local-test-model --approval-mode review --autonomy-mode guided` | Passed | Created retained local session `9cf2289e-31c0-4199-bef5-c44808089639` without live provider credentials. |
| Future-self preview | `uv run glassbox handoff prepare session 9cf2289e-31c0-4199-bef5-c44808089639 --preview --intent future-self --recipient future-operator --exported-by dogfood-operator --expected-custodian future-operator --note "future-self continuation preview with local-only evidence visible" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed | Preview reported reviewer-safe redaction, two local-only artifact references, seven total local-only inventory items, and safe inspection commands without writing a package. |
| Review-only export | `uv run glassbox handoff prepare session 9cf2289e-31c0-4199-bef5-c44808089639 .glassbox/releases/gbx-1763-v17-dogfooding/review-only-handoff.json --markdown-output .glassbox/releases/gbx-1763-v17-dogfooding/review-only-handoff.md --intent review-only --recipient reviewer --exported-by dogfood-operator --expected-custodian reviewer --note "review-only handoff should not imply continuation authority" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed | Wrote local JSON and Markdown package artifacts. The Markdown summary kept objective, evidence included, local-only inventory, stale or missing evidence, safe commands, recipient checklist, non-claims, and redaction summary visible. |
| Package JSON inspection | `uv run glassbox handoff inspect .glassbox/releases/gbx-1763-v17-dogfooding/review-only-handoff.json --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed, follow-up found | Import triage stayed inspection-first and non-mutating, but classified the exported session package as `legacy-inspection-only` and reported missing v17 digest/local-only summaries. |
| Package Markdown inspection | `uv run glassbox handoff inspect .glassbox/releases/gbx-1763-v17-dogfooding/review-only-handoff.json --markdown --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed | Rendered the richer review-only Markdown view with the expected non-claim that review-only is not approval to continue work. |
| Import triage and inspection-only import | `uv run glassbox handoff import .glassbox/releases/gbx-1763-v17-dogfooding/review-only-handoff.json --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/imported.sqlite3` | Passed | Created historical imported session `05a03ba0-9dda-4263-9c6d-d9d0a3f34842` with `resumable: false`, six imported events, and no live continuation. |
| Imported handoff list | `uv run glassbox handoff list --include-archived --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/imported.sqlite3` | Passed | Reported package `pkg-220eeb63aaa3127974499733` as `imported-inspected`, `awaiting-recipient`, and `legacy-inspection-only`. |
| Verification-needed readiness | `uv run glassbox session handoff-readiness 9cf2289e-31c0-4199-bef5-c44808089639 --intent verification-needed --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed, not ready | Returned `needs-verification` with unknown confidence, missing checkpoint evidence, safe inspection commands, and non-claims against resume, fork, approval, staging, commit, push, merge, deploy, or publication. |
| Fork-or-continue guidance | `uv run glassbox handoff guidance 05a03ba0-9dda-4263-9c6d-d9d0a3f34842 pkg-220eeb63aaa3127974499733 --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/imported.sqlite3` | Passed | Recommended `inspect-only`, listed fork, new-session, verify, and reject as explicit mutation paths, and named a low-severity missing package-artifact blocker. |
| Custody acceptance | `uv run glassbox handoff accept 05a03ba0-9dda-4263-9c6d-d9d0a3f34842 pkg-220eeb63aaa3127974499733 --accepted-by dogfood-recipient --follow-up-intent verification-needed --reason "accepted for verification-needed inspection follow-up" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/imported.sqlite3` | Passed | Recorded `ImportedHandoffAcceptedForFollowUp` with `accepted-needs-follow-up` and non-claims that custody is workflow metadata, not authorization, approval, or runtime ownership transfer. |
| Custody rejection | `uv run glassbox handoff reject 05a03ba0-9dda-4263-9c6d-d9d0a3f34842 pkg-220eeb63aaa3127974499733 --rejected-by dogfood-recipient --reason "package was legacy-inspection-only and lacked v17 digest/local-only summaries" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/imported.sqlite3` | Passed | Recorded `HandoffCustodyRejected`, preserved the rejection reason, and left safe next action as inspection of the handoff record. |
| Failure-triage preview | `uv run glassbox handoff prepare session 9cf2289e-31c0-4199-bef5-c44808089639 --preview --intent failure-triage --recipient triage-operator --exported-by dogfood-operator --expected-custodian triage-operator --note "failure-triage preview should expose missing local-only evidence before action" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed | Required `failure_posture`, kept recipient next action as inspection before repair, and preserved the same local-only and redaction boundaries. |
| Release-signoff package preview | `uv run glassbox handoff prepare session 9cf2289e-31c0-4199-bef5-c44808089639 --preview --intent release-signoff --recipient release-custodian --exported-by dogfood-operator --expected-custodian release-custodian --note "release-signoff handoff remains advisory and inspection-first" --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed | Required `release_evidence`, included the non-claim that release-signoff is not publication approval, and kept local-only release evidence advisory. |
| Workspace handoff readiness | `uv run glassbox observability handoff-readiness --source workspace --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed, degraded but readable | Returned `ready` with high confidence while clearly naming missing repository index evidence, local-only managed artifacts, provider-canary advisory evidence, and read-only safe commands. |
| Release handoff readiness | `uv run glassbox observability handoff-readiness --source release --json --cwd . --db-path .glassbox/releases/gbx-1763-v17-dogfooding/glassbox.sqlite3` | Passed, needs verification | Returned `needs-verification` because release-surface intelligence was missing and provider-canary evidence was stale. The summary still found fresh retained eval evidence and kept release handoff separate from publication approval. |
| Focused v17 handoff checks | `uv run pytest tests/unit/test_handoff_redaction_preview.py tests/unit/test_handoff_import_triage.py tests/unit/test_handoff_decisions.py tests/unit/test_handoff_guidance.py tests/unit/test_task_handoff_readiness.py tests/unit/test_session_handoff_readiness.py tests/unit/test_workspace_handoff_readiness.py tests/integration/test_cli_handoff_commands.py -q` | Passed | `35 passed`; covers preview, local-only inventory, import triage, custody, fork-or-continue guidance, and session/task/workspace readiness surfaces. |
| Handoff command discovery | `uv run glassbox handoff --help` | Passed | Listed `prepare`, `inspect`, `import`, `list`, `show`, `guidance`, `accept`, `reject`, and `archive` under the local workflow metadata description. |
| V17 release gate dry run | `uv run python scripts/validate_v17_release_gate.py --dry-run --evidence-dir .glassbox/releases/gbx-1763-v17-dogfooding/v17-gate-dry-run` | Passed | Planned 105 blocking deterministic stages and separated advisory provider, dashboard browser, accessibility, dogfooding, and manual release evidence. |

## Findings

### Fix Now

- No product-code release blocker was found during the dogfooding pass.
- The committed fix for this task is documentation and evidence hygiene:
  summarize retained local evidence, mark `GBX-1763` complete, and keep raw
  handoff packages, SQLite stores, release summaries, and Markdown exports out
  of the repository.

### Docs

- The supported recipient intents are understandable in practice. The preview
  output names intent-specific required sections such as `future_self_context`,
  `failure_posture`, and `release_evidence`, and the Markdown export keeps
  recipient checklist and non-claims close to the evidence.
- The import path is calmer than a blind package load: inspection reports safe
  first commands, compatibility posture, limitations, and recommended
  disposition before the package becomes historical local state.
- Release-signoff copy needs to keep saying the quiet part loudly: handoff can
  carry release evidence posture, but it is not release approval, publication,
  deployment, staging, committing, pushing, tagging, or maintainer signoff.
- The local-only inventory is especially useful when the source session has
  artifact references. It showed what existed, what stayed local, and what a
  recipient cannot verify from the package alone.

### Tests And Evals

- Existing deterministic v17 fixtures cover prepare preview, import triage,
  custody decisions, and reviewer-safe bundles.
- Focused runtime and CLI tests passed for redaction preview, local-only
  inventory, import triage, custody decisions, fork-or-continue guidance, and
  session/task/workspace readiness.
- The v17 release gate dry run confirms the full deterministic release path is
  wired, but this task intentionally did not run the full gate. Full execution
  belongs to `GBX-1764` release-candidate signoff.

### Accepted Risks

- The dogfooding session used `local-test-model`, not a live provider. This
  keeps raw provider output and secrets out of the evidence, but it does not
  prove live model handoff behavior.
- The exported session package can render rich review-only Markdown, but
  `handoff inspect --json` currently classifies it as `legacy-inspection-only`
  and says v17 digest/local-only summaries are absent. Import remains safe and
  inspection-only, so this is accepted as a bounded post-v17 follow-up unless a
  release custodian chooses to promote it before signoff.
- Workspace readiness was `ready` despite missing repository index evidence
  because the readiness model kept the missing index explicit and advisory.
- Release readiness was correctly `needs-verification`; release-surface
  intelligence was missing and provider-canary evidence was stale.
- The imported package was accepted for follow-up and then rejected in the same
  isolated store to exercise both custody paths. Those local workflow decisions
  are evidence records, not contradictory release decisions.
- The pass made no staging, commit, push, pull request, merge, deploy, package
  publication, release approval, or runtime ownership claim.

### Post-V17 Follow-Ups

- Align session handoff export metadata with `handoff inspect --json` so a v17
  package exported through `handoff prepare session` is not presented as
  `legacy-inspection-only` when richer profile, Markdown, and local-only
  inventory data exists.
- Consider linking exported package artifacts into the custody projection when
  packages are imported from local paths, so guidance can avoid the
  `missing-package-artifact` blocker for an otherwise inspectable local file.
- Consider adding a compact release-custodian walkthrough that starts with
  `observability handoff-readiness --source release`, then points to eval audit,
  package smoke, installed smoke, and advisory evidence review.
- Consider a deterministic fixture for unsupported or stale imported packages
  if the release candidate needs stronger regression coverage around rejected
  handoffs.

## Residual Risks

- Live provider handoff and provider-canary freshness remain advisory evidence
  unless promoted through deterministic fixtures.
- Dashboard browser and accessibility evidence remains advisory and is covered
  by the release gate as planned, not by this local CLI dogfooding pass.
- Package JSON, Markdown summaries, imported SQLite state, and gate summaries
  can contain local paths or historical session details. They are retained
  locally and should not be committed.
- Handoff readiness can be high-confidence for workspace continuation while
  still naming missing advisory evidence. Operators must inspect limitations,
  not only the top-level state.
- Release handoff is still a human workflow expectation, not an approval or
  publication mechanism.

## Disposition

The dogfooding pass found no v17 release blocker. It confirmed that local
handoff now gives recipients a clearer inspection-first story: intent is
explicit, local-only evidence is visible before export, packages can be
triaged before import, imported sessions stay inspection-only, custody
decisions are auditable local workflow metadata, and release-signoff posture
does not blur into publication authority.

The remaining findings are bounded residual risks or post-v17 polish items,
with one especially visible follow-up around aligning session package export
metadata with `handoff inspect --json`.
