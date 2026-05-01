# Team Workflow And Session Handoff

Glassbox v2 remains local-first: one workspace, one event-sourced session store,
and one authoritative runtime owner for live mutation. Team workflow support does
not turn Glassbox into a remote multi-user platform. It defines how operators can
inspect, act on, and hand off persisted sessions without losing auditability.

This document is the `GBX-350` contract for ownership, identity, and handoff. It
is the baseline for portable session export/import and workspace defaults work.

## Vocabulary

- **runtime owner**: the foreground `chat` process or workspace daemon that may
  execute live turns, resume suspended tool calls, and append canonical events
  for a live session.
- **acting operator**: the local human or automation identity that submits an
  intervention such as a prompt, answer, approval decision, denial, fork request,
  or handoff note.
- **session custodian**: the operator currently expected to notice and resolve
  actionable states for a session. Custody is a workflow expectation, not an
  exclusive lock.
- **handoff**: an explicit transfer of custodial context for a paused,
  actionable, failed, or historical session.
- **intervention**: any operator-originated action that can affect subsequent
  session behavior or reviewer interpretation.

Runtime ownership and session custody are different concerns. Runtime ownership
prevents conflicting writers. Session custody tells operators who is expected to
act next.

## Identity Model

Operator identity is local, inspectable metadata. It is not authentication,
authorization, or a cloud account.

The v2 identity contract is:

- every operator-originated intervention should be attributable when that
  attribution affects audit or handoff reasoning
- the identity value should be stable enough for humans to recognize in local
  artifacts, CLI output, dashboard rows, and exported session packages
- the default identity may be inferred from the local environment, but command
  surfaces that create portable handoff artifacts should allow an explicit
  operator label
- identity metadata must not grant permissions by itself; policy and approval
  semantics remain separate

The canonical shape for future event or artifact metadata is:

```text
operator_id: stable local identifier, for example alice or alice@example.test
operator_display_name: optional human label
operator_source: cli, dashboard, daemon, imported, or automation
```

Current single-operator workflows remain compatible by treating interventions as
coming from the implicit local operator when no explicit identity is supplied.

## Session Ownership Model

Glassbox keeps one authoritative mutation path for a workspace at a time:

- embedded mode: `glassbox session chat` owns the live runtime in the current process
- daemon mode: `glassbox daemon start` owns live mutation for the workspace
- historical mode: completed, failed, cancelled, and exported sessions are
  inspectable from persisted events, but they do not have a live runtime owner

Mutating commands must continue to respect the runtime-owner boundary described
in [interactive-workflows.md](./interactive-workflows.md) and
[persistent-runtime.md](./persistent-runtime.md). When a daemon owns the
workspace, local commands that would append or resume session state should route
through `attach` or fail visibly rather than creating a second writer.

Session custody is softer:

- an actionable session may have an expected custodian in docs, dashboard copy,
  export metadata, or future handoff notes
- custody does not override runtime-owner checks
- changing custody should be auditable when it changes who is expected to
  resolve a pending approval, answer a question, triage a failure, or continue a
  branch

## Intervention Attribution

The following operator actions materially affect audit reasoning and should carry
operator identity metadata in future event payloads or associated metadata:

- sending a prompt with `chat`, `message`, browser actions, or daemon-backed
  `attach`
- answering an `ask_user` question
- approving or denying a pending approval
- resuming a paused session after inspection
- forking a session or creating a child branch
- adding a handoff note or changing session custody
- importing a portable session package as inspectable or resumable local state

Read-only inspection does not need per-event attribution. Opening a dashboard,
running `status`, inspecting replay artifacts, or viewing historical transcripts
does not change session behavior and should not add noise to the event log.

## Handoff Model

A useful handoff should answer four questions without requiring access to the
originating terminal:

1. What session is being handed off?
2. Why does it need attention?
3. Who last acted, and who is expected to act next?
4. Is the recipient inspecting history, resolving a pause, or continuing live
   work?

