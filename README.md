# Glassbox

Glassbox is a local-first CLI agent harness with a live dashboard.

This repository is being built incrementally from the architecture and task documents in [docs/architecture.md](docs/architecture.md), [docs/database.md](docs/database.md), and [docs/tasks.md](docs/tasks.md).

Glassbox currently provides:

- a persisted event-sourced runtime backed by SQLite
- a terminal-first CLI for running, resuming, inspecting, and recovering sessions
- a FastAPI dashboard with session snapshot and event stream endpoints
- approval, resume, replay, replay-export, and projection rebuild workflows
- replay-backed eval suites for portable behavioral regression baselines

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Getting Started

Install the project and development tooling:

```bash
uv sync
uv run pre-commit install
```

Check that the CLI is available:

```bash
uv run glassbox --help
python -m glassbox --help
```

The current command surface is:

```text
glassbox run [PROMPT]
glassbox chat [PROMPT]
glassbox attach SESSION_ID
glassbox message SESSION_ID PROMPT
glassbox answer SESSION_ID QUESTION_ID ANSWER
glassbox resume SESSION_ID
glassbox fork SESSION_ID [--turn TURN_ID] [--branch-label LABEL] [--prompt PROMPT]
glassbox status SESSION_ID
glassbox replay SESSION_ID [--json]
glassbox replay --bundle BUNDLE_PATH [--json]
glassbox replay-export SESSION_ID [OUTPUT]
glassbox eval run [CASE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
glassbox rebuild [SESSION_ID | --all]
glassbox serve
```

## Interactive Terminal Workflow

Use `glassbox chat` as the default conversational entrypoint. It starts a new
session, keeps a live event subscription open in the terminal, and lets you keep
working in the same shell instead of restarting the CLI for every turn.

By default, `chat` also starts a co-hosted dashboard in the same process. Use
`--no-dashboard` to keep the session terminal-only, or `--dashboard-host` and
`--dashboard-port` to override the dashboard bind target.

When the co-hosted dashboard starts successfully, `chat` prints a session-
specific browser URL like `http://127.0.0.1:8765/?session=SESSION_ID`. Open
that URL while the interactive session is still running to watch the same live
session state that the terminal is driving.

```bash
uv run glassbox chat --cwd .
```

Or start with an initial prompt:

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

Inside an interactive session:

- freeform text sends the next prompt while the session is idle and running
- freeform text answers the pending `ask_user` question when the session is awaiting user input
- `/approve` and `/deny` resolve a pending approval without requiring the approval ID
- `/status`, `/help`, and `/exit` remain available as explicit control commands

The prompt context changes with the session state, so the terminal will tell you
whether it expects a new prompt, an `ask_user` answer, or an approval decision.

If default dashboard startup fails, `chat` keeps the terminal workflow running
and prints a warning that the dashboard is unavailable for that session. If you
explicitly set `--dashboard-host` or `--dashboard-port` and startup fails,
`chat` exits with an error instead of pretending a live dashboard exists.

### Example: Start And Continue In One Terminal

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

Then continue in the same terminal session:

```text
prompt> Now summarize the tests.
prompt> /status
prompt> /exit
```

### Example: Reopen An Actionable Session

Use `glassbox attach` when you already have a persisted session ID and want to
continue the operator workflow in a terminal.

```bash
uv run glassbox attach SESSION_ID --cwd .
```

`attach` is for sessions that are actionable from the operator side:

- idle running sessions waiting for the next prompt
- sessions awaiting `ask_user` input
- sessions awaiting approval resolution

Typical attach flow for a paused session:

```bash
uv run glassbox status SESSION_ID --cwd .
uv run glassbox attach SESSION_ID --cwd .
```

If the session is waiting on `ask_user`, the next freeform entry is treated as
the answer. If the session is waiting on approval, freeform text is blocked and
you must use `/approve` or `/deny`.

`attach` does not automatically start the dashboard. If you want browser-based
observation while re-entering a persisted session from another terminal or after
the original `chat` process has exited, run `glassbox serve` separately and
start from the root dashboard URL to browse recent sessions.

