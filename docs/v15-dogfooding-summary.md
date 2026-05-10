# V15 Dogfooding Summary

This document records the sanitized `GBX-1582` dogfooding pass for the v15
repository-intelligence milestone. The goal was to exercise repository
intelligence v2 on real local work before publishing the v15 release-candidate
guide.

Retained local evidence was written under:

```text
.glassbox/releases/gbx-1582-v15-dogfooding/
```

Raw `.glassbox` state, repository snapshots, workspace topology, eval
artifacts, and changeset records are intentionally local and uncommitted.
Reviewer-safe outcomes and friction findings are summarized here.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Repository snapshot rebuild | `uv run glassbox repo refresh --json --cwd .` | Passed | Rebuilt `.glassbox/repository-index.json` and `.glassbox/workspace-topology.json` with schema version 2, 1,210 source files, 11,412 entries, 97 command recipes, 14 subsystems, 14 ownership hints, 17 policy-sensitive paths, 4 release surfaces, and 40 topology dependencies. |
| Concurrent stale read | `uv run glassbox repo status --json --cwd .` during refresh | Advisory friction | Reads started before refresh completed observed stale v1 or missing topology state. The stale posture was surfaced instead of silently claiming fresh evidence. |
| Repository status after refresh | `uv run glassbox repo status --json --cwd .` | Passed | Reported fresh repository index and fresh workspace topology for the current source digest. Missing memory-derived entries remained advisory only. |
| Path inspection | `uv run glassbox repo path src/glassbox/runtime/repository_intelligence_queries.py --json --cwd .` | Passed | Returned fresh package, source-root, Runtime subsystem, owner-hint, command-recipe, and release-surface guidance for the runtime path. |
| Verification recommendation | `uv run glassbox repo recommend src/glassbox/runtime/repository_intelligence_queries.py docs/v15-release-gate.md --json --cwd .` | Passed | Recommended the five v15 repository-intelligence cases, release-candidate profile, v15 runtime tests, docs guardrail, package checks, lint, typecheck, and topology fallbacks with fresh source metadata. |
| Stale intelligence recovery | `uv run glassbox repo stale --json --cwd .` | Passed | After refresh, the only remaining cue was missing optional memory-derived entries. The recommended safe next actions stayed inspection and refresh oriented. |
| Session discovery for memory review | `uv run glassbox session list --json --cwd .` | Passed | Found local sessions suitable for explicit memory-candidate review. The output is retained locally because summaries can include historical user and assistant text. |
| Memory candidates without session | `uv run glassbox repo memory-candidates --limit 5 --json --cwd .` | Fixed in post-v15 refactor | GBX-R712 now fails with explicit `--session SESSION_ID` guidance and points operators to `glassbox session list --json --cwd .`. |
| Memory candidates with session | `uv run glassbox repo memory-candidates --session 27b0b5ed-e48f-485e-a9a5-8a6880eb4446 --limit 5 --json --cwd .` | Passed | Returned review-gated repository command candidates with repository-intelligence provenance, fresh snapshot digest notes, command tags, and redaction for one v15 advisory profile token. |
| Turn-context eval inspection | `uv run glassbox eval run repository-intelligence.context-drift --cwd .` | Passed | Exact match for the context-drift case with retained eval artifacts under `.glassbox/evals/20260510T160910Z`. |
| Turn-context and replay tests | `uv run pytest tests/unit/test_context_builder.py tests/unit/test_replay_orchestrator.py -q` | `41 passed` | Retained focused confidence for context construction and replay orchestration while dogfooding repository-intelligence context guidance. |
| Dashboard console tests | `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx workspace-overview.test.tsx changeset-console.test.tsx verification-cues.test.ts` | Passed | Deterministic dashboard confidence for repository, workspace, changeset, and verification cues passed with 130 frontend tests. |
| Changeset session seed | `uv run glassbox session run "Dogfood GBX-1582 v15 repository intelligence evidence" --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3 --model-name local-test-model --approval-mode review --autonomy-mode guided` | Passed | Created retained local session `38f6057a-62f2-4ca2-9e31-65ea8dccbb34` without live provider credentials. |
| Changeset review create | `uv run glassbox changeset create --from workspace-diff --session 38f6057a-62f2-4ca2-9e31-65ea8dccbb34 --objective "Dogfood GBX-1582 v15 repository intelligence evidence" --json --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed | Created changeset `027f1a20-6549-4f0a-a213-0f3332cd1c4e`; output was conservative because the session was running and the workspace diff was local. |
| Changeset verification before inventory | `uv run glassbox changeset verification-plan 027f1a20-6549-4f0a-a213-0f3332cd1c4e --json --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed, conservative | Reported missing verification readiness until a structured inventory was attached. |
| Changeset inventory refresh | `uv run glassbox changeset refresh 027f1a20-6549-4f0a-a213-0f3332cd1c4e --json --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed | Final inventory artifact `9b3031a8-3266-43de-9cbf-41e66125c7ca` covered 13 changed paths, with high risk from docs, missing provenance, packaging release, policy-sensitive, and runtime schema changes. |
| Changeset verification after inventory | `uv run glassbox changeset verification-plan 027f1a20-6549-4f0a-a213-0f3332cd1c4e --json --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed | Produced fresh topology impacts, 26 recommended targets, 18 recipes, 4 release surfaces, and 38 missing verification requirements without validation overflow. |
| Lifecycle brief | `uv run glassbox changeset brief 027f1a20-6549-4f0a-a213-0f3332cd1c4e --format markdown --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed | Generated review brief artifact `6589b549-6807-4f13-8661-0e9a88edc8d4` with 20 bounded safe inspection commands and explicit non-publication claims. |
| Handoff readiness | `uv run glassbox changeset handoff-readiness 027f1a20-6549-4f0a-a213-0f3332cd1c4e --json --cwd . --db-path .glassbox/releases/gbx-1582-v15-dogfooding/glassbox.sqlite3` | Passed, not ready | Reported `needs_verification`, untracked workspace state, 13 unresolved risks, and no staging, commit, push, PR, merge, deploy, or publication claims. |
| Requirement-id overflow regression | `uv run pytest tests/unit/test_changeset_verification_readiness.py -q` | `11 passed` | Added coverage for repository-intelligence requirement IDs over 200 characters and aggregate safe-next-action overflow. |
| Review-brief safe-command regression | `uv run pytest tests/unit/test_review_briefs.py tests/unit/test_changeset_verification_readiness.py -q` | `21 passed` | Added coverage that lifecycle brief safe inspection commands remain within the 20-item artifact cap. |
| V15 release gate dry run | `uv run python scripts/validate_v15_release_gate.py --dry-run --evidence-dir .glassbox/releases/gbx-1582-v15-dogfooding/v15-gate-dry-run` | Passed | Dry run now records dogfooding as advisory `recorded` evidence beside deterministic blocking gate stages. |

## Findings

### Snapshot And Freshness

- Repository snapshot rebuild worked on the full Glassbox repository and
  produced a fresh v2 index plus fresh workspace topology.
- Concurrent readers that started before `repo refresh` completed saw stale or
  missing state. That is acceptable for v15 because the output remained
  explicit about stale posture, but operators should prefer refresh completion
  before capturing release evidence.
- Freshness recovery was clear after the rebuild. `repo stale` degraded only on
  missing optional memory-derived entries, not on source digest or topology
  mismatch.

### Path-To-Verification Guidance

- Path inspection returned package, subsystem, owner, command, and release
  surface hints for runtime code without claiming a human reviewer requirement.
- Recommendation output mapped mixed runtime and release-gate docs paths to the
  five v15 repository-intelligence eval cases, release-candidate profile,
  docs guardrail, package checks, lint, typecheck, and topology fallback.
- Repository-intelligence guidance stayed advisory. Deterministic tests, evals,
  packaging checks, and the v15 gate remain the release authority.

### Memory Candidate Review

- `repo memory-candidates` works when the operator supplies `--session`.
  Candidates retain repository-intelligence provenance, command tags, fresh
  snapshot notes, and redaction.
- Running the command without `--session` originally returned
  `unknown session_id: None`. GBX-R712 keeps the command safe while making the
  failure actionable: operators now get explicit `--session SESSION_ID`
  guidance and the `glassbox session list --json --cwd .` discovery command.
- Session list output can contain historical prompt and assistant summaries, so
  this summary records only sanitized IDs and aggregate behavior.

### Turn Context And Replay

- The `repository-intelligence.context-drift` eval passed as an exact match.
  The pass confirmed that repository-intelligence context remains source-level
  evidence and does not convert cancellation or replay details into failure.
- Focused context and replay unit tests passed, keeping the dogfooding evidence
  tied to deterministic turn-context and replay contracts.

### Dashboard And Changeset Surfaces

- Dashboard confidence for this phase is deterministic frontend coverage plus
  retained `GBX-1554` advisory dashboard and accessibility evidence. Live
  browser evidence remains advisory unless captured separately.
- The changeset pass is intentionally local and summary-only. It is meant to
  check that repository-intelligence changes appear in reviewer workflows
  without publishing raw diffs or treating local evidence as approval.
- Dogfooding found and fixed two bounded-output bugs before signoff:
  repository-intelligence-derived changeset verification requirement IDs can
  exceed the 200-character model limit, and lifecycle brief safe inspection
  commands can exceed the 20-item artifact cap. Both are now bounded with
  focused regression tests.
- After the fixes, verification preview, lifecycle brief, and handoff readiness
  all completed against the real 13-path GBX-1582 diff. Handoff stayed
  conservative because retained verification was missing, risks were unresolved,
  and the workspace had untracked local dogfooding files.

## Disposition

The dogfooding pass found no v15 release blocker. It found these bounded
follow-ups:

- document that release evidence should wait for `repo refresh` completion when
  a refresh and read commands are started together
- keep session-list evidence local because historical prompt summaries can be
  sensitive even when command output is structurally useful

The pass also produced these completed fixes:

- bounded generated changeset verification requirement IDs with stable SHA-256
  suffixes when repository-intelligence recipe or command text would exceed the
  model limit
- bounded lifecycle brief safe inspection commands to the 20-item artifact cap
  while preserving detailed per-requirement guidance in the verification plan

The remaining observations are accepted advisory limits for v15:

- repository intelligence remains advisory and cannot replace deterministic
  tests, evals, package checks, or release gates
- missing memory-derived entries degrade confidence only; they do not block
  repository snapshot, topology, path, or recommendation evidence
- live dashboard/browser/accessibility evidence for the dogfooding changeset is
  advisory; deterministic frontend tests and retained `GBX-1554` evidence are
  the bounded confidence path