Supported v2 handoff states are:

- **paused for approval**: include the pending approval ID, subject, policy
  reason, last acting operator, and expected next custodian
- **paused for answer**: include the pending question ID, prompt text or summary,
  last acting operator, and expected next custodian
- **idle running**: include the next-work summary and whether a live runtime
  owner is reachable
- **failed**: include failure summary, retryability, relevant artifacts, and the
  expected triage owner
- **historical-only**: include lineage, branchability, replay or eval relevance,
  and whether the recipient should fork instead of mutate the original session

Handoff should be explicit. A recipient should not have to infer from a copied
session ID whether they are expected to approve a command, answer a question,
inspect a failed turn, fork a branch, or merely review history.

Export a handoff package with:

```bash
uv run glassbox session export SESSION_ID handoff.json --cwd .
```

The package is an inspectable JSON file for review and handoff. It is distinct
from `replay bundle export`: session export carries redacted session metadata,
transcript, lineage, pending-action context, event summaries, retained artifact
references, and a `handoff.summary` block, while replay bundle export carries
deterministic execution fixtures for offline replay. Session export does not
include the SQLite database or embed artifact contents.

The `handoff.summary` block is the reviewer story. It names the latest
objective, checkpoint posture, compaction posture, verification state, accepted
risks, pending actions, branch lineage, workspace knowledge posture, and safe
inspection commands such as:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox observability status --cwd .
uv run glassbox eval audit --cwd .
```

When the session has task plans or branch-search records, the summary also adds
bounded read-only commands such as `glassbox task show TASK_ID --cwd .` and
`glassbox branch-search show SEARCH_ID --cwd .`. Approve, answer, resume, and
select commands are intentionally not listed as safe inspection commands.

For explicit handoff context, add local operator labels:

```bash
uv run glassbox session export SESSION_ID handoff.json \
  --exported-by alice \
  --expected-custodian bob \
  --note "waiting on approval review" \
  --cwd .