### Scope Boundary

The interactive terminal UX is intentionally process-local in v1. `chat` owns
the live in-process event stream for the session it started, and `attach` can
reopen a persisted actionable session later, but Glassbox does not yet claim to
stream live terminal output from another already-running process or a daemon-
backed resident agent. For cross-process observation, use the dashboard.

## CLI Primitives

Start a session in the current workspace:

```bash
uv run glassbox run "Inspect the repository" --cwd .
```

Use the one-shot commands when you want scripting, recovery, or explicit state-
driven control instead of a long-lived conversational shell.

Glassbox persists runtime state under `.glassbox/` in the selected workspace by default.
The SQLite database lives at `.glassbox/glassbox.sqlite3` unless you override it with `--db-path`.

Inspect a session from the terminal:

```bash
uv run glassbox status SESSION_ID --cwd .
```

The status view summarizes the current turn, pending approvals, recent tool activity,
recent turn metrics, transcript count, the latest transcript message, and the
next valid operator action for the session's current state.

Resume a persisted session:

```bash
uv run glassbox resume SESSION_ID --cwd .
```

Submit another user prompt into an existing running session:

```bash
uv run glassbox message SESSION_ID "Continue with the next step" --cwd .
```

Answer a pending `ask_user` question for a suspended session:

```bash
uv run glassbox answer SESSION_ID QUESTION_ID "blue" --cwd .
```

When a session pauses for input, the CLI prints a `Question asked (...)` line with
the `QUESTION_ID` you need for the `answer` command.

Resolve a pending approval:

```bash
uv run glassbox approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox deny SESSION_ID APPROVAL_ID --cwd .
```

Rebuild derived projections from canonical events:

```bash
uv run glassbox rebuild SESSION_ID --cwd .
uv run glassbox rebuild --all --cwd .
```

## Multi-Turn Workflow

Prefer `glassbox chat` and `glassbox attach` for human-driven multi-turn work.
Use the lower-level commands below when you need to drive a specific session
state explicitly from scripts, recovery flows, or precise operator steps.

Use the command that matches the session's current actionable state:

- `glassbox chat [PROMPT]` starts a new long-lived terminal session for follow-up prompts without restarting the CLI each turn.
- `glassbox attach SESSION_ID` reopens an actionable persisted session in the interactive terminal workflow.
- `glassbox resume SESSION_ID` replays a persisted session after restart. It does not send a new prompt.
- `glassbox message SESSION_ID PROMPT` sends a fresh user prompt when the session is running and idle.
- `glassbox answer SESSION_ID QUESTION_ID ANSWER` answers a pending `ask_user` question when the session is awaiting user input.
- `glassbox approve SESSION_ID APPROVAL_ID` or `glassbox deny SESSION_ID APPROVAL_ID` resolves a pending approval when the session is awaiting approval.
- `glassbox status SESSION_ID` prints the current session state, any pending approval or question identifiers, and a `Next action:` line that tells you which of the commands above is valid now.

## Historical Inspection And Branching

Historical inspection, branching, and replay are related but different operator
workflows:

- Use `status` or the dashboard when you need to inspect what already happened.
- Use `attach`, `resume`, `message`, `answer`, `approve`, and `deny` when the session is still actionable.
- Use `fork` when you want a new child session that continues from an earlier stable point without mutating the original session.
- Use `replay` and `eval` when you want to compare current code against a recorded baseline rather than continue live work.

### Branching Model

Glassbox v1 time-travel is branch creation, not destructive rewind.

- The parent session remains immutable.
- The child session records explicit lineage fields: `parent_session_id`, `forked_from_turn_id`, `forked_from_sequence`, and optional `branch_label`.
- The child imports the inherited transcript prefix it needs for continuation, then records new post-fork events in its own session log.
- `--prompt` is optional. When provided, Glassbox submits that prompt to the child session immediately after creating it.

Valid fork points are stable completed-turn boundaries only:

- the latest completed turn in the session
- an explicitly selected completed turn via `--turn TURN_ID`

Fork creation is rejected when Glassbox cannot resolve a stable historical cut
point, including:

- a currently running turn
- a session paused on approval
- a session paused on `ask_user`
- ambiguous or corrupted historical state

### CLI Branch Workflow

Inspect a historical session, create a child branch from a selected turn, then
continue in the child:

```bash
uv run glassbox status PARENT_SESSION_ID --cwd .
uv run glassbox fork PARENT_SESSION_ID --turn TURN_ID --branch-label alt-path --cwd .
uv run glassbox message CHILD_SESSION_ID "Try the alternate fix" --cwd .
```

Or create the fork and submit the first child prompt in one step:

```bash
uv run glassbox fork PARENT_SESSION_ID \
  --turn TURN_ID \
  --branch-label alt-path \
  --prompt "Try the alternate fix" \
  --cwd .
```

The fork command prints the new `CHILD_SESSION_ID`, the exact historical turn,
and the inherited transcript count so the operator can audit what changed.

### Dashboard Branch Workflow

Use the browser workflow when you want to inspect lineage before branching:

1. open the session in the dashboard from the co-hosted `chat` URL or from `glassbox serve`
2. inspect the selected-session lineage summary to confirm whether the current view is actionable live work or historical-only state
3. use the fork controls over `branchable_turns` to keep the default latest completed turn or choose an older completed turn explicitly
4. create the fork and let the dashboard navigate into the resulting child session

If the dashboard cannot offer the action, treat that as a state signal rather
than a UI bug: `fork_blocked_reason` should explain why the selected session is
inspectable but not forkable yet.

### Choosing Between Live, Historical, And Child Work

- If the selected session is still actionable, keep working in that session with `attach`, `message`, `answer`, or approval commands.
- If the selected session is historical-only, inspect it with `status` or the dashboard and decide whether to leave it alone or create a child branch.
- If you want to test an alternate path while preserving the original audit trail, create a fork and continue only in the child session.

Inside interactive `chat` and `attach` sessions:

- freeform text sends the next prompt when the session is idle and running
- freeform text answers the pending `ask_user` question when the session is awaiting user input
- `/approve` and `/deny` resolve a pending approval without requiring the approval ID
- `/status`, `/help`, and `/exit` remain available as explicit control commands

In the dashboard, the same workflow is split by pane:

- The `Next Action` pane sends a new prompt for an idle running session.
- The `Next Action` pane switches into answer mode when the model is waiting on `ask_user` input.
- The `Pending Approvals` pane remains the only place to resolve approval-gated tool actions.

Choose the dashboard mode that matches the operator workflow:

- Use the co-hosted dashboard from `glassbox chat` when you want a browser view over the same live process that owns the interactive terminal session.
- Use `glassbox serve` when you want dashboard access without an active `chat` session, want to inspect persisted sessions from another process, or want explicit control over the dashboard server lifecycle.

`resume`, `message`, `answer`, `approve`, and `deny` remain important even with
interactive mode available. They are the low-level primitives for scripting,
recovery after process restart, explicit operator control, and workflows where a
long-lived terminal session is not the right interface.

## Replay And Eval Workflows

Replay and eval commands answer a different question from the live session CLI:
not "what should this session do next?" but "does the current codebase still
reproduce the recorded behavior I care about?"

Use the workflow that matches the problem you are solving:

- Use `glassbox status`, `attach`, `answer`, `approve`, and `message` when you are operating a live or paused session.
- Use `glassbox fork SESSION_ID` when you want to continue from a stable historical turn without rewriting the original session.
- Use `glassbox replay SESSION_ID` when you want to re-check one historical session stored in the local SQLite database.
- Use `glassbox replay-export SESSION_ID` when you want a portable baseline that can move across branches, repositories, or CI machines.
- Use `glassbox eval run` when you want a curated regression suite from checked-in replay bundles under `evals/`.

