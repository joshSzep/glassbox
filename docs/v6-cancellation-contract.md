# v6 Cancellation Contract

For the v6 task graph, see [tasks-v6.md](./tasks-v6.md). This document defines the backend cancellation semantics introduced by Phase 65 and replaces the v5 known gap where terminal interruption was informational only.

## Scope

Cancellation is a live-turn mutation. It applies to one active or suspended turn in one session and never rewrites historical events. A cancellation request can be made by the terminal, dashboard, API, or daemon attach client, but the live runtime owner remains the only authority that can acknowledge and execute it.

Cancellation is cancellable only while the turn is active, suspended for approval, suspended for `ask_user`, or reconnecting to a live owner that can still accept mutations. Completed, failed, imported, replay-only, and historical-only turns are not cancellable.

## Event Contract

Cancellation uses explicit persisted events so replay, dashboard, TUI, eval, and release evidence can distinguish intentional cancellation from timeout or failure.

| Event | Meaning |
| --- | --- |
| `CancellationRequested` | An operator or client requested cancellation for a specific turn. Repeated requests for the same active cancellation are idempotent. |
| `CancellationAcknowledged` | The live runtime owner accepted the request and began cancellation handling, or observed a repeated request already in progress. |
| `TurnStatusChanged(status="cancelling")` | The turn is no longer doing normal work and is trying to stop safely. |
| `ToolExecutionCancelled` | A tool call was intentionally interrupted by cancellation; partial output and artifacts remain evidence. |
| `TurnStatusChanged(status="cancelled")` | The turn reached a terminal cancelled state. |
| `TurnCancelled` | Final cancellation details, including reason and stage. |
| `TurnCompleted(outcome="cancelled")` | The turn terminal marker used by projections that already track `TurnCompleted`. |
| `CancellationFailed` | The request could not be honored, such as a completed turn, unavailable owner, or provider/tool refusal. |

`TurnFailed` remains reserved for unexpected runtime failures. `SessionCompleted(reason="cancelled")` remains a session-lifecycle outcome and must not be used to mean one turn was cancelled.

## State Rules

| State | Cancellation behavior |
| --- | --- |
| Idle session | Reject with `CancellationFailed`; there is no active turn. |
| Building context | Accept, stop before the next model call, and record a cancelled turn. |
| Active model call | Accept and short-circuit after the current cancellable await point; provider-level abort is best effort. |
| Active tool call | Accept, request tool interruption, preserve streamed output, and classify the tool result as cancelled. |
| Pending approval | Accept by cancelling the suspended turn; no implicit approval or denial is recorded. |
| Pending `ask_user` question | Accept by cancelling the suspended turn; no synthetic answer is recorded. |
| Reconnecting stream | The client may request cancellation only through the live owner. If the owner cannot be reached, reject with an unavailable-runtime failure. |
| Completed historical turn | Reject as non-cancellable historical state. |
| Failed turn | Reject; failures remain inspectable but are not converted into cancellations. |

## Outcome Classes

- Graceful cancellation: the runtime observes the request and records `TurnCancelled` plus `TurnCompleted(outcome="cancelled")`.
- Timeout: a command or operation exceeds its configured deadline and remains a timeout, not a cancellation.
- Subprocess interruption: a command is terminated by a signal outside the cancellation path and remains `interrupted`.
- Provider cancellation failure: the runtime records `CancellationFailed` if the provider cannot be stopped and the turn cannot be safely finalized as cancelled.
- Non-cancellable historical state: completed, failed, imported, or replay-only sessions reject mutation and keep existing state unchanged.

## Replay And Eval Policy

Cancelled turns are valid release evidence. Replay should preserve the cancellation events and partial outputs, then report the turn as intentionally cancelled rather than failed. Eval invariants may assert event order, final state, retained output, and no post-cancellation model/tool continuation; they must not depend on wall-clock timing or exact provider abort behavior.

## Related Files

- [architecture.md](./architecture.md)
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md)
- [v6-release-hardening.md](./v6-release-hardening.md)
- [v6-release-evidence.md](./v6-release-evidence.md)
