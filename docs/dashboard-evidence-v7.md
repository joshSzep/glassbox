# Dashboard Evidence v7 UX Contract

For the current dashboard usage guide, see [dashboard.md](./dashboard.md). For the broader operator-console model, see [operator-console.md](./operator-console.md).

This document is the GBX-770 target for v7 dashboard evidence work. It defines how Glassbox should present branch comparison, lineage, metrics, policy evidence, replay/eval evidence, provider capability evidence, and release cues for operator decisions without turning the default dashboard into a raw event dump.

## Product Posture

The dashboard remains an attention-first local operator console. It should answer these questions in order:

1. What needs action now?
2. What evidence changes that action?
3. Where can I inspect the underlying proof?

Persisted session events and backend read models remain authoritative. The browser may summarize, sort, filter, and stage local drafts, but it must not reinterpret raw events into new runtime truth that the backend does not expose.

## Evidence Priority Rules

Overview content is reserved for evidence that changes the next operator decision. Use the overview for:

- pending approvals, questions, failed sessions, active tools, and prompt readiness
- live stream state, projection health, and runtime availability
- blocking replay/eval evidence or projection degradation that should delay action
- advisory drift only when an approval, question, failure, or fork decision depends on it
- compare target identity when comparison is actively selected

Tabs and lazy panes own deeper inspection:

- Transcript: narrative context and current conversational state
- Timeline: turn, model, tool, suspension, failure, and forkable boundary chronology
- Actions: approvals, answers, cancellation, prompt continuation, and fork dialogs
- Lineage: parent, child, and forkable-turn navigation
- Compare: aligned differences between selected and compared session snapshots
- Runtime: repository context, working set, runtime notes, and artifact provenance
- Evidence: stream state, projection details, live output tail, retained event evidence, verification cues, replay/eval artifact references, and provider/release cues
- Metrics: turn duration, model duration, tool duration, tokens, failures, and timing patterns

Raw event rows, long metric tables, full artifact provenance, and release engineering details should never crowd the overview unless they are the reason an operator should stop or act differently.

## Branch Comparison And Lineage

Lineage evidence starts from persisted relationships, not transcript similarity. The dashboard should make parent, child, and forkable-turn relationships explicit before showing derived differences.

The compare model should cover:

- session identity, status, branch label, parent ID, fork source turn, and fork source sequence
- inherited transcript versus post-fork transcript messages
- latest user and assistant messages on both sides
- active, completed, failed, denied, and blocked tool activity
- policy outcomes and highest policy risk on each side
- turn count, total duration, model duration, tool duration, token totals, and failed-tool count
- runtime context, working-set, and high-signal path differences
- projection health and snapshot freshness for both sides

Compare UI should default to compact difference summaries and aligned latest evidence. Side-by-side detail is appropriate when screen width allows; otherwise use stacked sections with stable labels. Opening the compared session and clearing comparison must stay one action away.

Do not fetch or render full historical sessions on initial dashboard load just to prepare comparisons. Use selected-session snapshots and explicit compare-target loading.

## Metrics And Latency Analytics

Metrics are local operational evidence, not external analytics. Derive them from persisted turn metrics, event timing, and projections.

Session metrics should distinguish:

- total turn duration
- model call duration and token totals
- tool execution duration
- failed tool count and failure summaries
- cancellation timing when retained in events
- waiting-for-approval or waiting-for-answer time when derivable from event timestamps
- replay/eval drift timing only as evidence context, not runtime latency

Workspace-level metrics should summarize queues and sessions without requiring external services:

- slowest recent turns
- highest token sessions
- repeated failed tool patterns
- sessions awaiting approval or answer longest
- degraded projection counts and rebuild scope

Use thresholds only when documented. Without explicit thresholds, label metrics as observed values rather than failures. A slow provider call and a slow local tool should have different labels and different suggested inspection paths.

## Policy Evidence

Policy evidence should be visible at the moment an operator approves, denies, or investigates a blocked action. The dashboard should use the same decision language as the terminal:

- `advisory risk accepted`: action was allowed, with risk/source retained as evidence
- `approval required`: action is paused until an operator approves or denies it
- `denied by policy`: repository policy denied the action
- `invariant block`: a non-overridable runtime invariant blocked the action

Policy cards and summaries should show:

- outcome label
- risk level
- source kind and source label, rendered together when both are present
- reason text
- related tool name and tool call ID when available
- event sequence or artifact pointer when drilling into evidence

