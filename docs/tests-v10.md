# Glassbox Test Suite v10 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v10 test-suite performance roadmap. It complements
[tasks-v10.md](./tasks-v10.md) and [refactor-v10.md](./refactor-v10.md) by
turning the current pytest timing findings into small, executable work items.

## Purpose

This document defines a v10 test-suite speed and ergonomics roadmap for the
current Glassbox repository.

It is written in the same execution style as [tasks-v10.md](./tasks-v10.md) and
[refactor-v10.md](./refactor-v10.md): explicit dependencies, small vertical
slices, concrete deliverables, and validation requirements attached directly to
the work.

The goal is not to weaken release confidence. The goal is to keep the full test
suite trustworthy while making the default local loop fast enough that agents
and maintainers run it often.

The v10 test-suite thesis is:

- preserve full deterministic pytest coverage as release evidence
- make local verification targetable by default
- label expensive tests by the reason they are expensive
- keep one real smoke test for each important process boundary
- replace avoidable wall-clock waits with deterministic signals
- keep daemon, subprocess, terminal, and timeout behavior covered without paying
  for full-stack startup in every adjacent test
- make timing regressions visible before they become accepted background noise

## Initial Timing Baseline

The current timing probe on the repository produced:

```text
uv run pytest --collect-only -q
1124 tests collected in 1.80s

uv run pytest tests/unit --durations=50 --durations-min=0.01 -q
566 passed in 9.76s

uv run pytest tests/integration --durations=80 --durations-min=0.05 -q
554 passed in 46.90s

uv run pytest --durations=100 --durations-min=0.05 -q
1124 passed in 56.36s
```

## Repeatable Timing Command Set

Use these serial commands when changing test-suite performance. Run them from
the repository root on an otherwise quiet local machine, and keep the top
duration output with the summary line. Treat the ranges as local guidance, not
release-blocking thresholds.

```bash
uv run pytest --collect-only -q
uv run pytest tests/unit --durations=50 --durations-min=0.01 -q
uv run pytest tests/integration --durations=80 --durations-min=0.05 -q
uv run pytest -m "daemon or subprocess or timeout or tui" --durations=80 --durations-min=0.01 -q
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow" --durations=80 --durations-min=0.05 -q
uv run pytest --durations=100 --durations-min=0.05 -q
uv run pytest -n auto --dist loadfile --durations=100 --durations-min=0.05 -q
```

Current local baseline ranges:

- collection: about 1.5s to 2.3s
- unit suite: about 9s to 11s
- integration suite: about 46s to 52s
- expensive marker slice: about 29s to 33s
- fast marker slice: about 30s to 35s
- full suite: about 56s to 62s
- parallel full suite with file-level scheduling: about 26s to 28s

Representative timing evidence:

```text
uv run pytest --collect-only -q
1124 tests collected in 1.68s

uv run pytest tests/unit --durations=50 --durations-min=0.01 -q
566 passed in 9.93s

uv run pytest tests/integration --durations=80 --durations-min=0.05 -q
554 passed in 48.34s

uv run pytest -m "daemon or subprocess or timeout or tui" --durations=80 --durations-min=0.01 -q
51 passed, 1073 deselected in 30.61s

uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow" --durations=80 --durations-min=0.05 -q
1073 passed, 51 deselected in 31.49s

uv run pytest --durations=100 --durations-min=0.05 -q
1124 passed in 59.07s

uv run pytest -n auto --dist loadfile --durations=100 --durations-min=0.05 -q
1121 passed in 26.24s
```

Refresh procedure:

1. Run the six timing commands serially after the performance task is complete.
2. Replace the representative summary lines above with the new output.
3. Adjust baseline ranges only after at least two comparable local runs or a
   stable CI run show a sustained shift.
4. Preserve the top-duration output in task evidence when a speedup claim
   depends on specific tests moving out of the slow tail.
5. Do not make these timing ranges release-blocking until variance is tracked
   across more machines.
6. Use `--dist loadfile` for xdist runs. The default xdist scheduler can fan
   daemon tests across workers and is not the documented parallel strategy for
   this suite.