```

The exporter replaces absolute workspace paths with `<workspace-root>` and
redacts common secret-like key assignments or tokens in operator-facing text.

Import a package into another local workspace for inspection with:

```bash
uv run glassbox session import handoff.json --cwd .
```

Import creates a new local session ID and records imported transcript/history as
canonical import events. The imported handoff note includes the package's latest
objective and knowledge posture summary when present. The imported session is
historical and inspection-only; it does not silently merge with an existing
session or become live mutable state.

When the recipient is a reviewer rather than the next local operator, combine
the handoff export with the guidance in
[reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) so raw
`.glassbox` state, screenshots, provider output, and unreviewed logs stay local
unless they have been explicitly sanitized.

## Daily Team Workflow

Use this order when a session needs to move between people or terminals:

1. Check the live writer boundary with `glassbox daemon status --cwd .` or by
   noting whether the current `chat` process owns the session.
2. Inspect the session with `glassbox session status SESSION_ID --cwd .` or the
   dashboard session view.
3. If the session is actionable and the daemon owns the workspace, use
   `glassbox session attach SESSION_ID --cwd .` to reconnect instead of starting a
   second local writer.
4. If the next operator only needs review context, export a handoff package with
  `glassbox session export SESSION_ID handoff.json --cwd .` and include
   `--exported-by`, `--expected-custodian`, and `--note` when those labels help.
5. In the receiving workspace, import with `glassbox session import handoff.json
   --cwd .` and inspect the new historical session ID. Fork from stable history
   when alternate work is needed.

Workspace defaults help teams keep routine commands consistent. A repository can
declare `glassbox.profile.json` with default model, approval mode, and eval
profile routing. Use the named templates in
[workspace-profiles.md](./workspace-profiles.md) for manual, test-driven,
release-candidate, offline deterministic, and conservative provider-backed
workflows. Those values apply only when the operator does not pass an explicit
CLI flag. Provider credentials, base URLs, local database paths, and
runtime-owner metadata remain runtime-only local configuration.

## Attach, Approval, Answer, And Branching Review

The contract aligns with current semantics as follows:

| Surface | Current behavior | Team-workflow rule |
| --- | --- | --- |
| `attach` | Reconnects to a daemon-owned actionable session or locally reopens one when no daemon owns the workspace. | Preserve the runtime-owner boundary; attached operators are acting operators, not new runtime owners. |
| approvals | `approve` and `deny` resolve one pending approval ID and resume or deny the suspended tool call. | Record who made the decision when attribution is added; resolved approvals remain single-use. |
| `ask_user` answers | `answer` resolves one pending question and resumes the suspended turn. | Record who answered when attribution is added; answers are operator input, not policy approval. |
| branching | `fork` creates a child at a stable completed-turn boundary. | Forking is the preferred handoff path for alternate work on historical sessions. |
| dashboard actions | Browser actions call the same session APIs used by CLI flows. | Browser identity should be explicit metadata, not browser-local authority. |

This review preserves the single-operator compatibility baseline: existing
commands can keep working without requiring identity flags, while future handoff
and export/import features have a clear place to store attribution.

## Out Of Scope For V2

The v2 team workflow intentionally does not include:

- remote authentication, authorization, roles, or organization membership
- simultaneous multi-writer editing of one session
- cloud-hosted session coordination
- browser-local state as an authority for ownership, approval, or custody
- hidden custody transfer based only on who last opened a dashboard page
- background notification delivery outside the local workspace process model
- importing another operator's package as a live resumable session with hidden
  state mutation
- using `glassbox.profile.json` as a permissions, credential, or remote-policy
  mechanism

These features can be designed later, but they should not be implied by portable
session export, import, or workspace-profile work.

## Troubleshooting Team Workflows

- Ownership conflict: if a mutating command reports that a daemon owns the
  workspace, use `glassbox session attach SESSION_ID --cwd .` for live work or
  `glassbox daemon stop --cwd .` when you deliberately want local commands to
  take ownership again.
- Stale owner metadata: run `glassbox daemon status --cwd .` to confirm the
  state, then use `glassbox daemon start --cwd .` to replace stale metadata or
  `glassbox daemon stop --cwd .` to clear it.
- Unsupported package: `session import` rejects ambiguous JSON, unsupported
  versions, partially redacted payloads, and package formats that cannot be
  reopened safely for inspection.
- Malformed or secret-looking package: import rejects ambiguous JSON,
  unsupported versions, and apparent unredacted secret material. Ask the
  exporting operator to regenerate the package from the current CLI instead of
  editing it by hand.
- Profile precedence surprise: run commands with explicit `--model-name`,
  `--approval-mode`, or `--profile` when one invocation should differ from
  `glassbox.profile.json`. Remember that `.env` only supplies runtime provider
  credentials and base URLs.

## Validation Checklist

Before extending code for portable sessions or workspace defaults, check that a
proposed change preserves this contract:

- current single-operator `chat`, `attach`, `answer`, `approve`, `deny`, `fork`,
  and dashboard workflows still work without an explicit identity flag
- any new operator-originated mutation has a place to carry acting-operator
  metadata
- exported handoff artifacts distinguish last actor, expected custodian, runtime
  availability, historical-only state, latest objective, checkpoint and
  compaction posture, verification state, accepted risks, branch lineage,
  knowledge posture, and safe inspection commands
- imported sessions do not silently become live mutable sessions without an
  explicit resumability decision
- runtime ownership remains the writer-safety mechanism; session custody remains
  operator guidance
- collaboration copy stays honest about local-first scope
- workspace profiles are reviewable defaults, not secrets, locks, or remote
  policy controls

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [branching.md](./branching.md)
- [tool-policy.md](./tool-policy.md)
- [runtime-context.md](./runtime-context.md)
- [workspace-profiles.md](./workspace-profiles.md)
