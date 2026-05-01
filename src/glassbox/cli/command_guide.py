"""Compatibility facade for workflow-oriented command discovery."""

from glassbox.cli.command_guide_data import COMMAND_GUIDE_SECTIONS
from glassbox.cli.command_guide_json import command_guide_json_payload
from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection
from glassbox.cli.command_guide_render import format_command_guide
from glassbox.cli.command_guide_workflows import COMMAND_GUIDE_WORKFLOW_GROUPS
from glassbox.cli.command_guide_workflows import command_guide_sections
from glassbox.cli.command_guide_workflows import sections_for_workflow

__all__ = [
    "COMMAND_GUIDE_SECTIONS",
    "COMMAND_GUIDE_WORKFLOW_GROUPS",
    "CommandGuideEntry",
    "CommandGuideSection",
    "command_guide_json_payload",
    "command_guide_sections",
    "format_command_guide",
    "sections_for_workflow",
]