Repository rule decisions and hard invariant blocks must be visually distinguishable. A denied repository rule is reviewable policy behavior; an invariant block is a runtime guardrail that repository policy cannot override.

## Replay, Eval, Provider, And Release Cues

Replay and eval evidence should guide judgment but should not imply that the browser ran verification. The dashboard may summarize retained artifact evidence and recommendation pointers, but execution remains in CLI/backend workflows.

Cue severity language:

- Blocking evidence: replay/eval artifacts with failures, errors, or failing tests that should stop optimistic triage
- Advisory drift: stale, inherited, timed-out, or partial artifacts that require judgment
- Verified state: retained artifacts with no blocking or drift signal
- Missing evidence: neutral state; use CLI commands if reproduction is needed

Provider capability evidence is advisory unless backed by an explicit deterministic release gate. Canary status, provider diagnostics, unsupported-provider warnings, and model capability notes should not look like release signoff.

Release/eval freshness should show where evidence came from and when it was generated when the data is retained. If freshness is unknown, say so neutrally and route the operator to the Evidence tab or CLI recommendation command.

## Mobile And Keyboard Workflow

Mobile should be a drill-in console:

- overview and queues first
- selected-session header next
- tabs for transcript, timeline, actions, lineage, compare, runtime, evidence, events, and metrics
- actions must remain reachable without horizontal scrolling
- compare detail should stack current and compared evidence rather than squeezing side-by-side cards
- long event, metric, and artifact lists should use load-more controls or collapsible sections

Keyboard expectations:

- queue rows, inspector tabs, action buttons, lineage targets, compare controls, fork dialogs, load-more controls, and composer actions are reachable by tab order
- focus follows the operator workflow and survives live rerenders
- approval approve/deny and question answer flows remain operable without pointer shortcuts
- dialogs or sheets trap focus and restore it on close
- status chips include text, not color alone
- live updates should politely surface new approvals, questions, failures, and stream-state changes where the browser accessibility stack supports it

## Scenario Matrix For Evidence Review

Use these scenarios when reviewing v7 dashboard evidence changes:

| Scenario | Overview Signal | Primary Tab | Detail Evidence | Validation |
| --- | --- | --- | --- | --- |
| Pending policy approval for command | Awaiting approval, policy source, risk | Actions | Policy reason, source kind/label, related tool | Frontend action component test |
| Repository rule denies publish command | Failed/blocked action cue | Evidence or Timeline | `denied by policy`, rule ID, reason | Policy + dashboard evidence test |
| Workspace-scope invariant block | Failed/blocked action cue | Evidence or Timeline | `invariant block`, invariant label, reason | Policy + dashboard evidence test |
| Child branch diverges after fork | Compare target shown | Compare | status, transcript, metrics, working-set deltas | Compare state and routing test |
| Parent/child lineage navigation | Lineage available | Lineage | parent, children, forkable turns | Lineage component or Playwright workflow |
| Slow provider call | Metrics cue if action-relevant | Metrics | model duration, tokens, turn ID | Metrics component test |
| Slow local tool | Metrics cue if action-relevant | Metrics | tool duration, tool name, output/artifact pointer | Metrics component test |
| Replay/eval failing artifact | Blocking verification cue | Evidence | artifact path, failing tests, freshness | Verification cue test |
| Stale inherited artifact | Advisory drift cue | Evidence | provenance, inherited/freshness labels | Verification cue test |
| Provider canary stale or missing | Advisory provider cue | Evidence | provider, model, freshness, non-signoff label | Evidence cue test |
| Historical session with no retained artifacts | Neutral missing evidence | Evidence | missing evidence copy and CLI route | Session inspector test |
| Mobile compare drill-in | Selected session remains clear | Compare | stacked anchors and differences | Screenshot or responsive component review |

## Current Gaps To Close In Follow-On Tasks

- Compare currently summarizes snapshot differences but does not yet align post-fork transcript ranges or policy outcome deltas.
- Metrics currently show totals and raw rows but not slowest-turn, waiting-time, or workspace-level latency summaries.
- Verification cues currently focus on artifact-backed replay/eval evidence and working-set provenance; provider capability and release freshness cues need a normalized evidence model.
- Event evidence is reachable, but policy/eval/provider cues need stronger drill-in links to event sequence, artifact path, or recommended CLI command.

These gaps map directly to GBX-771, GBX-772, and GBX-773.
