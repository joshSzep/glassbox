"""Launch-mode selection for interactive terminal session commands."""

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class InteractiveLaunchMode(StrEnum):
    PLAIN = "plain"
    TUI = "tui"


class SupportsIsatty(Protocol):
    def isatty(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class InteractiveLaunchOptions:
    requested_mode: InteractiveLaunchMode | None
    default_mode: InteractiveLaunchMode
    stdin_is_tty: bool
    stdout_is_tty: bool
    term: str | None
    ci: bool
    tui_available: bool = False


def interactive_launch_options_from_args(
    args,
    *,
    stdin: SupportsIsatty | None = None,
    stdout: SupportsIsatty | None = None,
    environ: Mapping[str, str] | None = None,
    default_mode: InteractiveLaunchMode = InteractiveLaunchMode.PLAIN,
    tui_available: bool = False,
) -> InteractiveLaunchOptions:
    environment = os.environ if environ is None else environ
    requested_mode = _requested_mode_from_args(args)
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    return InteractiveLaunchOptions(
        requested_mode=requested_mode,
        default_mode=default_mode,
        stdin_is_tty=input_stream.isatty(),
        stdout_is_tty=output_stream.isatty(),
        term=environment.get("TERM"),
        ci=_is_ci_environment(environment),
        tui_available=tui_available,
    )


def resolve_interactive_launch_mode(
    options: InteractiveLaunchOptions,
) -> InteractiveLaunchMode:
    requested_mode = options.requested_mode or options.default_mode
    if requested_mode == InteractiveLaunchMode.PLAIN:
        return InteractiveLaunchMode.PLAIN

    if not options.tui_available:
        raise ValueError(
            "full-screen TUI launch is not available in this build yet; "
            "use --plain for the current line-mode terminal experience"
        )

    if not _supports_full_screen_tui(options):
        raise ValueError(
            "full-screen TUI launch requires interactive stdin/stdout, a supported "
            "terminal, and a non-CI environment; use --plain for line mode"
        )

    return InteractiveLaunchMode.TUI


def resolve_interactive_launch_mode_from_args(args) -> InteractiveLaunchMode:
    return resolve_interactive_launch_mode(interactive_launch_options_from_args(args))


def _requested_mode_from_args(args) -> InteractiveLaunchMode | None:
    launch_mode = getattr(args, "interactive_launch_mode", None)
    if launch_mode is None:
        return None
    return InteractiveLaunchMode(launch_mode)


def _supports_full_screen_tui(options: InteractiveLaunchOptions) -> bool:
    return (
        options.stdin_is_tty
        and options.stdout_is_tty
        and not options.ci
        and options.term not in {None, "", "dumb"}
    )


def _is_ci_environment(environment: Mapping[str, str]) -> bool:
    value = environment.get("CI")
    return value is not None and value.lower() not in {"", "0", "false", "no"}
