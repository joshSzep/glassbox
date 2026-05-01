"""Workflow grouping helpers for command-guide sections."""

from collections.abc import Iterable
from typing import Literal

from glassbox.cli.command_guide_data import COMMAND_GUIDE_SECTIONS
from glassbox.cli.command_guide_models import CommandGuideSection

CommandGuideWorkflow = Literal[
    "start",
    "inspection",
    "recovery",
    "verification",
    "provider",
    "knowledge",
    "branch-search",
    "handoff",
    "release",
]

COMMAND_GUIDE_WORKFLOW_GROUPS: dict[CommandGuideWorkflow, tuple[str, ...]] = {
    "start": ("start-work", "inspect-state", "unblock-work"),
    "inspection": ("inspect-state", "checkpoint-inspection"),
    "recovery": ("unblock-work", "long-run-recovery", "compaction", "tool-attempts"),
    "verification": ("checkpoint-inspection", "verify-work"),
    "provider": ("provider-posture",),
    "knowledge": ("knowledge-freshness",),
    "branch-search": ("branch-search-review",),
    "handoff": ("checkpoint-inspection",),
    "release": ("release-evidence",),
}


def command_guide_sections() -> tuple[CommandGuideSection, ...]:
    return COMMAND_GUIDE_SECTIONS


def sections_for_workflow(
    workflow: CommandGuideWorkflow,
    sections: Iterable[CommandGuideSection] = COMMAND_GUIDE_SECTIONS,
) -> tuple[CommandGuideSection, ...]:
    section_by_key = {section.key: section for section in sections}
    return tuple(
        section_by_key[key]
        for key in COMMAND_GUIDE_WORKFLOW_GROUPS[workflow]
        if key in section_by_key
    )


__all__ = [
    "COMMAND_GUIDE_WORKFLOW_GROUPS",
    "CommandGuideWorkflow",
    "command_guide_sections",
    "sections_for_workflow",
]
