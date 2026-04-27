"""Tests for interactive terminal launch-mode selection."""

from argparse import Namespace

import pytest

from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.interactive_launch import interactive_launch_options_from_args
from glassbox.cli.interactive_launch import resolve_interactive_launch_mode
from glassbox.cli.parser import build_parser


def test_launch_resolver_defaults_to_tui_when_supported() -> None:
    mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=True,
        )
    )

    assert mode == InteractiveLaunchMode.TUI


def test_launch_resolver_falls_back_to_plain_for_implicit_non_tty() -> None:
    mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=False,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=True,
        )
    )

    assert mode == InteractiveLaunchMode.PLAIN


def test_launch_resolver_falls_back_for_implicit_ci_and_dumb_term() -> None:
    ci_mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=True,
            tui_available=True,
        )
    )
    dumb_mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="dumb",
            ci=False,
            tui_available=True,
        )
    )

    assert ci_mode == InteractiveLaunchMode.PLAIN
    assert dumb_mode == InteractiveLaunchMode.PLAIN


def test_launch_resolver_falls_back_to_plain_when_tui_unavailable_implicitly() -> None:
    mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=None,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=False,
        )
    )

    assert mode == InteractiveLaunchMode.PLAIN


def test_launch_resolver_allows_explicit_plain_for_redirected_streams() -> None:
    mode = resolve_interactive_launch_mode(
        InteractiveLaunchOptions(
            requested_mode=InteractiveLaunchMode.PLAIN,
            default_mode=InteractiveLaunchMode.TUI,
            stdin_is_tty=False,
            stdout_is_tty=False,
            term="dumb",
            ci=True,
            tui_available=True,
        )
    )

    assert mode == InteractiveLaunchMode.PLAIN


def test_launch_resolver_rejects_explicit_tui_until_available() -> None:
    options = InteractiveLaunchOptions(
        requested_mode=InteractiveLaunchMode.TUI,
        default_mode=InteractiveLaunchMode.PLAIN,
        stdin_is_tty=True,
        stdout_is_tty=True,
        term="xterm-256color",
        ci=False,
    )

    with pytest.raises(ValueError, match="not available"):
        resolve_interactive_launch_mode(options)


def test_launch_resolver_rejects_tui_for_non_interactive_environment() -> None:
    options = InteractiveLaunchOptions(
        requested_mode=InteractiveLaunchMode.TUI,
        default_mode=InteractiveLaunchMode.PLAIN,
        stdin_is_tty=False,
        stdout_is_tty=True,
        term="xterm-256color",
        ci=False,
        tui_available=True,
    )

    with pytest.raises(ValueError, match="requires interactive stdin/stdout"):
        resolve_interactive_launch_mode(options)


def test_launch_options_capture_ci_environment() -> None:
    options = interactive_launch_options_from_args(
        Namespace(interactive_launch_mode=None),
        stdin=_FakeStream(is_tty=True),
        stdout=_FakeStream(is_tty=True),
        environ={"TERM": "xterm-256color", "CI": "true"},
        tui_available=True,
    )

    assert options.ci is True
    assert options.term == "xterm-256color"
    assert options.default_mode == InteractiveLaunchMode.TUI


def test_chat_and_attach_parse_launch_mode_flags() -> None:
    parser = build_parser()

    chat_args = parser.parse_args(["session", "chat", "--plain"])
    attach_args = parser.parse_args(
        ["session", "attach", "00000000-0000-0000-0000-000000000001", "--tui"]
    )

    assert chat_args.interactive_launch_mode == "plain"
    assert attach_args.interactive_launch_mode == "tui"


class _FakeStream:
    def __init__(self, *, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty
