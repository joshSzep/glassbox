# Evidence Graph

For the docs hub and operator guides, start at [README.md](./README.md). This
page defines the v16 evidence graph contract from
[tasks-v16.md](./tasks-v16.md) and the
[v16 operator flow compression contract](./v16-operator-flow-compression-contract.md).

The evidence graph is a derived, bounded, local view over existing Glassbox
state. It explains why a claim, recommendation, readiness state, verification
posture, queue item, next action, or handoff summary is supported, stale,
missing, contradicted, manual-only, or accepted with risk.

It is not a new source of truth.

## Scope

The evidence graph should help operators inspect claim support without reading
raw transcripts, raw command logs, raw artifacts, raw diffs, or local database
internals. It connects summaries and identifiers from canonical events,
projections, managed artifacts, typed API responses, and deterministic eval or
release evidence.

The initial v16 model supports:

- evidence nodes for events, artifacts, commands, tool attempts, verification
  checks, review feedback, manual evidence, memory entries, repository
  intelligence sources, eval cases, background jobs, release-gate rows, next
  actions, and claims
- evidence edges for supports, contradicts, supersedes, makes-stale, verifies,
  skipped-by, accepted-risk-for, derived-from, and safe-next-action-for
  relationships
- claim support summaries for supported, missing, stale, contradicted,
  manual-only, accepted-with-risk, and unsupported claims
- confidence, freshness, provenance, limitation, redaction, and visibility
  fields that can survive CLI, API, dashboard, review brief, handoff, and
  release-evidence transport

## Contract

An evidence graph is a bounded derived graph for one target. The target can be
a workspace, session, turn, task, changeset, review feedback item,
verification check, repository intelligence source, memory entry, background
job, artifact, provider, projection, release row, or unknown legacy object.

Every graph has:

- `graph_id`: stable identifier for the derived view
- `target`: the local object the graph explains
- `generated_at`: when the view was derived
- `nodes`: summary-first evidence nodes
- `edges`: relationships between nodes
- `claims`: claim support records that point to edge and node IDs
- `limitations`: graph-level caveats, truncation notes, sparse-session notes,
  and redaction warnings

Graph IDs and node IDs should be deterministic when the same local evidence is
derived again. Implementations can rebuild graphs from canonical events,
projections, and managed artifacts; they should not persist graph edges as a
second authoritative store unless a later performance task proves
materialization is required.

## Node Semantics

Evidence nodes summarize local evidence. A node should retain:

- `node_id`
- node kind
- title and summary
- provenance summaries such as event sequence, artifact ID, source path, source
  kind, or source ID
- freshness
- confidence
- redaction status
- visibility
- limitations

Node summaries should be enough to explain why the node matters without
exposing raw local state by default. Raw artifacts, transcripts, command logs,
and database rows stay behind the existing artifact, export, and redaction
boundaries.

Supported node kinds are:

- `event`
- `artifact`
- `command`
- `tool_attempt`
- `verification_check`
- `review_feedback`
- `manual_evidence`
- `memory_entry`
- `repository_intelligence_source`
- `eval_case`
- `background_job`
- `release_gate_row`
- `next_action`
- `claim`

## Edge Semantics

Edges describe why two nodes are related. The graph supports these edge kinds:

- `supports`: one node supports a claim or recommendation
- `contradicts`: one node conflicts with a claim or recommendation
- `supersedes`: one node replaces older evidence
- `makes-stale`: one node makes another node stale
- `verifies`: one node verifies a claim, path, check, or posture
- `skipped-by`: one node records that another check or evidence path was
  skipped
- `accepted-risk-for`: one node records accepted residual risk for a claim
- `derived-from`: one node or claim was derived from another local evidence
  source
- `safe-next-action-for`: one next-action node recommends safe inspection,
  planning, or operator-selected work for another node or claim

Edges must reference existing nodes in the same graph. Edge summaries should
explain the relationship without requiring raw evidence payloads.