Collection is not the bottleneck. Test-body execution is the bottleneck, and it
is concentrated in process-heavy integration tests, intentional timeout tests,
and Textual app-driver tests.

## Findings

Treat these findings as the evidence that should steer the first work slices:

- `tests/integration/test_daemon_runtime.py` dominates the slow tail. Several
  tests start a real daemon process, wait for health, exercise CLI behavior, and
  stop the daemon. Each full process lifecycle costs roughly 1.6 to 1.8 seconds.
- daemon helpers poll at 50 ms intervals while waiting for startup, shutdown,
  and background-job completion. The polling is appropriate for production
  behavior, but test coverage pays the interval repeatedly.
- `tests/integration/test_workflow_tools.py::test_run_tests_times_out` and
  `tests/integration/test_command_tool.py::test_run_command_times_out` add a
  hard wall-clock floor of about three seconds by intentionally waiting for
  command and pytest timeouts.
- `tests/integration/test_cli_tui_launch_smoke.py` starts a fresh Python
  subprocess to prove the non-TTY chat boundary. It is valuable, but it should
  remain a single smoke boundary rather than a pattern copied into adjacent
  tests.
- `tests/unit/test_cli_tui_app.py` is the unit-suite hotspot. The cost comes
  from Textual `app.run_test()` lifecycles, `pilot.pause()` calls, command
  palette filtering, markdown transcript rendering, and scrolling assertions.
- workflow git tests repeatedly initialize fresh repositories with `git init`,
  `git config`, `git add`, and `git commit`. The individual cost is small, but
  the pattern is visible in the slow list.
- `pyproject.toml` has no pytest markers for `slow`, `daemon`, `subprocess`,
  `timeout`, `tui`, or `release`. Contributors have no first-class way to run a
  fast default slice while preserving a full release slice.
- the dev dependency set does not include a parallel pytest runner. The suite is
  mostly `tmp_path` scoped and looks highly parallelizable, but this should be
  verified before becoming a default recommendation.

## Agent Execution Rules

These rules apply to every task in this file.

1. Preserve release confidence. Do not delete behavior coverage just to reduce
   wall-clock time.
2. Keep one real end-to-end smoke test for every process boundary that matters:
   daemon ownership, CLI subprocess launch, command execution, pytest execution,
   and terminal app behavior.
3. Prefer deterministic test seams over sleeping. If a test can observe a
   state transition, event, callback, fake clock, or injected timeout signal, do
   that before paying real wall-clock delay.
4. Mark expensive tests by the reason they are expensive, not by vague severity.
   Prefer names such as `daemon`, `subprocess`, `timeout`, `tui`, and
   `release_gate` over a single undifferentiated `slow` marker.
5. Keep default local commands honest. A fast local command may skip expensive
   smoke tests, but CI and release-gate commands must still include them.
6. Avoid broad fixture magic. Shared fixtures should make setup faster and more
   explicit, not hide process ownership, persistent files, or daemon cleanup.
7. Keep test timing evidence reproducible. Any task that claims a speedup should
   record before/after commands and representative timings in this document or a
   linked release/evidence document.
8. Every implementation task automatically includes:
   - focused pytest coverage for changed test helpers or runtime seams
   - `ruff` formatting and lint compliance for touched Python code
   - `ty` typecheck compliance for touched Python code when production Python is
     changed
   - frontend lint, typecheck, and tests when terminal or dashboard test helpers
     cross generated API or frontend boundaries
   - documentation updates when public validation commands, release gates, or
     test taxonomy change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the test coverage still exercises the behavior named by the original test
- the new command or marker taxonomy is documented
- focused validation passes for the touched slice
- the full suite still passes or any failure is unrelated and documented
- timing evidence shows that the change improved speed, reduced variance, or
  made expensive tests easier to target
- release-gate behavior remains deterministic and explicitly includes the
  expensive smoke tests it relies on

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task
IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
pyproject.toml
tests/
    unit/
    integration/
src/glassbox/
    runtime/
    tools/
    cli/