### Forked Sessions In Replay And Eval

Forked child sessions are first-class replay and eval baselines.

- `glassbox replay CHILD_SESSION_ID` replays the child session with its inherited transcript history intact.
- `glassbox replay-export CHILD_SESSION_ID` writes a portable bundle that includes the child lineage metadata and imported-history payload needed to replay without the original parent database.
- `glassbox eval run` can execute eval cases backed by forked child bundles the same way it executes ordinary session bundles.

In other words, a branch is still just a session from the replay and eval point
of view. The inherited prefix is preserved explicitly so replay can validate the
same child behavior offline instead of treating branched sessions as unsupported
history edge cases.

### Replay Result Categories

Single-session replay and batch eval cases use the same outcome vocabulary:

- `exact match`: the current codebase reproduced the recorded transcript, tool calls, approval flow, question flow, event families, and final state.
- `behavioral drift`: replay ran successfully but the normalized behavior changed.
- `manifest drift`: the recorded prompt/context/tool manifest no longer matches current preparation, so replay stops before pretending the drift is only downstream behavior.
- `unsupported session`: the replay artifacts or exported bundle use an unsupported schema version.
- `replay failure`: the baseline could not be replayed at all, for example because a bundle file or replay artifact is missing or corrupted.

These results compare against recorded baselines. They do not make live provider
calls deterministic, and they should not be read as a guarantee about provider
behavior outside the captured baseline.

### End-To-End Baseline Flow

The typical promotion flow is:

1. Capture or identify a replayable session.
2. Export its portable bundle.
3. Add an eval case manifest that declares the expected invariants.
4. Run the eval suite locally before checking in the baseline.

Export a portable baseline from a recorded session:

```bash
uv run glassbox replay-export SESSION_ID evals/bundles/tooling.readme.json --cwd .
```

Add the matching eval case manifest:

```json
{
	"manifest_version": 1,
	"case_id": "tooling.readme",
	"title": "README inspection stays stable",
	"bundle_path": "../bundles/tooling.readme.json",
	"tags": ["smoke", "tooling"],
	"expectation": {
		"mode": "exact_match"
	}
}
```

Run the case directly:

```bash
uv run glassbox eval run tooling.readme --cwd .
```

Or run a tagged suite and emit machine-readable output:

```bash
uv run glassbox eval run --tag smoke --json --cwd .
```

Each `glassbox eval run` invocation writes one JSON artifact per executed case
plus `summary.json`. If you omit `--output-dir`, Glassbox creates a timestamped
directory under `.glassbox/evals/`.

### Local-First Verification Policy

Glassbox assumes a direct-to-`main` workflow where the important regression
barrier happens before `git commit`, not in a pull-request gate that may never
exist.

Use replay and eval verification in three layers:

1. Commit time: blocking local hooks. The existing `pre-commit` stack already
   blocks on format, lint, type-check, and `pytest`. Phase 20 extends that same
   path with curated `smoke` eval cases so the cheapest high-value replay
  regressions fail before the commit is created. The smoke hook refreshes
  `.glassbox/evals/pre-commit/` in place and writes the latest per-case
  artifacts plus `summary.json` there.
2. Push time: broader confirmation after `git push origin main`. This is where
   larger or more artifact-heavy replay/eval suites can rerun and retain output
  for inspection without slowing every commit loop. The repository ships a
  push-triggered GitHub Actions workflow in `.github/workflows/push-smoke-evals.yml`
  that reruns the same `smoke` tag set and uploads `.glassbox/evals/push-smoke/`
  as a remote artifact bundle. That workflow also renders a job summary with
  suite counts, outcome totals, per-case outcome severity, and retained artifact
  paths so a failed push can be triaged without downloading raw JSON first.
3. Later scheduled coverage: optional non-blocking suites for wider advisory
   drift detection.

The expected tag split is:

- `smoke` tags are the commit-time blocking set.
- Broader tags stay non-blocking until they are small and stable enough to earn
  promotion into the smoke barrier.

