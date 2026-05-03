# Review Feedback

Glassbox review feedback is local changeset evidence. It records reviewer
comments, requested changes, reviewer questions, operator notes,
observations, and risks without turning them into hosted review state,
approval, or publication automation.

Feedback is stored as canonical review-loop events and rebuilt into SQLite
projections for CLI, API, and dashboard inspection. Adding, resolving,
reopening, archiving, or accepting risk for feedback mutates only local
evidence; Glassbox does not stage, commit, push, open a pull request, merge,
deploy, or publish.

## Command Workflow

Create feedback against an existing changeset:

```bash
glassbox changeset feedback add CHANGESET_ID \
  --kind requested_change \
  --summary "Clarify the verification summary" \
  --provenance reviewer \
  --reviewer-label "local-reviewer" \
  --file src/glassbox/runtime/changesets.py \
  --line-start 42 \
  --cwd .
```

List feedback for a changeset:

```bash
glassbox changeset feedback list --changeset CHANGESET_ID --cwd .
```

Show one feedback record and its scope metadata:

```bash
glassbox changeset feedback show FEEDBACK_ID --cwd .
```

Record local resolution evidence:

```bash
glassbox changeset feedback resolve FEEDBACK_ID \
  --summary "The verification summary now names retained evidence." \
  --residual-risk "Reviewer acceptance is not implied." \
  --cwd .
```

Reopen feedback when a response is no longer sufficient:

```bash
glassbox changeset feedback reopen FEEDBACK_ID \
  --reason "The dashboard still needs to show open questions." \
  --cwd .
```

Accept local residual risk explicitly:

```bash
glassbox changeset feedback accept-risk FEEDBACK_ID \
  --risk-summary "Dashboard mutation is deferred to the later UX phase." \
  --reason "CLI and API mutations are sufficient for this slice." \
  --cwd .
```

Archive feedback after explicit operator intent:

```bash
glassbox changeset feedback archive FEEDBACK_ID \
  --reason "Superseded by narrower feedback." \
  --cwd .
```

Every command supports `--json` for scripting. JSON output includes bounded
feedback fields, scope rows, event sequences for mutations, safe next actions,
and non-claims.

## API And Dashboard

The dashboard changeset detail response includes `review_feedback` rows beside
review briefs, readiness, verification, command evidence, sources, and safe
next actions. The changeset console shows open feedback, requested changes,
questions, locally resolved feedback, and accepted risks without implying
approval.

The API surfaces are:

- `GET /changesets/feedback`
- `GET /changesets/feedback/{feedback_id}`
- `POST /changesets/{changeset_id}/feedback`
- `POST /changesets/feedback/{feedback_id}/resolve`
- `POST /changesets/feedback/{feedback_id}/reopen`
- `POST /changesets/feedback/{feedback_id}/archive`
- `POST /changesets/feedback/{feedback_id}/accept-risk`

The dashboard remains read-oriented for this slice. Integrated dashboard
mutation controls are intentionally deferred to the later v13 UX phase, after
fixup responses, manual evidence, browser evidence, and lifecycle briefs have
settled.

## Evidence Boundaries

Use feedback dispositions carefully:

- `open`: feedback still needs attention or explicit disposition
- `in_progress`: local response work has started
- `responded`: response evidence exists but local resolution is not claimed
- `resolved_locally`: Glassbox has retained local response evidence
- `accepted_with_risk`: the operator chose an explicit residual-risk path
- `archived`: feedback is no longer active, usually because it was superseded

These states are local evidence posture. They do not mean a reviewer approved
the changeset, accepted the response, or cleared the work for publication.

Feedback scope metadata may name a changeset, file, task, turn, artifact,
verification, or branch candidate. File scopes store paths and optional line
hints only; they do not retain raw file contents.