docs/
scripts/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
uv run pytest -m "not daemon and not subprocess and not timeout and not tui"
uv run pytest -m "daemon or subprocess or timeout or tui"
uv run pytest --durations=100 --durations-min=0.05 -q
```

Marker taxonomy:

- `daemon`: starts, stops, inspects, or guards the workspace daemon boundary
- `subprocess`: spawns a real subprocess boundary
- `timeout`: intentionally exercises timeout behavior
- `tui`: runs or smokes the Textual terminal app boundary
- `release_gate`: smoke coverage required by full release confidence checks
- `slow`: intentionally expensive tests not covered by a narrower marker

Default local loop:

```bash
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
```

Full confidence loop:

```bash
uv run pytest
```

The full confidence loop intentionally has no marker exclusion, so it includes
all daemon, subprocess, timeout, TUI, slow, and release-gate coverage.

Baseline validation for completed test-suite work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

If parallel execution is introduced, keep both serial and parallel confidence
checks available until ordering, cleanup, and port-allocation risks are closed.
The supported local parallel confidence check is:

```bash
uv run pytest -n auto --dist loadfile
```

Keep daemon-heavy investigation serial or use the same file-level scheduler:

```bash
uv run pytest -m daemon -n auto --dist loadfile
```

## Milestone Map

The intended v10 test-suite milestone order is:

1. taxonomy and measurement
2. timeout and polling reductions
3. daemon integration slicing
4. TUI app-driver tightening
5. workflow fixture reuse
6. optional parallel execution
7. documentation and release-gate alignment

## Task Graph

---

## Phase 90: Test Taxonomy And Measurement

### GBX-T900: Add Pytest Marker Taxonomy

- Status: `DONE`
- Depends on: none
- Goal: make expensive test categories first-class so local and release runs can
  be selected intentionally
- Deliverables:
  - add pytest marker definitions for `daemon`, `subprocess`, `timeout`, `tui`,
    `release_gate`, and `slow`
  - mark the known expensive tests and files by their actual cost driver
  - add one documented fast-local command that excludes expensive categories
  - add one documented full-confidence command that includes every marker
- Implementation notes:
  - avoid marking an entire file if only a few tests need the expensive marker
  - keep marker names stable and boring
  - include `--strict-markers` only after all current markers are declared
- Tests and validation included in task:
  - `uv run pytest --collect-only -q`
  - `uv run pytest -m "daemon or subprocess or timeout or tui" --collect-only -q`
  - `uv run pytest -m "not daemon and not subprocess and not timeout and not tui" --collect-only -q`
- Done when:
  - contributors can run a fast default slice without remembering individual
    test files

Validation evidence:

- `uv run pytest --collect-only -q`: 1124 tests collected in 1.57s
- `uv run pytest -m "daemon or subprocess or timeout or tui" --collect-only -q`:
  51 selected / 1124 collected in 1.56s
- `uv run pytest -m "not daemon and not subprocess and not timeout and not tui" --collect-only -q`:
  1073 selected / 1124 collected in 2.23s
- `uv run ruff format --check tests/integration/test_command_tool.py tests/integration/test_workflow_tools.py tests/integration/test_cli_tui_launch_smoke.py tests/integration/test_daemon_runtime.py tests/unit/test_cli_tui_app.py tests/unit/test_tui_framework_smoke.py`:
  6 files already formatted
- `uv run ruff check tests/integration/test_command_tool.py tests/integration/test_workflow_tools.py tests/integration/test_cli_tui_launch_smoke.py tests/integration/test_daemon_runtime.py tests/unit/test_cli_tui_app.py tests/unit/test_tui_framework_smoke.py`:
  all checks passed

### GBX-T901: Record A Repeatable Timing Command Set

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: make suite timing a routine measurement instead of an anecdote
- Deliverables:
  - document timing commands for collection, unit, integration, expensive
    marker slice, fast marker slice, and full suite
  - add expected baseline timing ranges for the current machine class or CI
    environment where available
  - add a short update procedure for refreshing this document after test-suite
    speed work
- Implementation notes:
  - do not make exact timing thresholds release-blocking until variance is
    understood
  - prefer ranges and top-duration output over a single wall-clock number
- Tests and validation included in task:
  - run the documented timing commands once and record representative output
- Done when:
  - a future agent can measure whether a proposed speedup actually helped

Validation evidence:

- `uv run pytest --collect-only -q`: 1124 tests collected in 1.68s
- `uv run pytest tests/unit --durations=50 --durations-min=0.01 -q`:
  566 passed in 9.93s
- `uv run pytest tests/integration --durations=80 --durations-min=0.05 -q`:
  554 passed in 48.34s
- `uv run pytest -m "daemon or subprocess or timeout or tui" --durations=80 --durations-min=0.01 -q`:
  51 passed, 1073 deselected in 30.61s
- `uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow" --durations=80 --durations-min=0.05 -q`:
  1073 passed, 51 deselected in 31.49s