Interpret failures based on where they happen:

- A commit-time replay/eval failure means the local regression barrier already
  found drift in a curated contract. Fix or intentionally refresh the baseline
  before committing.
- A post-push replay/eval failure means the broader confirmation suite caught
  drift outside the current smoke set. Treat that as a signal to investigate the
  change and possibly promote that case or tag into the commit-time barrier.
  First check the failed `Push Smoke Evals` run for the pushed commit, then
  read the rendered job summary for the failing case, its outcome class, and the
  retained artifact path. If you still need detail, download the
  `push-smoke-evals-SHA` artifact and inspect `summary.json` plus the per-case
  JSON files.

### Local-First Operating Flows

When a commit is blocked by the smoke gate, use this sequence:

1. Run `uv run pre-commit run eval-smoke --all-files` again if you need a clean
  repro outside `git commit`.
2. Open `.glassbox/evals/pre-commit/summary.json` to identify the failing case,
  replay outcome, and artifact path.
3. Open the failing `.glassbox/evals/pre-commit/CASE_ID.json` file and inspect
  the mismatch list or error message.
4. If the drift is accidental, fix the code and rerun the smoke hook.
5. If the drift is intentional, refresh the checked-in replay bundle and case
  manifest together, review that diff as a baseline change, and rerun the hook
  before committing.

When local commit checks pass but push-time confirmation fails, use this sequence:

1. Open the failed `Push Smoke Evals` run for the pushed commit.
2. Read the rendered job summary first. It tells you which case failed, whether
  the failure was `behavioral_drift`, `manifest_drift`, `unsupported_session`,
  or `replay_failure`, and which retained artifact path to inspect.
3. If the job summary is enough to explain the regression, fix the code or
  decide whether that case now belongs in the commit-time smoke barrier.
4. If you need more detail, download the `push-smoke-evals-SHA` artifact and
  inspect `.glassbox/evals/push-smoke/summary.json` plus the failing per-case
  JSON file.
5. After the fix or baseline refresh, rerun the relevant local smoke command,
  commit, and push again so the remote confirmation reruns on the corrected
  tree.

Use these rules for the blocking `smoke` tag set:

- Keep `smoke` small, deterministic, and offline-friendly.
- Put a case in `smoke` only when it protects a high-value contract and reruns
  fast enough to stay in the commit path.
- Leave broader or more volatile cases on non-blocking tags until they have
  proved stable enough to justify blocking every commit.
- Promote a non-blocking case into `smoke` when a post-push failure shows that
  the repo needs that regression signal earlier.

### Targeted Expectations And Baseline Refresh

The default expectation is strict `exact_match`. Use a narrower
`selected_invariants` expectation only when the repository intentionally cares
about a smaller contract, such as `final_state` or `transcript` only.

That is a reviewable statement about what the case is meant to protect. It is
not a mechanism for silently tolerating arbitrary drift. When prompts, tool
schemas, or runtime context intentionally change, refresh the exported bundle and
review the bundle diff together with the case manifest change.

Use this baseline refresh playbook:

1. Confirm the observed drift is intentional and not a regression you want to
  keep catching.
2. Regenerate or re-export the replay bundle into `evals/bundles/CASE_ID.json`.
3. Update `evals/cases/CASE_ID.json` if the title, tags, notes, or selected
  invariants changed with the new contract.
4. Review bundle and manifest diffs together so the expected behavior change is
  explicit in one commit.
5. Rerun `uv run glassbox eval run CASE_ID --cwd .` or the relevant tagged suite
  before committing the refreshed baseline.

### Replay And Eval Troubleshooting

