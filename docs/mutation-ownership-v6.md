# Mutation Ownership Contract

Glassbox keeps one live mutation owner for a workspace/database pair.

## Rules

- A healthy daemon owner handles live dashboard, terminal attach, cancellation,
  prompt, answer, approval, denial, and fork mutations.
- Local mutating commands must fail while daemon owner metadata is running.
- Read-only inspection remains available from persisted state.
- API mutation conflicts return `409` with the service conflict detail.
- CLI local mutation conflicts explain that the workspace runtime is owned by the
  daemon and point operators to `glassbox daemon stop`.
- Stale owner metadata may be cleaned up, after which local attach and local
  mutation paths can proceed normally.

## Client Expectations

- Dashboard actions should surface backend `409` details without retrying as a
  different owner.
- Terminal attach should route through the daemon when it is healthy and fall
  back locally only after stale metadata is cleared.
- Repeated approval, denial, answer, fork, or cancellation attempts may be
  rejected as conflicts; this is safer than silently creating a second live
  owner.