- `uv run pytest --durations=100 --durations-min=0.05 -q`:
  1124 passed in 59.07s

---

## Phase 91: Timeout And Polling Reductions

### GBX-T910: Replace Real Timeout Sleeps With Deterministic Timeout Seams

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: remove the hard wall-clock floor from command and pytest timeout tests
  while preserving timeout behavior coverage
- Deliverables:
  - introduce a test seam for command timeout expiry or subprocess wait timing
  - update command timeout tests so they do not require `sleep 60` plus a real
    one-second timeout
  - update pytest-runner timeout tests so they do not require a real two-second
    timeout
  - keep one marked `timeout` smoke test that proves the real wall-clock path
    still works
- Implementation notes:
  - prefer dependency injection in the command/test runner over monkeypatching
    private asyncio internals
  - assert the same output fields: `timed_out`, exit code, failure category, and
    execution envelope timeout
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_command_tool.py -q`
  - `uv run pytest tests/integration/test_workflow_tools.py -q`
  - `uv run pytest -m timeout --durations=20 --durations-min=0.01 -q`
- Done when:
  - timeout coverage remains explicit, but the regular timeout slice no longer
    pays multiple seconds of unavoidable waiting

Validation evidence:

- Added injectable subprocess-runner seams to `RunCommandTool` and
  `RunTestsTool` so timeout result envelopes can be exercised without waiting
  for real subprocess expiry.
- Kept `test_run_command_real_timeout_smoke` as the marked `timeout`,
  `subprocess`, and `release_gate` wall-clock smoke path.
- `uv run pytest tests/integration/test_command_tool.py -q`:
  16 passed in 1.73s
- `uv run pytest tests/integration/test_workflow_tools.py -q`:
  30 passed in 3.90s
- `uv run pytest -m timeout --durations=20 --durations-min=0.01 -q`:
  3 passed, 1122 deselected in 2.73s; only the real timeout smoke appears in
  the slow list at 1.01s
- `uv run ruff format --check src/glassbox/tools/command.py src/glassbox/tools/workflow.py tests/integration/test_command_tool.py tests/integration/test_workflow_tools.py`:
  4 files already formatted
- `uv run ruff check src/glassbox/tools/command.py src/glassbox/tools/workflow.py tests/integration/test_command_tool.py tests/integration/test_workflow_tools.py`:
  all checks passed
- `uv run ty check`: all checks passed

### GBX-T911: Tighten Daemon Polling In Tests Without Weakening Production Defaults

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: reduce repeated 50 ms polling costs in daemon tests
- Deliverables:
  - expose narrowly scoped test-only or injectable polling intervals for daemon
    startup and shutdown waits
  - use shorter intervals in daemon tests where the event source is local and
    deterministic
  - keep production defaults conservative
- Implementation notes:
  - do not make daemon health checks busy-spin
  - preserve stale-owner recovery and port-conflict behavior
  - keep cleanup reliable even when a daemon test fails
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py -q`
  - `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`
- Done when:
  - daemon tests have lower average duration without increased flake risk

Validation evidence:

- Added `DEFAULT_RUNTIME_OWNER_POLL_INTERVAL_SECONDS` with injectable startup
  and shutdown poll intervals; production callers keep the 50 ms default.
