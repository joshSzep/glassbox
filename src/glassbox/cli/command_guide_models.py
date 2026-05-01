"""Typed models for workflow-oriented command discovery."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandGuideEntry:
    command: str
    purpose: str


@dataclass(frozen=True)
class CommandGuideSection:
    key: str
    title: str
    summary: str
    entries: tuple[CommandGuideEntry, ...]


__all__ = ["CommandGuideEntry", "CommandGuideSection"]