- If replay reports `manifest drift`, inspect the current prompt/context/tool preparation before refreshing the baseline. This usually means the runtime contract changed before any tool execution or transcript comparison happened.
- If replay reports `behavioral drift`, read the mismatch list and the per-case artifact JSON to see which normalized dimensions changed.
- If replay reports `unsupported session`, refresh or migrate the baseline instead of trusting a partial replay from an older manifest or bundle version.
- If replay reports `replay failure`, check for missing or corrupted replay artifacts, a missing bundle file, or a damaged checked-in baseline.
- If a child-session replay or eval case fails unexpectedly, confirm that you exported the child session itself. Child bundles are self-contained once exported, but replaying the wrong parent bundle will of course validate the wrong history.
- If a provider-backed baseline drifts unexpectedly, remember that Glassbox is replaying the recorded manifests and outputs offline. The replay signal says the current code no longer matches that recorded baseline, not that the live provider has become deterministic.
- If you only need one historical check, use `glassbox replay`. Promote to `evals/` only when the scenario should become a curated regression contract for the repository.

## Real Provider Setup

Glassbox can run against real OpenAI and Anthropic providers when provider
credentials are available in the runtime environment.

Supported provider-qualified model names for real provider execution are:

- `openai:...`
- `anthropic:...`

If no provider runtime config is present, Glassbox keeps using the deterministic
local executor path for offline development and tests.

Set credentials in your shell environment:

```bash
export OPENAI_API_KEY="..."
uv run glassbox run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
```

Or use Anthropic:

```bash
export ANTHROPIC_API_KEY="..."
uv run glassbox run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
```

Glassbox also reads an optional `.env` file from the selected runtime workspace
root, which is the path you pass through `--cwd`.

```dotenv
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
```

Process environment variables override values from `.env`.

More detail, including all supported variables and troubleshooting, is in
[docs/providers.md](docs/providers.md).

## Dashboard

There are two ways to reach the dashboard:

- `glassbox chat` starts a co-hosted dashboard by default and prints a URL that already includes `?session=SESSION_ID` for the live session it just started.
- `glassbox serve` starts a standalone dashboard server for the workspace database and is the right choice when no active `chat` process is owning the browser view.

Treat `serve` as the standalone browser console for persisted sessions. It is
the right path when you want to inspect or recover work after the original
interactive terminal session is gone, or when the browser should outlive any
single `chat` process.

Start the dashboard server:

```bash
uv run glassbox serve --cwd . --host 127.0.0.1 --port 8765
```

The command prints the dashboard URL before it blocks on the running server.

Use `serve` when you want browser access that outlives a particular `chat`
process, when you deliberately started `chat --no-dashboard`, or when the
co-hosted dashboard was unavailable and you still want to inspect persisted
session state afterward.

Open the standalone dashboard root in a browser:

```text
http://127.0.0.1:8765/
```

The root view is the recent-session browser. It lets you:

- discover the right persisted session without copying a `session_id` first
- open a selected session from the browser and keep using the direct `?session=SESSION_ID` deep-link when you already know the target
- recover from stale or invalid deep links by returning to the session index instead of leaving the browser on a dead session URL

The dashboard reads a session snapshot from `GET /sessions/{session_id}` and then
subscribes to the live SSE stream at `GET /sessions/{session_id}/events`.

Use the standalone dashboard as a durable operator console, not as terminal
reattach. A useful recovery flow now looks like this:

1. start `glassbox serve`
2. open `http://127.0.0.1:8765/`
3. browse the recent-session list and choose the session with the right next-action summary
4. use the selected-session summary to decide whether the browser can act now or whether the session is historical-only

When reading the standalone dashboard, interpret the browser state this way:

- `connecting` means the snapshot is loaded and the dashboard is trying to attach the live SSE tail
- `live` means the dashboard is receiving incremental events from an active runtime
- `reconnecting` means the snapshot is still valid while the browser retries the live stream
- `live unavailable` means the persisted snapshot is still readable, but the live stream could not be re-established and the owning runtime may be gone
- `historical snapshot` means the selected session is completed, cancelled, failed, or otherwise not expected to emit more live events
- pending `ask_user` questions and pending approvals still reflect actionable session state and can be resolved through the browser when the session allows it
- standalone browser access does not replace terminal-native `chat` ownership or create cross-process interactive attach semantics

### Lineage And Fork Data In The Dashboard