- The daemon integration file uses a 5 ms autouse test interval and keeps the
  background-job completion poll local to the test at 10 ms.
- `uv run pytest tests/integration/test_daemon_runtime.py -q`:
  21 passed in 18.34s
- `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`:
  11 passed, 1114 deselected in 18.21s
- `uv run ruff format --check src/glassbox/runtime/daemon.py tests/integration/test_daemon_runtime.py`:
  2 files already formatted
- `uv run ruff check src/glassbox/runtime/daemon.py tests/integration/test_daemon_runtime.py`:
  all checks passed
- `uv run ty check`: all checks passed

---

## Phase 92: Daemon Integration Slicing

### GBX-T920: Split Real Daemon Smoke From CLI Formatting And Guard Tests

- Status: `DONE`
- Depends on: `GBX-T911`
- Goal: keep daemon process confidence while avoiding full daemon startup for
  assertions that can run against records, fakes, or in-process helpers
- Deliverables:
  - identify daemon tests that only verify status text, JSON shape, stale-owner
    guidance, duplicate-owner errors, or CLI guard wording
  - move those assertions to faster unit or in-process integration tests
  - keep a small marked `daemon` smoke set that starts the real daemon process
  - keep one background-job daemon smoke covering the real worker loop
- Implementation notes:
  - preserve the one-local-mutation-owner contract
  - do not replace the real port-conflict smoke until there is equivalent
    process-boundary evidence
  - prefer helper functions that build owner metadata and status records over
    broad mocks
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py -q`
  - focused unit tests for moved status/formatting behavior
  - `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`
- Done when:
  - the daemon file no longer pays a real process lifecycle for every nearby CLI
    assertion

Validation evidence:

- Converted daemon status JSON shape coverage to an in-process
  `RuntimeOwnerStatus` fixture instead of starting a daemon only to inspect
  formatting.
- Converted the TUI attach daemon-routing assertion to a mocked healthy runtime
  owner plus mocked TUI handoff; it still verifies the daemon dashboard URL is
  passed through.
- Kept the real daemon smoke set for daemon ownership, stale recovery,
  port-conflict handling, background job execution, live attach, observation,
  cancellation, and historical-session rejection.
- `uv run pytest tests/integration/test_daemon_runtime.py -q`:
  21 passed in 16.01s
- `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`:
  9 passed, 1116 deselected in 15.67s
- `uv run ruff format --check tests/integration/test_daemon_runtime.py`:
  1 file already formatted
- `uv run ruff check tests/integration/test_daemon_runtime.py`:
  all checks passed
- `uv run ty check`: all checks passed

### GBX-T921: Add Shared Daemon Smoke Fixture With Strong Cleanup

- Status: `DONE`
- Depends on: `GBX-T920`
- Goal: reduce duplicated daemon lifecycle setup where multiple assertions can
  safely share one process within a test
- Deliverables:
  - add a helper or fixture that starts a daemon, yields its port and database
    path, and always stops it
  - convert applicable daemon tests to perform multiple related assertions
    within one daemon lifecycle
  - document when not to share a daemon because isolation is part of the test
- Implementation notes:
  - keep the fixture function-scoped unless a broader scope proves safe under
    serial and parallel execution
  - avoid hiding test setup so much that process ownership is unclear
  - share a daemon only when related assertions can safely exercise the same
    workspace, database, and session state; keep separate daemon lifecycles for
    startup failure, port conflict, stale-owner recovery, background-worker
    smoke, and transcript-mutating attach flows where isolation is part of the
    evidence
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py -q`
  - rerun the daemon slice twice to look for cleanup leaks
- Done when:
  - daemon lifecycle setup is explicit, reliable, and less repetitive

Validation evidence:

- Added a function-scoped `DaemonStarter` fixture that starts a real daemon with
  an explicit workspace, optional database path, and reserved port, then always
  stops any started daemon in fixture teardown.
- Converted real-daemon smoke tests to use the shared starter where startup
  itself is not the subject of the assertion.
- Combined live attach observation, idle cancel routing, and historical-session
  rejection into one real-daemon routing guard test, preserving the behavior
  checks while reducing daemon lifecycles.
