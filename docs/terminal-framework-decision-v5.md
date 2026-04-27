# v5 Terminal UI Framework Decision

For the v5 task graph, see [tasks-v5.md](./tasks-v5.md). For the interaction contract that motivates this decision, see [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md).

## Decision

Glassbox v5 will use Textual as the full-screen terminal UI framework for `glassbox session chat` and, later, `glassbox session attach`.

Textual is now a normal runtime dependency in [pyproject.toml](../pyproject.toml). The accepted dependency range is `textual>=6,<7`, currently locked to `6.12.0` in [uv.lock](../uv.lock).

## Why Textual

The v5 terminal client needs to be a real application, not a styled line prompt. Textual is the best fit because it provides:

- full-screen app lifecycle and layout primitives
- async workers and message handling suited to live event streams
- keyboard bindings, focus management, widgets, modals, and command-surface patterns
- Rich-backed styled text and markdown-compatible rendering paths
- scrollable regions for transcript and details surfaces
- a built-in app test driver for deterministic widget and keyboard tests
- enough structure for future agent-built changes to remain maintainable

This matches the v5 product direction: chat-first, full-screen, keyboard-native, streaming, and paired with the browser dashboard.

## Alternatives Considered

### prompt-toolkit

`prompt-toolkit` is strong for advanced line-mode shells. It offers multiline input, history, completion, styling, and async prompt support. It is less suitable as the primary v5 foundation because the desired product is not a richer REPL; it is a full-screen coding-agent workspace with persistent regions, action cards, transcript scrolling, optional details, and a command palette.

`prompt-toolkit` remains a useful conceptual reference for composer behavior, but choosing it would bias the product back toward line-mode architecture.

### Hand-Rolled ANSI Or curses

Hand-rolled terminal control would keep dependencies smaller, but it would make layout, resizing, input buffer ownership, focus, modals, scrollback, testing, and cross-terminal behavior project-specific problems. That directly conflicts with the v5 goal of optimizing for user experience and maintainable agent-built evolution.

The old line-mode renderer already shows the ceiling of lightweight terminal control: it can be correct, but it cannot become a modern coding-agent surface without accumulating fragile terminal mechanics.

### Rich-Only Rendering

Rich is excellent for styled output, but it is not enough by itself for app lifecycle, focus management, keyboard routing, scrollable panes, or robust full-screen interaction. Textual uses Rich where appropriate while providing the missing application model.

## Package And Typing Notes

Textual is a runtime dependency because the default `session chat` path is intended to become a full-screen TUI in supported terminals. It is not a development-only feature.

The first smoke test lives at [tests/unit/test_tui_framework_smoke.py](../tests/unit/test_tui_framework_smoke.py). It imports Textual, constructs a minimal app, runs it under Textual's test driver, queries a widget, and exits cleanly. This proves the framework can be imported and exercised in the project test environment before product widgets exist.

If future implementation discovers type-checking limitations in Textual APIs, prefer narrow adapters or explicit local typing over broad `Any` escapes in product code.

## Packaging Notes

The dependency is managed through `uv` and recorded in both [pyproject.toml](../pyproject.toml) and [uv.lock](../uv.lock). The v5 packaging task should later verify wheel and sdist installs with Textual included, but GBX-562 establishes that the project dependency graph can resolve, install, import, and smoke-run the framework.

No Node, browser process, or frontend tooling is required for the terminal TUI dependency.

## Validation

GBX-562 validation consists of:

- dependency resolution and installation through `uv add 'textual>=6,<7'`
- smoke test: `uv run pytest tests/unit/test_tui_framework_smoke.py`
- typecheck: `uv run ty check`