The standalone session index and per-session snapshot expose lineage and branch
readiness directly so the browser does not have to infer history from transcript
text.

Recent-session summaries include:

- `parent_session_id`, `forked_from_turn_id`, `forked_from_sequence`, and `branch_label` for ancestry
- `child_session_count` for quick branch discovery
- `can_fork`, `latest_fork_point_turn_id`, `latest_fork_point_sequence`, and `fork_blocked_reason` for lightweight branchability state

The selected-session snapshot adds:

- `child_sessions` with child session ID, status, branch label, update time, and latest message summary
- `branchable_turns` with explicit completed-turn choices the dashboard can offer in the fork UI

Use those fields this way:

- if `can_fork` is true, the latest completed turn is forkable and `branchable_turns` may offer older completed turns too
- if `can_fork` is false, `fork_blocked_reason` explains why the session is currently inspectable only
- `historical snapshot` does not mean "dead end"; it often means "inspect here, then fork if you want to continue from this history"

### Dashboard Troubleshooting

- If `glassbox chat --no-dashboard` was used, no dashboard URL is advertised for that session. Start `glassbox serve`, open `/`, and choose the session from the recent-session browser. You can still deep-link with `/?session=SESSION_ID` if you already have the ID.
- If plain `glassbox chat` warns that the dashboard is unavailable, the chat session is still running normally; the warning only means no live dashboard was started for that process.
- If `glassbox chat --dashboard-host ...` or `--dashboard-port ...` fails, fix the bind target or port conflict and rerun the command.
- The co-hosted dashboard stops when the owning `glassbox chat` process exits. Use `glassbox serve` for post-session inspection or for browser access from a separate long-lived process.
- If a standalone dashboard view still shows useful snapshot data but reports `live unavailable`, keep using the snapshot as persisted history unless another active process is known to be driving it.
- If a direct `?session=...` URL points at a deleted, stale, or invalid session, the dashboard returns to the session index and shows a `Session unavailable` recovery message instead of leaving the browser stuck on an unusable selection.
- If you need to reopen actionable work after a `chat` process exits, use the recent-session browser and the selected-session summary to determine whether to answer a pending question, resolve an approval, or switch back to CLI primitives such as `attach`, `answer`, `approve`, or `message`.
- If the dashboard shows `can_fork: false` or no `branchable_turns`, the session does not currently expose a stable completed-turn boundary for branch creation.
- If a fork action is rejected, read `fork_blocked_reason` in the summary or snapshot first; it should explain whether the session is running, paused at a suspension point, or otherwise not branchable yet.

## Local Validation

Run the baseline local validation sequence with:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pre-commit run --all-files
```

When the commit-time smoke eval hook fails, inspect the emitted suite summary
and per-case JSON under `.glassbox/evals/pre-commit/`. Each rerun refreshes
that managed directory instead of accumulating timestamped outputs.

During incremental work, prefer narrower checks for the slice you touched. Examples:

```bash
uv run pytest tests/integration/test_cli_commands.py
uv run pytest tests/integration/test_web_session_snapshot.py
uv run ruff check src/glassbox/cli/__init__.py tests/integration/test_cli_commands.py
uv run ty check src/glassbox/cli/__init__.py
uv run pytest tests/test_import_smoke.py
uv run glassbox replay SESSION_ID --cwd .
uv run glassbox eval run --tag smoke --cwd .
uv run pre-commit run eval-smoke --all-files
uv run glassbox eval run --tag smoke --output-dir .glassbox/evals/pre-commit --refresh-output-dir --cwd .
```

## Reference Docs

- Architecture: [docs/architecture.md](docs/architecture.md)
- Database design: [docs/database.md](docs/database.md)
- Eval suite layout: [evals/README.md](evals/README.md)
- Provider setup and secrets: [docs/providers.md](docs/providers.md)
- Tool policy and approvals: [docs/tool-policy.md](docs/tool-policy.md)
- Roadmap and task graph: [docs/tasks.md](docs/tasks.md)