- `uv run pytest tests/integration/test_daemon_runtime.py -q`:
  19 passed in 12.17s
- `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`:
  7 passed, 1116 deselected in 11.48s
- `uv run pytest -m daemon --durations=40 --durations-min=0.01 -q`:
  7 passed, 1116 deselected in 11.39s
- `uv run ruff format --check tests/integration/test_daemon_runtime.py`:
  1 file already formatted
- `uv run ruff check tests/integration/test_daemon_runtime.py`:
  all checks passed
- `uv run ty check`: all checks passed
- `uv run pytest --durations=100 --durations-min=0.05 -q`:
  1123 passed in 47.78s

---

## Phase 93: Terminal App Driver Tightening

### GBX-T930: Audit Textual Pilot Pauses

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: remove unnecessary `pilot.pause()` calls and replace them with more
  specific assertions or event waits
- Deliverables:
  - review `tests/unit/test_cli_tui_app.py` for pauses after key presses,
    command execution, stream ingestion, and markdown rendering
  - delete pauses that are no longer required
  - replace remaining pauses with helper names that explain the state being
    awaited
  - keep tests readable for future terminal behavior changes
- Implementation notes:
  - do not trade speed for flakiness
  - prioritize the command palette and streaming transcript tests, which appear
    at the top of the unit slow list
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_app.py --durations=40 --durations-min=0.01 -q`
  - `uv run pytest tests/unit/test_tui_framework_smoke.py -q`
- Done when:
  - Textual unit tests are faster and the remaining waits name what they are
    waiting for

Validation evidence:

- Replaced raw `pilot.pause()` calls in `test_cli_tui_app.py` with named helper
  waits for reactive widget updates, palette filtering, stream ingestion,
  transcript scrolling, and markdown rendering.
- Shortened the command palette filter path by setting the mounted palette
  input value directly and waiting for the filter update instead of simulating
  long per-character typing.
- Before: `uv run pytest tests/unit/test_cli_tui_app.py --durations=40 --durations-min=0.01 -q`:
  36 passed in 7.14s; command palette test 1.76s.
- After: `uv run pytest tests/unit/test_cli_tui_app.py --durations=40 --durations-min=0.01 -q`:
  36 passed in 6.33s; command palette test 0.47s.
- `uv run pytest tests/unit/test_tui_framework_smoke.py -q`:
  1 passed in 0.06s
- `uv run ruff format --check tests/unit/test_cli_tui_app.py`:
  1 file already formatted
- `uv run ruff check tests/unit/test_cli_tui_app.py`:
  all checks passed
- `uv run ty check`: all checks passed

### GBX-T931: Separate Pure TUI State Tests From App-Driver Tests

- Status: `DONE`
- Depends on: `GBX-T930`
- Goal: avoid launching a Textual app for behavior that can be tested through
  pure reducers, selectors, command handlers, or widget formatting helpers
- Deliverables:
  - identify assertions in `test_cli_tui_app.py` that do not need a mounted app
  - move those assertions to existing pure TUI state, conversation, command, or
    widget tests
  - keep mounted app tests for keyboard integration, focus behavior, scrolling,
    and lifecycle behavior
- Implementation notes:
  - preserve coverage for user-visible keyboard and rendering contracts
  - do not make pure tests duplicate mounted app assertions unnecessarily
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py -q`
- Done when:
  - app-driver tests are reserved for behavior that truly needs the app driver

Validation evidence:

- Moved pure terminal keybinding coverage from `test_cli_tui_app.py` to
  `test_cli_tui_commands.py`, alongside the command registry and slash command
  checks.
- Moved `session_dashboard_url` selector coverage from the app-driver file to
  `test_cli_tui_conversation.py`.
- Kept mounted app-driver coverage for app creation, lifecycle, focus,
  keyboard integration, palette execution, streaming, markdown rendering,
  scrolling, and runtime feedback behavior.
- `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py -q`:
  76 passed in 6.34s
- `uv run pytest tests/unit/test_cli_tui_app.py --durations=40 --durations-min=0.01 -q`:
  31 passed in 6.06s
