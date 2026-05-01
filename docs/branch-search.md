# Branch Search

Branch search is a bounded strategy-search workflow for autonomous local work.
It uses ordinary session fork semantics, but records why each candidate exists,
which strategy it tried, and how verification compared the outcomes.

It differs from a manual fork in three ways:

- a `BranchSearchStarted` event owns the objective and budgeted candidate count
- every candidate has an explicit strategy label and verification status
- selection and rejection are metadata events, not automatic merges into the
  parent session history

Candidate sessions remain inspectable. Rejected candidates are historical
evidence unless an operator prunes artifacts separately.

## Decision Support

Branch-search decision support is a typed comparison target derived from local
branch-search projections. It gives each candidate an operator-readable posture
without changing branch-search semantics:

- objective and strategy label
- retained evidence pointers such as candidate session, verification, artifact,
  and selection records
- changed-file summary
- verification posture
- cost estimate
- risk posture and accepted risks
- recommended follow-up action

Current changed-file evidence is intentionally conservative. Branch-search
projections do not yet retain candidate diff inventories, so the decision
support model reports an empty changed-file list with an instruction to inspect
the candidate session before manually carrying work forward. Later surfaces may
replace that unknown cue with retained diff evidence, but they must not infer
file changes from unavailable state.

Branch search remains decision support, not automatic integration. Selecting a
candidate records operator intent and retained evidence; it does not merge,
cherry-pick, rebase, or otherwise mutate the parent session history.

Inspect searches:

```bash
uv run glassbox branch-search start SESSION_ID \
  --objective "Try targeted and broader repair strategies" \
  --strategy "targeted pytest repair" \
  --strategy "broader refactor" \
  --max-candidates 2 \
  --cwd .
uv run glassbox branch-search list --cwd .
uv run glassbox branch-search show SEARCH_ID --json --cwd .
uv run glassbox branch-search select SEARCH_ID CANDIDATE_ID \
  --reason "best passing verification evidence" \
  --cwd .
```

`branch-search show` includes a `decision_support` object in JSON output. Human
output prints candidate verification posture, risk posture, cost estimate,
follow-up action, verification recommendation, and any accepted risks next to
the raw candidate status. When candidate changed-file evidence is available, the
recommendation uses the same eval and verification recipe rules as
`glassbox eval recommend`; when changed-file evidence is not retained, the
candidate is labeled with a missing-evidence recommendation instead of an
inferred command. The dashboard branch-search console renders the same
comparison so reviewers can separate passed, risky, rejected, and needs-review
candidates without losing access to the candidate session or retained artifact
links.

The bounded coordinator runs candidates sequentially under branch-attempt,
tool-call, write, command, and verification budgets. It records planned, forked,
executed, verified, and compared evidence, but it never merges candidate
changes automatically.

Selection is handoff metadata. `select`, `reject`, and `needs-review` update the
candidate projection while preserving every candidate as historical evidence.
Session export includes branch-search summaries and selected candidate evidence
so an operator can continue from the winning branch intentionally.
