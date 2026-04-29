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
```

The bounded coordinator runs candidates sequentially under branch-attempt,
tool-call, write, command, and verification budgets. It records planned, forked,
executed, verified, and compared evidence, but it never merges candidate
changes automatically.