- `uv run ruff format --check tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py`:
  4 files already formatted
- `uv run ruff check tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py`:
  all checks passed
- `uv run ty check`: all checks passed

---

## Phase 94: Workflow Fixture Reuse

### GBX-T940: Reduce Repeated Git Repository Setup Cost

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: make git workflow tests cheaper without losing real git behavior
- Deliverables:
  - introduce a small helper or fixture for initialized git repositories
  - avoid repeated config/setup commands when a test only needs a clean commit
  - keep tests that validate git command behavior against real git
- Implementation notes:
  - be careful with shared repositories; most tests should still get isolated
    `tmp_path` state
  - prefer a copied template repository only if it is faster and does not hide
    test intent
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_workflow_tools.py --durations=40 --durations-min=0.01 -q`
  - `uv run pytest tests/unit/test_verification_drift.py -q`
- Done when:
  - git workflow setup is less repetitive and remains easy to inspect

Validation evidence:

- Added a session-scoped initialized git repository template and a function
  scoped `git_repo` copy fixture in `test_workflow_tools.py`, so each test keeps
  isolated workspace state while avoiding repeated `git init`, config, add, and
  initial commit setup.
- Kept tests that validate staged changes and additional commits on real git
  commands inside the copied per-test repository.
- Before: `uv run pytest tests/integration/test_workflow_tools.py --durations=40 --durations-min=0.01 -q`:
  30 passed in 3.03s
- After: `uv run pytest tests/integration/test_workflow_tools.py --durations=40 --durations-min=0.01 -q`:
  30 passed in 2.59s
- `uv run pytest tests/unit/test_verification_drift.py -q`:
  4 passed in 0.53s
- `uv run ruff format --check tests/integration/test_workflow_tools.py`:
  1 file already formatted
- `uv run ruff check tests/integration/test_workflow_tools.py`:
  all checks passed
- `uv run ty check`: all checks passed

### GBX-T941: Cache OpenAPI Schema Construction Where Tests Only Inspect Shape

- Status: `DONE`
- Depends on: `GBX-T900`
- Goal: reduce repeated FastAPI/OpenAPI construction costs in schema tests
- Deliverables:
  - share schema construction within `tests/integration/test_openapi_schema.py`
    when tests only inspect deterministic schema shape
  - keep determinism coverage that builds the schema twice
  - avoid global cache in production schema export behavior unless separately
    justified
- Implementation notes:
  - fixture-level caching is enough; production behavior does not need to change
  - preserve the deterministic export test
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_openapi_schema.py --durations=20 --durations-min=0.01 -q`
- Done when:
  - schema tests retain coverage while avoiding unnecessary repeated app setup

Validation evidence:

- Added a module-scoped `openapi_schema` fixture for the two shape-inspection
  tests in `test_openapi_schema.py`.
- Kept `test_openapi_schema_export_is_deterministic` building the schema twice
  so determinism coverage remains independent of fixture caching.
- Before: `uv run pytest tests/integration/test_openapi_schema.py --durations=20 --durations-min=0.01 -q`:
  3 passed in 2.36s
- After: `uv run pytest tests/integration/test_openapi_schema.py --durations=20 --durations-min=0.01 -q`:
  3 passed in 1.93s
- `uv run ruff format --check tests/integration/test_openapi_schema.py`:
  1 file already formatted
- `uv run ruff check tests/integration/test_openapi_schema.py`:
  all checks passed
- `uv run ty check`: all checks passed

---

## Phase 95: Parallel Execution Evaluation

### GBX-T950: Evaluate Pytest Parallelism Safely

- Status: `DONE`
- Depends on: `GBX-T920`, `GBX-T940`
- Goal: determine whether `pytest-xdist` can shorten full-suite wall-clock time
  without hiding cleanup or port-allocation bugs
- Deliverables:
  - add `pytest-xdist` to dev dependencies only after a clean evaluation
  - run representative unit, integration, daemon, and full-suite parallel passes
  - document any tests that must remain serial and why
  - add a recommended parallel local command if results are stable
