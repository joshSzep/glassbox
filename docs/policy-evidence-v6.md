# Policy Evidence And Audit Surfaces

Glassbox policy evidence is persisted with the event log and projected into the
operator surfaces that explain tool decisions.

## Persisted Evidence

- `ModelToolCallRequested` records the evaluated outcome, risk level, decision
  source, source label, and policy reason before any tool execution occurs.
- `ApprovalRequested` repeats the policy outcome, risk, source, and label for
  approval-gated tools so a pending approval is explainable without replaying the
  model request.
- `ToolExecutionStarted` repeats policy metadata for executed tools, including
  tools resumed after approval.
- Blocked tools retain the policy reason in the failed tool result summary and
  replay tool-result artifact.

## Operator Surfaces

- `glassbox session status` prints aggregate policy counts and points operators
  to pending approvals and recent tool activity for source/reason detail.
- Pending approvals include outcome, risk, source kind, source label, and reason.
- Recent tool activity includes outcome, risk, source, and reason when available.
- Dashboard session snapshots expose the same pending approval and tool-call
  policy fields for browser rendering.

## Release Evidence

Deterministic approval workflow tests are the current release evidence for
policy-gated behavior. The `approval_flow` capability remains declared in
`evals/coverage.json` as advisory eval coverage until a curated replay case is
promoted, so release audits continue to show the replay/eval gap explicitly
instead of implying that unit or integration tests are replay baselines.
