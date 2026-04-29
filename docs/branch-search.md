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
uv run glassbox branch-search list --cwd .
uv run glassbox branch-search show SEARCH_ID --json --cwd .
```

The first model supports started, planned, forked, executed, verified,
compared, selected, rejected, and abandoned events. Later runtime coordinators
can use those events to run bounded candidates without mutating parent history.
