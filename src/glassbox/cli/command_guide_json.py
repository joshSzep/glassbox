"""JSON serialization for workflow-oriented command discovery."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection
from glassbox.cli.command_guide_workflows import command_guide_sections


def command_guide_json_payload() -> dict[str, object]:
    """Return a stable JSON payload for workflow command discovery."""

    return {
        "schema_version": 1,
        "sections": [
            _section_json_payload(section) for section in command_guide_sections()
        ],
    }


def _section_json_payload(section: CommandGuideSection) -> dict[str, object]:
    return {
        "key": section.key,
        "title": section.title,
        "summary": section.summary,
        "commands": [_entry_json_payload(entry) for entry in section.entries],
    }


def _entry_json_payload(entry: CommandGuideEntry) -> dict[str, str]:
    return {"command": entry.command, "purpose": entry.purpose}


__all__ = ["command_guide_json_payload"]
