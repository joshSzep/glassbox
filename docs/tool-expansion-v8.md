# v8 Tool Expansion And Sandboxing Contract

For the docs hub and operator guides, start at [README.md](./README.md). Pair
this contract with [tool-policy.md](./tool-policy.md),
[verification-loops.md](./verification-loops.md), and
[repository-intelligence-index.md](./repository-intelligence-index.md).

This document records the GBX-870 contract for adding more capable local tools
without turning Glassbox into an unrestricted plugin runner. The goal is to make
common agentic engineering actions structured, inspectable, replay-aware, and
bounded by the same local policy and autonomy budgets that already govern turns,
tasks, verification, and background jobs.

## Current Tool Baseline

Glassbox tools are registered through `src/glassbox/tools/registry.py`. Each
tool declares a typed input model, typed output model, risk bucket, streaming
mode, path argument names, and optional command argument name.

The current model-facing tool posture is intentionally small:

| Tool family | Examples | Risk bucket | Notes |
| --- | --- | --- | --- |
| Workspace inspection | `list_dir`, `read_file`, `search_files`, `git_status` | `read_only` | Must stay inside the workspace and produce structured output. |
| Operator interaction | `ask_user` | `read_only` | Suspends control flow but does not mutate workspace state. |
| Workspace mutation | `apply_patch` | `workspace_write` | Mutates only in-scope workspace files and remains approval/budget governed. |
| Local commands | `run_command`, `run_tests` | `command` | Executes local processes behind destructive-command blocks, policy rules, approvals, cancellation, streaming output, and budgets. |

The v8 expansion path should reduce repeated raw-shell guessing by exposing
narrow, structured, local tools for the workflows Glassbox already performs.
New tools must be easier to audit than an equivalent unconstrained shell command.

## Candidate Tools

| Candidate | Purpose | First-slice risk | Required controls |
| --- | --- | --- | --- |
| Structured file edit | Apply constrained edits such as replace range, append section, or rewrite generated block. | `workspace_write` | Workspace path scope, write budget, approval-mode calibration, generated-path markers where applicable, diff artifact, replay capture. |
| Test discovery | List test files, classes, functions, markers, and collection limits without running tests. | `read_only` | Workspace path scope, crawl/collection limits, timeout budget if pytest collection is used, no test execution by default. Implemented first as `test_discovery` and `test_target_selection`. |
| Dependency inspection | Summarize `pyproject.toml`, lockfiles, package scripts, and dependency groups. | `read_only` | Workspace path scope, lockfile size limits, redaction of private index URLs or tokens, freshness metadata. |
| Package script discovery | List known scripts and validation commands from package metadata and repository index. | `read_only` | Workspace path scope, no execution, confidence labels, provenance from exact files or index entries. |
| Code search | Structured regex/plain search with path filters and result summaries. | `read_only` | Workspace path scope, result limits, binary-file skip, artifact recording for large result sets. |
| Symbol lookup | Resolve indexed symbols, definitions, and simple references from repository intelligence. | `read_only` | Freshness posture, source path and line provenance, graceful stale-index fallback. |
| Diff review | Summarize working-tree or staged diffs by file, size, risk markers, tests, docs, generated outputs, and binary changes. | `read_only` | No git mutation, path filters, large-diff artifact summary, sensitive-diff redaction posture. Implemented first as `workspace_diff_summary`. |
| Artifact summarization | Summarize retained local artifacts such as command logs, eval outputs, and verification failures. | `read_only` | Artifact path/ID scope, byte limits, retention policy, provenance and redaction labels. |
| Browser/network diagnostics | Check local app health, screenshots, accessibility smoke, or static assets. | Contract-only in GBX-875 | Local-only defaults, host allowlist, timeout budget, output redaction, explicit approval for remote hosts. See [network-browser-diagnostics-v8.md](./network-browser-diagnostics-v8.md). |

The first implementation candidates should be read-only diff review and test
discovery because they improve verification and branch-search explanations
without increasing mutation authority.

## Implemented First Slice

`workspace_diff_summary` is the first GBX-871 implementation of this contract.
It is a read-only workflow tool that inspects `workspace`, `staged`, or
`unstaged` git diff scopes with optional workspace-relative path filters.

The tool returns structured patch-risk evidence:

- touched file count, insertions, deletions, binary file count, and clean state
- per-file summaries without raw diff hunks
- generated-file, test-file, docs-file, policy-sensitive, and untracked-file cues
- truncation state when the requested `max_files` limit is reached
- artifact-ready JSON when the full file summary is too large for inline display

Large summaries are recorded through the existing turn artifact path as
`workspace_diff_summary` artifacts when the tool is used during a session with an
artifact repository. The artifact stores summary metadata only; it deliberately
does not store raw patch hunks.

`test_discovery` and `test_target_selection` are the first GBX-872
implementation of the test-discovery portion of this contract. They are
read-only workflow tools:

- `test_discovery` scans bounded workspace paths for pytest-style files and uses
  Python AST parsing to list test functions, test classes, and `pytest.mark`
  markers without running tests.
- `test_target_selection` maps changed paths or short task context to advisory
  pytest targets with `high`, `medium`, or `low` confidence and explicit
  selection reasons.
- both tools include repository-index freshness status and use index test-entry
  summaries as owner hints when a local index exists.
- unknown layouts degrade to empty results plus warnings rather than shelling out
  to broad discovery commands.

## Risk Classification

`read_only` tools may inspect in-scope workspace files, repository metadata, and
retained local artifacts. They still need limits because inspection can be
expensive, reveal sensitive local content, or materially affect prompt context.

`workspace_write` tools may mutate files inside the workspace only after policy,
approval mode, repository autonomy rules, and the active autonomy budget permit
the write. They must emit enough structured output to explain changed paths and
must leave full change review to git-aware surfaces rather than hiding edits in
tool prose.

`command` tools remain the only way to execute local processes. New structured
tools should not quietly shell out unless their contract declares a command risk
or an explicit bounded subprocess posture. Destructive command patterns, remote
publish flows, and credentialed network use remain blocked or approval-gated by
policy.

Browser and network diagnostics are not part of the default v8 tool expansion.
If accepted later, they should have a narrower risk posture than general web
automation: local dev server health, local screenshots, local accessibility
smoke, and static asset checks before remote URL diagnostics.

## Required Tool Contract

Every new model-facing tool must declare:

- typed pydantic input and output models with `extra="forbid"`
- a stable `ToolSpec` name and description
- a risk bucket from the existing registry vocabulary unless a later task adds a
  documented bucket migration
- path argument names for every workspace path input
- a command argument name if it executes a command or shells out
- streaming mode when output can be streamed
- bounded limits for path count, result count, bytes, timeout, and artifact size
- structured success, skip, warning, and failure fields where relevant
- artifact pointers when output is too large for event payloads
- redaction posture for sensitive content
- replay capture expectations and drift posture

Tool output should be directly useful to events, verification summaries, branch
candidate comparisons, and dashboard evidence. A tool that returns only prose is
not a v8-quality tool.

## Policy And Budget Controls

New tools must honor hard invariants before repository rules or autonomy budgets:

1. paths remain inside the workspace or retained artifact store
2. destructive commands remain blocked
3. provider secrets and raw credentials are not persisted
4. approval mode remains meaningful
5. repository autonomy rules may narrow authority but do not bypass hard bounds
6. budget exhaustion pauses or blocks further autonomous work with durable
   evidence

At minimum, new tools must participate in these budget dimensions where relevant:

- tool-call count
- write-operation count
- command-operation count
- verification-attempt count
- wall-clock duration
- artifact-byte budget
- branch-attempt budget when used inside branch search

## Validation Matrix

| Behavior | Required validation |
| --- | --- |
| Schema exposure | Registry tests prove stable names, input schemas, output schemas, risk buckets, streaming modes, and path/command argument declarations. |
| Workspace scope | Unit and integration tests cover relative paths, absolute in-workspace paths, outside-workspace rejection, symlink posture where applicable, and missing paths. |
| Policy traces | Policy tests cover allow, approval required, deny, autonomy-rule match, budget match, and budget exhaustion. |
| Streaming output | Streaming tools test chunk ordering, cancellation, timeout, and final structured result. |
| Cancellation | Long-running tools stop promptly and emit a cancelled/interrupted result without corrupting artifacts. |
| Artifacts | Large outputs are summarized in events and retained as artifacts with byte limits and redaction labels. |
| Replay capture | Replay bundles retain enough structured input/output metadata to classify drift without storing unreviewed sensitive payloads. |
| Verification integration | Verification and branch-search tests prove summaries can cite tool outputs without rerunning commands. |

## Migration Notes

Tool schema exposure should remain backward compatible for existing model
adapters. Adding a tool is additive, but renaming a tool, changing a field type,
or changing a risk bucket is a compatibility migration and should include replay
and eval notes.

Existing command-heavy workflows should migrate gradually. A structured tool may
replace common shell inspection when it can produce clearer evidence, but raw
commands remain necessary for repository-specific validation under policy.

Replay capture should store stable tool names, argument fingerprints, result
summaries, artifact references, policy decisions, and budget posture. Full raw
diffs, large logs, model prompts, model responses, provider metadata, and secrets
should stay out of portable exports unless a later redaction review explicitly
allows them.

## Non-Goals

v8 tool expansion does not introduce:

- arbitrary plugin marketplaces
- remote tool execution authority
- hosted worker fleets or cloud control planes
- browser-native code editing
- unrestricted web browsing or credentialed scraping
- automatic package publication, deployment, or release upload tools
- provider-side memory or opaque remote retrieval as a substitute for local
  provenance
- silent model or provider switching based on canary results

The expansion test is simple: if a new tool cannot explain what it inspected,
what it changed, what policy allowed it, and how replay should treat it, it does
not belong in the v8 runtime yet.