## Claim Support

Claim support records are the operator-facing answer to "what supports this?"

Each claim support record has:

- `claim_id`
- title and summary
- support state
- confidence
- supporting edge IDs
- contradicting edge IDs
- stale node IDs
- missing evidence records
- accepted-risk node IDs
- limitations
- visibility

Support states mean:

- `supported`: local evidence supports the claim within visible limitations
- `missing`: expected evidence is absent
- `stale`: evidence exists but no longer matches current inputs or freshness
  policy
- `contradicted`: local evidence conflicts with the claim
- `manual-only`: support depends on manual or advisory evidence rather than
  deterministic retained checks
- `accepted_with_risk`: the operator recorded residual risk for the claim
- `unsupported`: no adequate supporting evidence exists

Missing evidence is explicit. It can carry safe next actions, such as inspect,
refresh, or plan commands, but those actions remain advisory and do not approve
execution.

## Confidence And Freshness

Confidence is one of `high`, `medium`, `low`, or `unknown`. Confidence should
drop when evidence is stale, partial, manual-only, redacted, contradicted, or
derived from advisory inputs.

Freshness is one of `fresh`, `stale`, `missing`, `superseded`, `manual-only`,
or `unknown`. Freshness should follow the source surface's existing policy
where one exists:

- repository intelligence freshness comes from repository intelligence
  snapshots and freshness cues
- changeset inventory freshness comes from changeset inventory status
- verification freshness comes from verification ledgers, command evidence,
  skipped evidence, stale inventory, and accepted-risk records
- memory freshness comes from confirmed, stale, invalidated, imported, pruned,
  and prompt-use state
- projection freshness comes from projection-health reads

The graph should not turn stale evidence into a pass. Stale evidence can still
be useful, but it must remain visibly stale.

## Redaction And Visibility

Redaction status is one of:

- `safe_summary`
- `local_only`
- `redacted`
- `blocked`
- `unknown`

Visibility is one of:

- `operator_only`
- `reviewer_safe`
- `release_safe`

Reviewer-safe graph slices must omit local-only, blocked, or raw-sensitive
details by default. They can include safe summaries, IDs, redaction reports,
non-claims, limitations, and missing-evidence states.

Release-safe graph slices must not elevate advisory provider, browser,
accessibility, manual, repository intelligence, memory, or review-feedback
evidence into deterministic release authority.

## Non-Claims

The evidence graph does not:

- approve commands
- run verification
- stage, commit, push, open pull requests, merge, deploy, or publish
- replace release gates, tests, replay, evals, package checks, type checks,
  lint, or deterministic validation
- expose raw local artifacts by default
- make repository intelligence, memory, provider canaries, browser evidence,
  accessibility evidence, manual evidence, review feedback, owner hints, or
  next actions authoritative release approval

## Implementation Notes

The first model lives in `glassbox.core` so runtime, CLI, API, dashboard type
generation, review briefs, handoff summaries, and release-evidence surfaces can
share the same serialized shape.

Follow-on derivation should prefer bounded query helpers over new projection
tables. If later performance evidence requires materialized graph summaries,
the materialized rows should remain rebuildable from canonical events and
managed artifacts.

## Dashboard Explorer

The dashboard renders evidence graphs as compact lists before any visual graph
layout. Selected sessions show a Session Evidence Graph in the inspector's
Evidence tab, and selected changesets show a Changeset Evidence Graph near the
review action panels.

The explorer keeps raw payloads out of the default view. It shows graph counts,
filter buckets for stale, missing, manual-only, accepted-risk, contradictory,
and reviewer-safe evidence, then claim support, node summaries, relationships,
and graph limitations. Node links are local anchors so operators can move from
relationships back to the bounded node summary without opening raw event logs
or artifact payloads.

If an older session or changeset has no derived graph, the dashboard keeps the
panel visible with a sparse-state explanation and continues to show the
existing event, command, verification, and artifact summaries.
