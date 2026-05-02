# Reviewer Evidence Bundles

For the docs hub and workflow guides, start at [README.md](./README.md). Pair
this guide with [team-workflows.md](./team-workflows.md),
[replay-evals.md](./replay-evals.md), [dogfooding.md](./dogfooding.md), and the
current release-gate guide.

Glassbox evidence is local workspace state by default. A reviewer bundle is a
small, explicit set of summaries and portable artifacts that lets another
operator inspect the claim without copying `.glassbox/`, live provider
credentials, raw databases, or private working-tree state.

## Reviewer-Safe Surfaces

Use these surfaces first because they are already summarized, scoped, or
redacted by design:

| Surface | Command Or Path | Good For | Review Before Sharing |
| --- | --- | --- | --- |
| Handoff export | `uv run glassbox session export SESSION_ID handoff.json --cwd .` | Session story, latest objective, checkpoint and compaction posture, verification state, accepted risks, branch lineage, knowledge posture, and safe inspection commands. | Transcript text, operator note, branch labels, and accepted-risk wording. |
| Changeset export | `uv run glassbox changeset export CHANGESET_ID changeset-review.json --cwd .` | Change-centered objective, inventory summary, provenance, verification readiness, latest review brief metadata, artifact references, redaction report, and non-claims. | Objective text, risk summaries, source reasons, artifact IDs, and any local-only brief limitations. |
| Eval report | `uv run glassbox eval report commit-smoke --cwd .` | Deterministic profile pass/fail evidence and retained `summary.json` paths. | Changed path names, case notes, and failure summaries. |
| Eval audit | `uv run glassbox eval audit --cwd .` | Coverage gaps and profile manifest health. | Repository path names and local output paths. |
| Replay bundle | `uv run glassbox replay bundle export SESSION_ID bundle.json --cwd .` | Portable deterministic replay fixture when the behavior should become regression evidence. | Prompt text, transcript summaries, bundle notes, and artifact references. |
| Release summary | `.glassbox/releases/.../summary.json` | Gate stage status, blocking versus advisory evidence, package smoke, provider skip reasons, and retained evidence pointers. | Local paths, provider/model labels, skipped canary reasons, and manual-evidence notes. |
| Live cockpit or accessibility summary | `.glassbox/releases/.../live-cockpit/.../summary.json` or manual review docs | Browser, keyboard, or screen-reader evidence that is intentionally non-blocking unless a later gate promotes it. | Screenshots, browser logs, assistive-technology transcripts, and private route names. |

Do not hand over the workspace SQLite database, `.env`, provider transcripts,
raw command logs, full `.glassbox/` directories, screenshots, or browser traces
unless the recipient is supposed to have the same local custody and the files
have been reviewed for private content.

## Redaction Rules

Before attaching evidence to a PR, issue, release note, or handoff package,
remove or replace:

- API keys, tokens, cookies, credential values, and environment values
- absolute local paths, home directories, user names, hostnames, and machine IDs
- private repository names, customer names, ticket IDs, branch names, and
  proprietary service URLs
- raw provider prompts or responses when they quote private code or data
- source snippets, private diffs, dependency URLs, and stack traces containing
  private paths
- screenshots, logs, exported sessions, and replay bundles that have not been
  reviewed after generation

Prefer neutral aliases such as `workspace-root`, `repo-alpha`,
`provider-skipped-no-credentials`, `provider-present-redacted`, and `task-1`.
It is fine to commit or paste command names, Glassbox version or commit labels,
high-level workflow category, pass/fail status, explicit skip reasons, and
follow-up task IDs when they do not disclose private implementation details.

## Retention Rules

Keep raw evidence local under `.glassbox/` unless a repository deliberately
chooses to retain a sanitized artifact. Commit small text summaries when they
help future reviewers. Avoid committing binary screenshots, terminal
recordings, provider canary output, large logs, or ad hoc exported sessions by
default.

If raw evidence is too private to share, commit a sanitized summary that names:

- the command or workflow category
- the Glassbox version, commit, or candidate label
- the local evidence path retained outside git
- the pass/fail state
- redaction performed
- accepted residual risks or follow-up task IDs

## Release-Candidate Review Example

For a release candidate, provide the reviewer with:

```bash
uv run glassbox readiness check --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
uv run glassbox provider canary evidence --cwd .
```

Then point to the retained release `summary.json` under `.glassbox/releases/...`
and include sanitized links or copied snippets for blocking deterministic
evidence, advisory provider evidence, live cockpit evidence, accessibility
pairings, dogfooding summaries, and accepted residual risks. Provider canaries,
live browser runs, and screen-reader pairings remain advisory unless the active
release gate explicitly promotes a deterministic fixture-backed check.

## Ordinary Code-Review Handoff Example

For a normal code-review handoff, provide:

```bash
uv run glassbox changeset export CHANGESET_ID changeset-review.json --cwd .
uv run glassbox session export SESSION_ID handoff.json --cwd .
uv run glassbox eval recommend PATH --cwd .
uv run glassbox eval audit --cwd .
```

The changeset export is the preferred review-centered bundle when a changeset
exists. It does not include raw `.glassbox` database state, raw command output,
provider transcripts, raw diffs, or file contents. The handoff export gives the
reviewer the broader session story and safe inspection commands. The
recommendation output explains the cheapest trustworthy next verification
command. The audit output shows whether the repository-owned eval coverage has
gaps that matter for the touched surface.

If the behavior should become repeatable release evidence, export or promote a
replay bundle only after reviewing the bundle contents for private transcript
text and local path leakage.