- Implementation notes:
  - daemon tests and port-reservation tests need special attention
  - do not make parallel execution the only supported validation mode
  - keep serial full-suite validation available for release confidence
- Tests and validation included in task:
  - serial `uv run pytest`
  - candidate parallel `uv run pytest -n auto`
  - repeated daemon slice under the chosen parallel strategy
- Done when:
  - the project either has a documented safe parallel command or a documented
    reason to defer parallelism

Validation evidence:

- Added `pytest-xdist>=3.8,<4` to the dev dependency group.
- Default xdist scheduling is not recommended for daemon-heavy slices:
  `uv run --with pytest-xdist pytest -m daemon -n auto --durations=40 --durations-min=0.01 -q`
  failed with 6 daemon startup-health failures because daemon tests were
  scheduled across workers concurrently.
- `uv run pytest --durations=100 --durations-min=0.05 -q`:
  1121 passed in 44.47s
- `uv run --with pytest-xdist pytest -n auto --durations=100 --durations-min=0.05 -q`:
  1121 passed in 20.01s, but this default scheduler is not the documented
  strategy because the daemon slice failed separately.
- `uv run --with pytest-xdist pytest tests/unit -n auto --durations=50 --durations-min=0.01 -q`:
  564 passed in 26.13s
- `uv run --with pytest-xdist pytest tests/integration -n auto --dist loadfile --durations=80 --durations-min=0.05 -q`:
  553 passed in 26.68s
- `uv run --with pytest-xdist pytest -m daemon -n auto --dist loadfile --durations=40 --durations-min=0.01 -q`:
  7 passed in 27.98s
- repeated `uv run --with pytest-xdist pytest -m daemon -n auto --dist loadfile --durations=40 --durations-min=0.01 -q`:
  7 passed in 26.92s
- `uv run --with pytest-xdist pytest -n auto --dist loadfile --durations=100 --durations-min=0.05 -q`:
  1121 passed in 26.24s
- final installed-dependency `uv run pytest -q`:
  1121 passed in 44.80s
- final installed-dependency `uv run pytest -n auto --dist loadfile -q`:
  1121 passed in 18.97s
- final installed-dependency `uv run pytest -m daemon -n auto --dist loadfile -q`:
  7 passed in 15.47s
- final installed-dependency `uv run pytest --collect-only -q`:
  1121 tests collected in 1.33s
- `uv run ruff format --check .`:
  496 files already formatted
- `uv run ruff check .`:
  all checks passed
- `uv run ty check`:
  all checks passed

---

## Phase 96: Release And Documentation Alignment

### GBX-T960: Align Release Gates With Test Marker Taxonomy

- Status: `TODO`
- Depends on: `GBX-T900`, `GBX-T950`
- Goal: make release scripts intentionally include the expensive tests that
  prove process and timeout boundaries
- Deliverables:
  - review release-gate scripts and docs for pytest command assumptions
  - ensure expensive markers are included in full release validation
  - add a fast-local command to contributor docs without weakening release
    commands
  - update any release evidence docs that describe test posture
- Implementation notes:
  - do not replace replay/eval release authority with marker filtering
  - make the relationship between fast local checks and full release checks
    explicit
- Tests and validation included in task:
  - dry-run relevant release-gate scripts
  - `uv run pytest -m "daemon or subprocess or timeout or tui" -q`
  - `uv run pytest`
- Done when:
  - local speed improvements and release confidence are both documented

### GBX-T961: Add A Suite-Speed Regression Watch

- Status: `TODO`
- Depends on: `GBX-T901`
- Goal: make future test-speed regressions visible during normal maintenance
- Deliverables:
  - add a lightweight script or documented command that records top slow tests
  - define a review practice for new tests that exceed a chosen local threshold
  - document when a new expensive test should receive a marker
- Implementation notes:
  - avoid brittle hard thresholds until the suite has stable timing history
  - prefer top-duration reporting and marker taxonomy over failing CI on small
    variance
- Tests and validation included in task:
  - run the suite-speed command and confirm it reports useful top-duration data
- Done when:
  - expensive tests become a conscious review decision instead of accumulated
    drag
