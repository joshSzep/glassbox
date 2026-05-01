"""Terminal rendering for workflow-oriented command discovery."""

from glassbox.cli.command_guide_workflows import command_guide_sections


def format_command_guide() -> str:
    """Format the workflow command guide for terminal output."""

    lines = [
        "Glassbox command guide",
        "Workflow-oriented discovery for common operator tasks.",
        "",
    ]
    for section in command_guide_sections():
        lines.append(section.title)
        lines.append(f"  {section.summary}")
        for entry in section.entries:
            lines.append(f"  - {entry.command}")
            lines.append(f"    {entry.purpose}")
        lines.append("")
    lines.append(
        "Use `glassbox command tree` for the exhaustive structural command surface."
    )
    return "\n".join(lines)


__all__ = ["format_command_guide"]
