"""Command tree formatting for the Glassbox CLI."""

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandTreeColorTheme:
    prog: str
    action: str
    reset: str


def format_command_tree(
    parser: argparse.ArgumentParser,
    *,
    color_theme: CommandTreeColorTheme | None = None,
) -> str:
    lines = [
        _format_command_tree_node(
            parser.prog,
            parser.description,
            color_theme.prog if color_theme else None,
            color_theme,
        )
    ]
    _append_command_tree_lines(parser, lines, prefix="", color_theme=color_theme)
    return "\n".join(lines)


def _append_command_tree_lines(
    parser: argparse.ArgumentParser,
    lines: list[str],
    *,
    prefix: str,
    color_theme: CommandTreeColorTheme | None,
) -> None:
    entries = _visible_subparser_entries(parser)
    max_name_length = max((len(name) for name, _, _ in entries), default=0)
    for index, (name, child_parser, help_text) in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "`-- " if is_last else "|-- "
        name_padding = " " * (max_name_length - len(name))
        name_color = color_theme.action if color_theme else None
        node = _format_command_tree_node(
            name,
            help_text,
            name_color,
            color_theme,
            name_padding=name_padding,
        )
        lines.append(f"{prefix}{branch}{node}")
        child_prefix = f"{prefix}{'    ' if is_last else '|   '}"
        _append_command_tree_lines(
            child_parser,
            lines,
            prefix=child_prefix,
            color_theme=color_theme,
        )


def _format_command_tree_node(
    name: str,
    help_text: str | None,
    color: str | None,
    color_theme: CommandTreeColorTheme | None,
    *,
    name_padding: str = "",
) -> str:
    formatted_name = f"{_colorize(name, color, color_theme)}{name_padding}"
    if not help_text:
        return formatted_name.rstrip()
    return f"{formatted_name}  {help_text}"


def _colorize(
    text: str,
    color: str | None,
    color_theme: CommandTreeColorTheme | None,
) -> str:
    if color is None or color_theme is None:
        return text
    return f"{color}{text}{color_theme.reset}"


def _visible_subparser_entries(
    parser: argparse.ArgumentParser,
) -> list[tuple[str, argparse.ArgumentParser, str | None]]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            visible_choices = [
                choice
                for choice in action._choices_actions
                if choice.help is not argparse.SUPPRESS
            ]
            return [
                (choice.dest, action.choices[choice.dest], choice.help)
                for choice in visible_choices
                if choice.dest in action.choices
            ]
    return []
